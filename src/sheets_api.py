"""Google Sheets API - Leitura e escrita na planilha de monitoramento."""

import os
import json
from datetime import datetime
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "")

SHEET_HEADERS = [
    "order_id_ml",
    "shipment_id_ml",
    "numero_pedido_bling",
    "numero_nf",
    "transportadora",
    "status_ml",
    "substatus_ml",
    "prazo_estimado",
    "prazo_final",
    "data_faturamento",
    "dias_restantes",
    "status_prazo",
    "data_atualizacao",
    "destinatario",
    "cidade_destino",
    "uf_destino",
    "valor_pedido",
    "tracking_number",
]


def get_credentials():
    """Carrega credenciais da Service Account."""
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT", "")
    if creds_json:
        creds_info = json.loads(creds_json)
    else:
        creds_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "google_service_account.json"
        )
        if not os.path.exists(creds_path):
            raise FileNotFoundError(
                "Credenciais Google não encontradas. "
                "Configure GOOGLE_SERVICE_ACCOUNT env var ou coloque o JSON em config/"
            )
        with open(creds_path) as f:
            creds_info = json.load(f)

    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )
    return creds


def get_sheets_service():
    """Retorna serviço do Google Sheets."""
    creds = get_credentials()
    return build("sheets", "v4", credentials=creds)


def get_drive_service():
    """Retorna serviço do Google Drive."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def setup_sheet():
    """Cria a estrutura da planilha se não existir."""
    service = get_sheets_service()

    try:
        service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    except Exception:
        _create_sheet(service)

    _ensure_headers(service)


def _create_sheet(service):
    """Cria uma nova planilha com as abas."""
    body = {
        "properties": {"title": "Monitor de Fretes ML ↔ Bling"},
        "sheets": [
            {"properties": {"title": "Pedidos", "sheetId": 0}},
            {"properties": {"title": "Log", "sheetId": 1}},
        ],
    }
    result = service.spreadsheets().create(body=body).execute()
    global SHEET_ID
    SHEET_ID = result["spreadsheetId"]


def _ensure_headers(service):
    """Garante que os cabeçalhos existem na aba Pedidos."""
    range_query = "Pedidos!A1:R1"
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=range_query
    ).execute()

    existing = result.get("values", [[]])[0] if result.get("values") else []

    if existing != SHEET_HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range="Pedidos!A1",
            valueInputOption="RAW",
            body={"values": [SHEET_HEADERS]},
        ).execute()


def _ensure_log_headers(service):
    """Garante que os cabeçalhos existem na aba Log."""
    log_headers = [
        "data_hora",
        "tipo_operacao",
        "registros_processados",
        "erros",
        "detalhes",
    ]

    range_query = "Log!A1:E1"
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=range_query
    ).execute()

    existing = result.get("values", [[]])[0] if result.get("values") else []

    if existing != log_headers:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range="Log!A1",
            valueInputOption="RAW",
            body={"values": [log_headers]},
        ).execute()


def get_existing_orders() -> dict:
    """Lê todos os pedidos existentes e retorna como dict por order_id_ml."""
    service = get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="Pedidos!A2:R",
    ).execute()

    rows = result.get("values", [])
    orders = {}
    for idx, row in enumerate(rows):
        if row and row[0]:
            order_id = str(row[0]).strip()
            orders[order_id] = {
                "row_idx": idx + 2,
                "data": row,
            }

    return orders


def upsert_pedido(pedido: dict):
    """Insere ou atualiza um pedido na planilha."""
    service = get_sheets_service()

    existing = get_existing_orders()
    order_id = str(pedido.get("order_id_ml", "")).strip()

    row_data = [
        str(pedido.get("order_id_ml", "")),
        str(pedido.get("shipment_id_ml", "")),
        str(pedido.get("numero_pedido_bling", "")),
        str(pedido.get("numero_nf", "")),
        str(pedido.get("transportadora", "")),
        str(pedido.get("status_ml", "")),
        str(pedido.get("substatus_ml", "")),
        str(pedido.get("prazo_estimado", "")),
        str(pedido.get("prazo_final", "")),
        str(pedido.get("data_faturamento", "")),
        str(pedido.get("dias_restantes", "")),
        str(pedido.get("status_prazo", "")),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        str(pedido.get("destinatario", "")),
        str(pedido.get("cidade_destino", "")),
        str(pedido.get("uf_destino", "")),
        str(pedido.get("valor_pedido", "")),
        str(pedido.get("tracking_number", "")),
    ]

    if order_id in existing:
        row_num = existing[order_id]["row_idx"]
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"Pedidos!A{row_num}:R{row_num}",
            valueInputOption="RAW",
            body={"values": [row_data]},
        ).execute()
    else:
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range="Pedidos!A:R",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_data]},
        ).execute()


def write_log(tipo_operacao: str, registros: int, erros: str, detalhes: str):
    """Registra log de operação."""
    service = get_sheets_service()
    _ensure_log_headers(service)

    log_row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        tipo_operacao,
        str(registros),
        erros,
        detalhes,
    ]

    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="Log!A:E",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [log_row]},
    ).execute()


def read_all_pedidos() -> list:
    """Lê todos os pedidos da planilha e retorna como lista de dicts."""
    service = get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="Pedidos!A2:R",
    ).execute()

    rows = result.get("values", [])
    pedidos = []

    for row in rows:
        if not row or not row[0]:
            continue
        while len(row) < len(SHEET_HEADERS):
            row.append("")

        pedido = {}
        for i, header in enumerate(SHEET_HEADERS):
            pedido[header] = row[i] if i < len(row) else ""
        pedidos.append(pedido)

    return pedidos
