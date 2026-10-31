import json
from functools import lru_cache

import pandas as pd

from src.config import DATA_DIR


def _ler_csv(nome: str) -> pd.DataFrame:
    """Encontra e lê o CSV cujo nome termina com o nome informado (ex.: 'products')."""
    arquivos = list(DATA_DIR.glob(f"*{nome}.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV terminando em '{nome}.csv' em {DATA_DIR}")
    return pd.read_csv(arquivos[0])


@lru_cache(maxsize=1)
def carregar_dados() -> dict[str, pd.DataFrame]:
    """Carrega e trata todas as tabelas. Só lê os arquivos uma vez."""
    produtos = _ler_csv("products")
    categorias = _ler_csv("categories")
    pedidos = _ler_csv("orders")
    itens = _ler_csv("order_items")
    promocoes = _ler_csv("promotions")
    clientes = _ler_csv("customers")

    # specs: texto JSON -> dicionário
    produtos["specs"] = produtos["specs"].apply(json.loads)

    # nome da categoria dentro da tabela de produtos
    produtos = produtos.merge(
        categorias[["category_id", "name"]].rename(columns={"name": "category_name"}),
        on="category_id",
        how="left",
    )

    # textos -> datas
    produtos["created_at"] = pd.to_datetime(produtos["created_at"])
    pedidos["order_date"] = pd.to_datetime(pedidos["order_date"])
    pedidos["estimated_delivery"] = pd.to_datetime(pedidos["estimated_delivery"])

    return {
        "produtos": produtos,
        "categorias": categorias,
        "pedidos": pedidos,
        "itens": itens,
        "promocoes": promocoes,
        "clientes": clientes,
    }


if __name__ == "__main__":
    dados = carregar_dados()
    for nome, tabela in dados.items():
        print(f"{nome}: {len(tabela)} linhas")
    print(dados["produtos"][["name", "price_brl", "category_name"]].head())