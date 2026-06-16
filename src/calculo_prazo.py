"""Cálculo de prazos e status de entrega."""

from datetime import datetime, timedelta
from typing import Optional


def calcular_prazos(pedido: dict) -> dict:
    """Calcula prazos e status de prazo de um pedido."""
    lead_time = pedido.get("lead_time")

    prazo_estimado = ""
    prazo_final = ""

    if lead_time:
        est = lead_time.get("estimated_delivery_time", {})
        if est:
            prazo_estimado = est.get("date", "")

        final = lead_time.get("estimated_delivery_final", {})
        if final:
            prazo_final = final.get("date", "")

    if not prazo_final and prazo_estimado:
        prazo_final = prazo_estimado

    pedido["prazo_estimado"] = _formatar_data(prazo_estimado)
    pedido["prazo_final"] = _formatar_data(prazo_final)

    pedido["dias_restantes"] = _calcular_dias_restantes(pedido["prazo_final"])

    pedido["status_prazo"] = _classificar_status(
        pedido.get("status_ml", ""),
        pedido.get("substatus_ml", ""),
        pedido["dias_restantes"],
    )

    return pedido


def _formatar_data(data_str: str) -> str:
    """Converte data ISO para formato DD/MM/YYYY."""
    if not data_str:
        return ""

    try:
        if "T" in data_str:
            dt = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
        elif "-" in data_str and len(data_str) == 10:
            dt = datetime.strptime(data_str, "%Y-%m-%d")
        else:
            return data_str

        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return data_str


def _calcular_dias_restantes(prazo_final: str) -> Optional[int]:
    """Calcula dias restantes até o prazo final."""
    if not prazo_final:
        return None

    try:
        if "/" in prazo_final:
            dt_prazo = datetime.strptime(prazo_final, "%d/%m/%Y")
        elif "-" in prazo_final:
            dt_prazo = datetime.strptime(prazo_final, "%Y-%m-%d")
        else:
            return None

        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        diff = dt_prazo - hoje
        return diff.days
    except (ValueError, TypeError):
        return None


def _classificar_status(status_ml: str, substatus_ml: str, dias_restantes: Optional[int]) -> str:
    """Classifica o status do prazo."""
    status_lower = (status_ml or "").lower()

    if status_lower == "delivered":
        return "Entregue"

    if status_lower in ("cancelled", "not_delivered"):
        return "Cancelado"

    if status_lower in ("error", "not_verified"):
        return "Erro"

    if status_lower in ("closed",):
        return "Fechado"

    if dias_restantes is None:
        return "Sem Prazo"

    if dias_restantes < 0:
        return "Atrasado"

    if dias_restantes <= 1:
        return "Em Risco"

    if dias_restantes <= 3:
        return "Atenção"

    return "No Prazo"


def gerar_resumo(pedidos: list) -> dict:
    """Gera resumo dos pedidos para o dashboard."""
    total = len(pedidos)
    por_status = {}
    por_transportadora = {}
    por_uf = {}
    em_risco = []
    atrasados = []

    for p in pedidos:
        status = p.get("status_prazo", "Sem Prazo")
        por_status[status] = por_status.get(status, 0) + 1

        transp = p.get("transportadora", "") or "Não informada"
        por_transportadora[transp] = por_transportadora.get(transp, 0) + 1

        uf = p.get("uf_destino", "") or "N/A"
        por_uf[uf] = por_uf.get(uf, 0) + 1

        if status in ("Em Risco", "Atenção"):
            em_risco.append(p)
        elif status == "Atrasado":
            atrasados.append(p)

    return {
        "total": total,
        "por_status": por_status,
        "por_transportadora": por_transportadora,
        "por_uf": por_uf,
        "em_risco": em_risco,
        "atrasados": atrasados,
        "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
