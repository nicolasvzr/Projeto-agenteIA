import os
from pathlib import Path

from dotenv import load_dotenv

# Pasta raiz do projeto (a pasta acima de src/)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

# Lê o .env que está na raiz do projeto
load_dotenv(BASE_DIR / ".env")

# Chave da API do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Lista de modelos: o primeiro é o principal, os demais são reservas
GEMINI_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_MODELS", "gemini-3.5-flash").split(",")
    if m.strip()
]

if not GEMINI_API_KEY:
    raise ValueError(f"GEMINI_API_KEY não encontrada. Confira o arquivo {BASE_DIR / '.env'}")
if not GEMINI_MODELS:
    raise ValueError(f"GEMINI_MODELS não encontrada. Confira o arquivo {BASE_DIR / '.env'}")