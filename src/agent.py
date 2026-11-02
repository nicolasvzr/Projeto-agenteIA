from google import genai
from google.genai import types
from google.genai import errors
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.data_loader import carregar_dados
from src.prompts import SYSTEM_PROMPT
from src.tools import buscar_produtos
import time
from src.spinner import Spinner

# Máximo de idas e vindas com ferramentas por mensagem (evita loop infinito)
MAX_PASSOS = 5
# Quantas vezes tentar de novo quando o Google estiver indisponível ou com limite de uso
TENTATIVAS = 3

# Liga o NOME que o Gemini usa à FUNÇÃO Python que será executada
FUNCOES = {
    "buscar_produtos": buscar_produtos,
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


class Agente:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.historico: list[types.Content] = []
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[_declaracao_buscar_produtos()])],
        )
    def _gerar(self):
        """Chama o Gemini e tenta de novo, esperando um pouco, se o servidor estiver ocupado."""
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                with Spinner("Pensando"):
                    return self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=self.historico,
                        config=self.config,
                    )
            except (errors.ServerError, errors.ClientError) as erro:
                pode_repetir = isinstance(erro, errors.ServerError) or erro.code == 429
                if not pode_repetir or tentativa == TENTATIVAS:
                    raise
                espera = 2 ** tentativa
                print(f"  [aviso] modelo indisponível ({erro.code}), tentando de novo em {espera}s...")
                time.sleep(espera)

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
                    print(f"  [ferramenta] {chamada.name}({dict(chamada.args or {})})")
                    resultado = _executar_ferramenta(chamada)
                    partes.append(types.Part.from_function_response(name=chamada.name, response=resultado))
                self.historico.append(types.Content(role="user", parts=partes))

            return "Desculpe, tive um problema para concluir sua solicitação. Pode tentar de novo?"

        except errors.APIError as erro:
            # Desfaz a mensagem que falhou, para o histórico não ficar quebrado
            del self.historico[tamanho_antes:]
            print(f"  [erro] {erro.code}: {erro.message}")
            return "Ops, estou com uma instabilidade aqui. Pode mandar sua mensagem de novo em instantes? 🙏"