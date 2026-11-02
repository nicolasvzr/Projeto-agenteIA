"""Extrai o texto do manual de políticas (PDF) para docs/politicas.md.

Rodar uma vez, na raiz do projeto:  python -m scripts.extrair_politicas
Depois, revisar o .md à mão (tabelas e quebras de linha costumam sair bagunçadas).
"""
from pypdf import PdfReader

from src.config import DATA_DIR, DOCS_DIR


def main():
    pdfs = list(DATA_DIR.glob("*pol*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Nenhum PDF de políticas encontrado em {DATA_DIR}")

    leitor = PdfReader(pdfs[0])
    paginas = [pagina.extract_text() for pagina in leitor.pages]

    DOCS_DIR.mkdir(exist_ok=True)
    destino = DOCS_DIR / "politicas.md"
    destino.write_text("\n\n".join(paginas), encoding="utf-8")

    print(f"{len(paginas)} páginas extraídas para {destino}")


if __name__ == "__main__":
    main()