"""Mercado Livre API - Funções para pedidos e envios ME1."""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Optional

BASE_URL = "https://api.mercadolibre.com"
SELLER_ID = "2497155445"  # Sollar Sul

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "3257050458992695")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "V1OQ3lOyLbfTpBwKZhPUfJ6tr27qsRzn")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN", "")


def refresh_token() -> dict:
    """Renova o access token do ML."""
    r = requests.post(
        f"{BASE_URL}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": ML_CLIENT_ID,
            "client_secret": ML_CLIENT_SECRET,
            "refresh_token": ML_REFRESH_TOKEN,
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
        "Accept": "application/json",
    }


def search_orders(token: str, date_from: Optional[str] = None, offset: int = 0) -> dict:
    """Busca pedidos do seller. Limit max = 50."""
    params = {
        "seller": SELLER_ID,
        "limit": 50,
        "offset": offset,
    }
    if date_from:
        params["order.date_created.from"] = date_from

    r = requests.get(
        f"{BASE_URL}/orders/search",
        headers=_headers(token),
        params=params,
    )
    r.raise_for_status()
    return r.json()


def get_all_orders(token: str, days_back: int = 15) -> list:
    """Busca todos os pedidos dos últimos N dias, paginando."""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00.000-03:00")
    all_orders = []
    offset = 0

    while True:
        result = search_orders(token, date_from=date_from, offset=offset)
        orders = result.get("results", [])
        if not orders:
            break
        all_orders.extend(orders)
        total = result.get("paging", {}).get("total", 0)
        offset += len(orders)
        if offset >= total:
            break

    return all_orders


def get_order_shipment(token: str, order_id: int) -> Optional[dict]:
    """Busca o shipment de um pedido específico."""
    r = requests.get(
        f"{BASE_URL}/orders/{order_id}/shipments",
        headers=_headers(token),
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return data if "id" in data else None


def get_shipment(token: str, shipment_id: int) -> Optional[dict]:
    """Busca detalhes completos de um envio."""
    r = requests.get(
        f"{BASE_URL}/shipments/{shipment_id}",
        headers={**_headers(token), "x-format-new": "true"},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def get_shipment_lead_time(token: str, shipment_id: int) -> Optional[dict]:
    """Busca lead_time (prazos) de um envio."""
    r = requests.get(
        f"{BASE_URL}/shipments/{shipment_id}/lead_time",
        headers=_headers(token),
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def get_shipment_carrier(token: str, shipment_id: int) -> Optional[dict]:
    """Busca informações da transportadora."""
    r = requests.get(
        f"{BASE_URL}/shipments/{shipment_id}/carrier",
        headers=_headers(token),
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def get_me1_orders(token: str, days_back: int = 15) -> list:
    """Busca todos os pedidos ME1 com informações de envio."""
    orders = get_all_orders(token, days_back)
    me1_orders = []

    for order in orders:
        shipping = order.get("shipping", {})
        shipment_id = shipping.get("id")
        if not shipment_id:
            continue

        shipment = get_shipment(token, shipment_id)
        if not shipment:
            continue

        logistic = shipment.get("logistic", {})
        if logistic.get("mode") != "me1":
            continue

        lead_time = get_shipment_lead_time(token, shipment_id)
        carrier_info = get_shipment_carrier(token, shipment_id)

        me1_orders.append({
            "order_id": order.get("id"),
            "shipment_id": shipment_id,
            "status": shipment.get("status"),
            "substatus": shipment.get("substatus"),
            "tracking_number": shipment.get("tracking_number"),
            "carrier_name": carrier_info.get("name") if carrier_info else None,
            "carrier_url": carrier_info.get("url") if carrier_info else None,
            "logistic_mode": logistic.get("mode"),
            "logistic_type": logistic.get("type"),
            "date_created": order.get("date_created"),
            "last_updated": shipment.get("last_updated"),
            "lead_time": lead_time,
            "destination": shipment.get("destination", {}),
            "order_items": order.get("order_items", []),
            "total_amount": order.get("total_amount"),
            "buyer": order.get("buyer", {}),
            "tags": order.get("tags", []),
        })

    return me1_orders
