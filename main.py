from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

resposta = client.models.generate_content(
    model=GEMINI_MODEL,
    contents="Oi! Vocês vendem violão?",
    config=types.GenerateContentConfig(
        system_instruction="Você é um atendente simpático de uma loja de instrumentos musicais.",
    ),
)

print(resposta.text)