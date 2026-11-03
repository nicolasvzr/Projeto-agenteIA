from google import genai
from google.genai import types
from google.genai import errors
from src.config import GEMINI_API_KEY, GEMINI_MODELS
from src.data_loader import carregar_dados
from src.prompts import montar_prompt
from src.tools import buscar_produtos
import time
from src.spinner import Spinner
from src.tools import buscar_produtos, consultar_pedido

# Máximo de idas e vindas com ferramentas por mensagem (evita loop infinito)
MAX_PASSOS = 5
# Quantas vezes tentar de novo quando o Google estiver indisponível ou com limite de uso
TENTATIVAS = 3

# Liga o NOME que o Gemini usa à FUNÇÃO Python que será executada
FUNCOES = {
    "buscar_produtos": buscar_produtos,
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
}


def _declaracao_buscar_produtos() -> types.FunctionDeclaration:
    """Descreve a ferramenta para o Gemini: o que faz e quais parâmetros aceita."""
    categorias = carregar_dados()["categorias"]["name"].tolist()

    return types.FunctionDeclaration(
        name="buscar_produtos",
        description=(
            "Busca instrumentos no catálogo da loja. Use SEMPRE que o cliente perguntar sobre "
            "produtos, preços, disponibilidade, estoque ou promoções. Retorna preço original, "
            "desconto e preço final já formatados em reais."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "termo": types.Schema(
                    type=types.Type.STRING,
                    description="Palavras do nome ou da descrição. Ex.: 'takamine gd20', 'nylon', 'choro'.",
                ),
                "categoria": types.Schema(
                    type=types.Type.STRING,
                    enum=categorias,
                    description="Categoria do produto.",
                ),
                "preco_min": types.Schema(
                    type=types.Type.NUMBER,
                    description="Preço mínimo em reais.",
                ),
                "preco_max": types.Schema(
                    type=types.Type.NUMBER,
                    description="Preço máximo em reais.",
                ),
                "apenas_disponiveis": types.Schema(
                    type=types.Type.BOOLEAN,
                    description=(
                        "True (padrão): só itens à venda e com estoque. Use False para verificar "
                        "se um produto específico existe, mas está esgotado ou descontinuado."
                    ),
                ),
                "cordas": types.Schema(
                    type=types.Type.STRING,
                    enum=["nylon", "aço"],
                    description="Tipo de corda (só violões e ukuleles).",
                ),
                "eletrico": types.Schema(
                    type=types.Type.BOOLEAN,
                    description="True para eletroacústicos (com captação para ligar em amplificador); False para só acústicos.",
                ),
            },
        ),
    )

def _declaracao_consultar_pedido() -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name="consultar_pedido",
        description=(
            "Consulta status, rastreio, datas, valor, forma de pagamento e itens de um pedido. "
            "Use quando o cliente perguntar sobre um pedido específico (status, entrega, troca, devolução). "
            "Só chame quando tiver os TRÊS dados informados pelo cliente: número do pedido, nome e e-mail do cadastro."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "numero_pedido": types.Schema(type=types.Type.INTEGER, description="Número do pedido."),
                "nome": types.Schema(type=types.Type.STRING, description="Nome do cliente, como informado por ele."),
                "email": types.Schema(type=types.Type.STRING, description="E-mail do cadastro, como informado pelo cliente."),
            },
            required=["numero_pedido", "nome", "email"],
        ),
    )


def _executar_ferramenta(chamada: types.FunctionCall) -> dict:
    """Executa a função pedida pelo Gemini e devolve o resultado (ou o erro)."""
    funcao = FUNCOES.get(chamada.name)
    if funcao is None:
        return {"erro": f"Ferramenta '{chamada.name}' não existe."}
    try:
        return {"resultado": funcao(**(chamada.args or {}))}
    except Exception as erro:
        print(f"  [erro na ferramenta] {type(erro).__name__}: {erro}")
        return {"erro": str(erro)}

def _args_para_log(args: dict) -> dict:
    """Esconde dados pessoais antes de imprimir no terminal."""
    seguro = dict(args)
    if "email" in seguro:
        usuario, _, dominio = str(seguro["email"]).partition("@")
        seguro["email"] = f"{usuario[:2]}***@{dominio}"
    if "nome" in seguro:
        seguro["nome"] = str(seguro["nome"]).split()[0] + " ***"
    return seguro


class Agente:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.historico: list[types.Content] = []
        self.config = types.GenerateContentConfig(
            system_instruction=montar_prompt(),
            tools=[types.Tool(function_declarations=[_declaracao_buscar_produtos(), _declaracao_consultar_pedido()])],
        )
    def _gerar(self):
        """Tenta cada modelo da lista. Servidor ocupado (5xx): tenta de novo. Cota esgotada (429): pula de modelo."""
        ultimo_erro = None
        for modelo in GEMINI_MODELS:
            for tentativa in range(1, TENTATIVAS + 1):
                try:
                    with Spinner("Pensando"):
                        return self.client.models.generate_content(
                            model=modelo,
                            contents=self.historico,
                            config=self.config,
                        )
                except errors.ClientError as erro:
                    if erro.code != 429:
                        raise  # erro no pedido (ex.: chave inválida): trocar de modelo não resolve
                    ultimo_erro = erro
                    print(f"  [aviso] cota do {modelo} esgotada, trocando de modelo...")
                    break  # sai das tentativas e vai para o próximo modelo
                except errors.ServerError as erro:
                    ultimo_erro = erro
                    if tentativa < TENTATIVAS:
                        espera = 2 ** tentativa
                        print(f"  [aviso] {modelo} ocupado ({erro.code}), tentando de novo em {espera}s...")
                        time.sleep(espera)
                    else:
                        print(f"  [aviso] {modelo} não respondeu, trocando de modelo...")
        raise ultimo_erro

    def responder(self, mensagem: str) -> str:
        # Guarda o tamanho do histórico para desfazer, caso dê erro
        tamanho_antes = len(self.historico)
        self.historico.append(types.Content(role="user", parts=[types.Part.from_text(text=mensagem)]))

        try:
            for _ in range(MAX_PASSOS):
                resposta = self._gerar()
                self.historico.append(resposta.candidates[0].content)

                if not resposta.function_calls:
                    return resposta.text or "Desculpe, não consegui responder agora."

                partes = []
                for chamada in resposta.function_calls:
                    print(f"  [ferramenta] {chamada.name}({_args_para_log(dict(chamada.args or {}))})")
                    resultado = _executar_ferramenta(chamada)
                    partes.append(types.Part.from_function_response(name=chamada.name, response=resultado))
                self.historico.append(types.Content(role="user", parts=partes))

            return "Desculpe, tive um problema para concluir sua solicitação. Pode tentar de novo?"

        except errors.APIError as erro:
            # Desfaz a mensagem que falhou, para o histórico não ficar quebrado
            del self.historico[tamanho_antes:]
            print(f"  [erro] {erro.code}: {erro.message}")
            return "Ops, estou com uma instabilidade aqui. Pode mandar sua mensagem de novo em instantes? 🙏"