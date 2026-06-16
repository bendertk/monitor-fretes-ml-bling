"""Bling ERP API v3 - Funções para pedidos de venda e notas fiscais."""

import os
import json
import time
import base64
import requests
from datetime import datetime, timedelta
from typing import Optional

BASE_URL = "https://api.bling.com.br/Api/v3"

BLING_CLIENT_ID = os.getenv("BLING_CLIENT_ID", "83483e57e0af43c356b267ce6106bca22202c277")
BLING_CLIENT_SECRET = os.getenv("BLING_CLIENT_SECRET", "9879630e958f7f8a78023e7995898cc62df3c2e04c4d2fbedd528db9dd43")
BLING_REFRESH_TOKEN = os.getenv("BLING_REFRESH_TOKEN", "bb02a0dde7e8db92d035910088ea8e368b9fee29")


def refresh_token() -> dict:
    """Renova o access token do Bling."""
    auth = base64.b64encode(
        f"{BLING_CLIENT_ID}:{BLING_CLIENT_SECRET}".encode()
    ).decode()

    r = requests.post(
        f"{BASE_URL}/oauth/token",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "1.0",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": BLING_REFRESH_TOKEN,
        },
    )
    r.raise_for_status()
    data = r.json()
    data["saved_at"] = time.time()
    return data


def get_access_token() -> str:
    """Retorna access token válido."""
    data = refresh_token()
    return data["access_token"]


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "1.0",
    }


def list_pedidos_vendas(
    token: str,
    data_inicial: str,
    data_final: str,
    situacao: int = 9,
    pagina: int = 1,
    limite: int = 100,
) -> dict:
    """
    Lista pedidos de venda do Bling.
    situacao: 6=Em Aberto, 9=Faturado, 12=Em Aberto (editavel)
    """
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "situacao": situacao,
        "pagina": pagina,
        "limite": limite,
    }
    r = requests.get(
        f"{BASE_URL}/pedidos/vendas",
        headers=_headers(token),
        params=params,
    )
    r.raise_for_status()
    return r.json()


def get_pedido_venda(token: str, pedido_id: int) -> Optional[dict]:
    """Busca detalhe de um pedido de venda específico."""
    r = requests.get(
        f"{BASE_URL}/pedidos/vendas/{pedido_id}",
        headers=_headers(token),
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def list_nfe(
    token: str,
    data_inicial: str,
    data_final: str,
    tipo: int = 1,
    situacao: int = 6,
    pagina: int = 1,
    limite: int = 100,
) -> dict:
    """
    Lista notas fiscais do Bling.
    tipo: 0=Entrada, 1=Saída
    situacao: 5=Autorizada, 6=Emitida DANFE, 7=Registrada
    """
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "tipo": tipo,
        "situacao": situacao,
        "pagina": pagina,
        "limite": limite,
    }
    r = requests.get(
        f"{BASE_URL}/nfe",
        headers=_headers(token),
        params=params,
    )
    r.raise_for_status()
    return r.json()


def get_nfe(token: str, nfe_id: int) -> Optional[dict]:
    """Busca detalhe de uma NF específica."""
    r = requests.get(
        f"{BASE_URL}/nfe/{nfe_id}",
        headers=_headers(token),
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def get_all_pedidos_faturados(token: str, days_back: int = 15) -> list:
    """Busca todos os pedidos faturados dos últimos N dias."""
    data_inicial = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    data_final = datetime.now().strftime("%Y-%m-%d")

    all_pedidos = []
    pagina = 1

    while True:
        result = list_pedidos_vendas(
            token,
            data_inicial=data_inicial,
            data_final=data_final,
            situacao=9,
            pagina=pagina,
        )
        pedidos = result.get("data", [])
        if not pedidos:
            break
        all_pedidos.extend(pedidos)

        links = result.get("links", [])
        has_next = any(link.get("rel") == "next" for link in links)
        if not has_next:
            break
        pagina += 1

    return all_pedidos


def get_all_pedidos_recentes(token: str, days_back: int = 15) -> list:
    """Busca TODOS os pedidos recentes (todas as situações)."""
    data_inicial = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    data_final = datetime.now().strftime("%Y-%m-%d")

    all_pedidos = []
    pagina = 1

    while True:
        params = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
            "pagina": pagina,
            "limite": 100,
        }
        r = requests.get(
            f"{BASE_URL}/pedidos/vendas",
            headers=_headers(token),
            params=params,
        )
        r.raise_for_status()
        result = r.json()

        pedidos = result.get("data", [])
        if not pedidos:
            break
        all_pedidos.extend(pedidos)

        links = result.get("links", [])
        has_next = any(link.get("rel") == "next" for link in links)
        if not has_next:
            break
        pagina += 1

    return all_pedidos


def get_all_nfe_saida(token: str, days_back: int = 15) -> list:
    """Busca todas as NF de saída autorizadas dos últimos N dias."""
    data_inicial = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d 00:00:00")
    data_final = datetime.now().strftime("%Y-%m-%d 23:59:59")

    all_nfe = []
    pagina = 1

    while True:
        result = list_nfe(
            token,
            data_inicial=data_inicial,
            data_final=data_final,
            tipo=1,
            situacao=6,
            pagina=pagina,
        )
        nfe_list = result.get("data", [])
        if not nfe_list:
            break
        all_nfe.extend(nfe_list)

        links = result.get("links", [])
        has_next = any(link.get("rel") == "next" for link in links)
        if not has_next:
            break
        pagina += 1

    return all_nfe


def extrair_transportadora_nfe(nfe: dict) -> Optional[str]:
    """Extrai nome da transportadora da NF."""
    if not nfe:
        return None

    transporte = nfe.get("transporte", {})
    if not transporte:
        return None

    transportadora = transporte.get("transportadora", {})
    if transportadora:
        return transportadora.get("nome")

    return transporte.get("transportadora", {}).get("descricao")


def extrair_numero_loja_pedido(pedido: dict) -> Optional[str]:
    """Extrai o numeroLoja (número do pedido ML) do pedido Bling."""
    if not pedido:
        return None

    numero_loja = pedido.get("numeroLoja", "")
    if numero_loja:
        return str(numero_loja).strip()

    return None
