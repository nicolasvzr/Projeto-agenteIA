import unicodedata

import pandas as pd

from src.data_loader import carregar_dados

LIMITE_RESULTADOS = 10


def _normalizar(texto) -> str:
    """Remove acentos, deixa minúsculo e tira espaços das pontas. 'Violão' -> 'violao'."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower().strip()

def _formatar_reais(valor: float) -> str:
    """1299.9 -> 'R$ 1.299,90'"""
    texto = f"{valor:,.2f}"  # '1,299.90' (padrão americano)
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


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
    eletrico: bool | None = None,
) -> dict:
    """Busca produtos no catálogo por nome/descrição, categoria e faixa de preço."""
    df = _produtos_com_preco_final()

    if apenas_disponiveis:
        df = df[(df["status"] == "active") & (df["stock_quantity"] > 0)]

    if categoria:
        df = df[df["category_name"].apply(_normalizar) == _normalizar(categoria)]

    if cordas:
        valor = {"nylon": "nylon", "aco": "steel"}.get(_normalizar(cordas))
        df = df[df["specs"].apply(lambda s: s.get("strings")) == valor]

    if eletrico is not None:
        esperado = "yes" if eletrico else "no"
        df = df[df["specs"].apply(lambda s: s.get("electronics")) == esperado]

    if termo:
        texto = (df["name"] + " " + df["description"]).apply(_normalizar)
        for palavra in _normalizar(termo).split():
            df = df[texto.loc[df.index].str.contains(palavra, regex=False)]

    if preco_min is not None:
        df = df[df["preco_final"] >= preco_min]
    if preco_max is not None:
        df = df[df["preco_final"] <= preco_max]

    total = len(df)
    df = df.sort_values("preco_final").head(LIMITE_RESULTADOS)

    produtos = [
        {
            "nome": linha["name"],
            "categoria": linha["category_name"],
            "preco_original": _formatar_reais(linha["price_brl"]),
            "desconto_percent": int(linha["discount_percent"]),
            "promocao": linha["promocao"] if pd.notna(linha["promocao"]) else None,
            "preco_final": _formatar_reais(linha["preco_final"]),
            "estoque": int(linha["stock_quantity"]),
            "status": linha["status"],
            "especificacoes": linha["specs"],
            "descricao": linha["description"],
        }
        for _, linha in df.iterrows()
    ]

    return {"total_encontrado": total, "exibindo": len(produtos), "produtos": produtos}


if __name__ == "__main__":
    r = buscar_produtos(categoria="Violões", cordas="aço", preco_max=1000)
    print(f"Total: {r['total_encontrado']} | Exibindo: {r['exibindo']}")
    for p in r["produtos"]:
        print(p["nome"], "|", p["preco_final"])

    print("\n--- Takamine GD20 ---")
    print(buscar_produtos(termo="takamine gd20"))

    print("\n--- Produto em promoção (Ohana CK-20) ---")
    print(buscar_produtos(termo="ohana ck-20"))