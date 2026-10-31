import unicodedata

import pandas as pd

from src.data_loader import carregar_dados

LIMITE_RESULTADOS = 10


def _normalizar(texto) -> str:
    """Remove acentos, deixa minúsculo e tira espaços das pontas. 'Violão' -> 'violao'."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower().strip()


def _produtos_com_preco_final() -> pd.DataFrame:
    """Tabela de produtos com as colunas da promoção ativa e do preço final."""
    dados = carregar_dados()
    produtos = dados["produtos"]
    promocoes = dados["promocoes"]

    ativas = promocoes[promocoes["is_active"] == 1][["product_id", "discount_percent", "description"]]
    ativas = ativas.rename(columns={"description": "promocao"})

    df = produtos.merge(ativas, on="product_id", how="left")
    df["discount_percent"] = df["discount_percent"].fillna(0)
    df["preco_final"] = (df["price_brl"] * (1 - df["discount_percent"] / 100)).round(2)
    return df


def buscar_produtos(
    termo: str | None = None,
    categoria: str | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
    apenas_disponiveis: bool = True,
) -> list[dict]:
    """Busca produtos no catálogo por nome/descrição, categoria e faixa de preço."""
    df = _produtos_com_preco_final()

    if apenas_disponiveis:
        df = df[(df["status"] == "active") & (df["stock_quantity"] > 0)]

    if categoria:
        df = df[df["category_name"].apply(_normalizar) == _normalizar(categoria)]

    if termo:
        texto = (df["name"] + " " + df["description"]).apply(_normalizar)
        for palavra in _normalizar(termo).split():
            df = df[texto.loc[df.index].str.contains(palavra, regex=False)]

    if preco_min is not None:
        df = df[df["preco_final"] >= preco_min]
    if preco_max is not None:
        df = df[df["preco_final"] <= preco_max]

    df = df.sort_values("preco_final").head(LIMITE_RESULTADOS)

    return [
        {
            "nome": linha["name"],
            "categoria": linha["category_name"],
            "preco_original": linha["price_brl"],
            "desconto_percent": int(linha["discount_percent"]),
            "promocao": linha["promocao"] if pd.notna(linha["promocao"]) else None,
            "preco_final": linha["preco_final"],
            "estoque": int(linha["stock_quantity"]),
            "status": linha["status"],
            "especificacoes": linha["specs"],
            "descricao": linha["description"],
        }
        for _, linha in df.iterrows()
    ]


if __name__ == "__main__":
    print("--- Violões até R$1000 ---")
    for p in buscar_produtos(categoria="Violões", preco_max=1000):
        print(p["nome"], "|", p["preco_final"])

    print("\n--- Takamine GD20 ---")
    print(buscar_produtos(termo="takamine gd20"))

    print("\n--- Produto em promoção (Ohana CK-20) ---")
    print(buscar_produtos(termo="ohana ck-20"))