import unicodedata

import pandas as pd

from src.data_loader import carregar_dados

from datetime import date

LIMITE_RESULTADOS = 10


def _normalizar(texto) -> str:
    """Remove acentos, deixa minúsculo e tira espaços das pontas. 'Violão' -> 'violao'."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.lower().strip()


def _formatar_reais(valor: float) -> str:
    """1299.9 -> 'R$ 1.299,90'"""
    texto = f"{valor:,.2f}"
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


def _promocoes_encerradas() -> dict:
    """{product_id: ['Nome da promoção', ...]} das promoções que já acabaram."""
    promocoes = carregar_dados()["promocoes"]
    return (
        promocoes[promocoes["is_active"] == 0]
        .groupby("product_id")["description"]
        .apply(lambda nomes: sorted(set(nomes)))
        .to_dict()
    )


def buscar_produtos(
    termo: str | None = None,
    categoria: str | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
    cordas: str | None = None,
    eletrico: bool | None = None,
    apenas_disponiveis: bool = True,
) -> dict:
    """Busca produtos no catálogo por nome/descrição, categoria, faixa de preço, tipo de corda e captação."""
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
    encerradas = _promocoes_encerradas()

    produtos = [
        {
            "nome": linha["name"],
            "categoria": linha["category_name"],
            "preco_original": _formatar_reais(linha["price_brl"]),
            "desconto_percent": int(linha["discount_percent"]),
            "promocao": linha["promocao"] if pd.notna(linha["promocao"]) else None,
            "preco_final": _formatar_reais(linha["preco_final"]),
            "promocoes_encerradas": encerradas.get(linha["product_id"], []),
            "estoque": int(linha["stock_quantity"]),
            "status": linha["status"],
            "especificacoes": linha["specs"],
            "descricao": linha["description"],
        }
        for _, linha in df.iterrows()
    ]

    return {"total_encontrado": total, "exibindo": len(produtos), "produtos": produtos}

STATUS_PEDIDO = {
    "pending": "Aguardando confirmação do pagamento",
    "confirmed": "Pagamento confirmado, em preparação para envio",
    "shipped": "Enviado",
    "delivered": "Entregue",
    "cancelled": "Cancelado",
}


def _forma_pagamento(codigo: str) -> str:
    """'credit_12x' -> 'Cartão de crédito em 12x'"""
    nomes = {"pix": "PIX", "debit": "Cartão de débito", "boleto": "Boleto bancário"}
    if codigo in nomes:
        return nomes[codigo]
    if codigo.startswith("credit_"):
        return f"Cartão de crédito em {codigo.removeprefix('credit_')}"
    return codigo


def _data(valor) -> str | None:
    """Data do pandas -> '05/01/2026' (ou None se estiver vazia)."""
    return valor.strftime("%d/%m/%Y") if pd.notna(valor) else None


def consultar_pedido(numero_pedido: int, nome: str, email: str) -> dict:
    """Consulta um pedido. Só devolve os dados se o nome e o e-mail baterem com o cadastro do cliente."""
    dados = carregar_dados()
    pedidos, clientes = dados["pedidos"], dados["clientes"]
    nao_encontrado = {"encontrado": False, "mensagem": "Nenhum pedido encontrado com esses dados."}

    pedido = pedidos[pedidos["order_id"] == int(numero_pedido)]
    if pedido.empty:
        return nao_encontrado
    pedido = pedido.iloc[0]

    cliente = clientes[clientes["customer_id"] == pedido["customer_id"]].iloc[0]

    # E-mail: precisa ser igual (sem diferenciar maiúsculas). Nome: todas as palavras informadas
    # precisam estar no nome do cadastro (aceita "Rafael Pereira" para "Rafael Augusto Pereira").
    email_ok = _normalizar(email) == _normalizar(cliente["email"])
    palavras_nome = _normalizar(nome).split()
    nome_ok = bool(palavras_nome) and all(p in _normalizar(cliente["name"]).split() for p in palavras_nome)
    if not (email_ok and nome_ok):
        return nao_encontrado  # mesma resposta para qualquer erro: não revela qual dado está errado

    itens = dados["itens"].merge(dados["produtos"][["product_id", "name"]], on="product_id")
    itens = itens[itens["order_id"] == pedido["order_id"]]

    hoje = date.today()
    entrega = pedido["estimated_delivery"]
    return {
        "encontrado": True,
        "numero_pedido": int(pedido["order_id"]),
        "primeiro_nome_cliente": cliente["name"].split()[0],
        "status": STATUS_PEDIDO.get(pedido["status"], pedido["status"]),
        "data_pedido": _data(pedido["order_date"]),
        "dias_desde_o_pedido": (hoje - pedido["order_date"].date()).days,
        "previsao_entrega": _data(entrega),
        "dias_desde_a_entrega_prevista": (hoje - entrega.date()).days if pd.notna(entrega) else None,
        "entrega_atrasada": bool(pedido["status"] == "shipped" and pd.notna(entrega) and entrega.date() < hoje),
        "valor_total": _formatar_reais(pedido["total_brl"]),
        "forma_pagamento": _forma_pagamento(pedido["payment_method"]),
        "codigo_rastreio": pedido["tracking_code"] if pd.notna(pedido["tracking_code"]) else None,
        "observacao": pedido["notes"] if pd.notna(pedido["notes"]) else None,
        "itens": [{"produto": i["name"], "quantidade": int(i["quantity"])} for _, i in itens.iterrows()],
        "data_de_hoje": hoje.strftime("%d/%m/%Y"),
    }


if __name__ == "__main__":
    r = buscar_produtos(categoria="Violões", cordas="aço", preco_max=1000)
    print(f"Total: {r['total_encontrado']} | Exibindo: {r['exibindo']}")
    for p in r["produtos"]:
        print(p["nome"], "|", p["preco_final"])

    print("\n--- Martin D-28 (promoção encerrada) ---")
    for p in buscar_produtos(termo="martin d-28", apenas_disponiveis=False)["produtos"]:
        print(p["nome"], "|", p["preco_final"], "| encerradas:", p["promocoes_encerradas"])

    print("\n--- Pedidos ---")
    print(consultar_pedido(5, "Rafael Pereira", "rafael.pereira@jmail.com"))   # certo
    print(consultar_pedido(5, "Rafael Pereira", "outro@email.com"))            # e-mail errado
    print(consultar_pedido(19, "pedro henrique oliveira", "PEDRO.OLIVEIRA@jmail.com"))  # maiúsculas
    print(consultar_pedido(8, "Ana Carolina Ferreira", "anacarol.ferreira@coldmail.com"))  # enviado e atrasado
