from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.data_loader import carregar_dados
from src.prompts import SYSTEM_PROMPT
from src.tools import buscar_produtos

# Máximo de idas e vindas com ferramentas por mensagem (evita loop infinito)
MAX_PASSOS = 5

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
        return {"erro": str(erro)}


class Agente:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.historico: list[types.Content] = []
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[_declaracao_buscar_produtos()])],
        )

    def responder(self, mensagem: str) -> str:
        # 1. Mensagem do cliente entra no histórico
        self.historico.append(types.Content(role="user", parts=[types.Part.from_text(text=mensagem)]))

        for _ in range(MAX_PASSOS):
            # 2. Manda o histórico inteiro + as ferramentas para o Gemini
            resposta = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=self.historico,
                config=self.config,
            )

            # 3. Guarda a resposta do modelo (completa, não só o texto)
            self.historico.append(resposta.candidates[0].content)

            # 4. Se não pediu ferramenta, é a resposta final
            if not resposta.function_calls:
                return resposta.text or "Desculpe, não consegui responder agora."

            # 5. Executa cada ferramenta pedida e devolve os resultados ao modelo
            partes = []
            for chamada in resposta.function_calls:
                print(f"  [ferramenta] {chamada.name}({dict(chamada.args or {})})")
                resultado = _executar_ferramenta(chamada)
                partes.append(types.Part.from_function_response(name=chamada.name, response=resultado))
            self.historico.append(types.Content(role="user", parts=partes))

        return "Desculpe, tive um problema para concluir sua solicitação. Pode tentar de novo?"