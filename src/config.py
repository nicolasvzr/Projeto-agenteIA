import os
from pathlib import Path

from dotenv import load_dotenv

# Lê o arquivo .env e carrega as variáveis de ambiente
load_dotenv()

# Pasta raiz do projeto (a pasta acima de src/)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

# Configurações do modelo (Google Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY não encontrada. Confira o arquivo .env.")