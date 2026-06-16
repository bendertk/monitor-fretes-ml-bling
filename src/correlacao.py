"""Correlação entre pedidos ML e Bling."""

from typing import Optional
from src.bling_api import extrair_numero_loja_pedido


def correlacionar_pedidos(pedidos_ml: list, pedidos_bling: list) -> list:
    """
    Correlaciona pedidos ML com pedidos Bling.
    
    Busca por: numeroLoja, numeroPedidoLoja, ou numero
    """
    mapa_bling = {}
    for p in pedidos_bling:
        numero_loja = _extrair_todos_numeros(p)
        for num in numero_loja:
            if num:
                mapa_bling[str(num).strip()] = p

    pedidos_enriquecidos = []

    for ml_order in pedidos_ml:
        order_id = str(ml_order.get("order_id", "")).strip()
        pedido_bling = mapa_bling.get(order_id)

        enriquecido = {
            "order_id_ml": order_id,
            "shipment_id_ml": ml_order.get("shipment_id"),
            "status_ml": ml_order.get("status"),
            "substatus_ml": ml_order.get("substatus"),
            "tracking_number": ml_order.get("tracking_number"),
            "carrier_name_ml": ml_order.get("carrier_name"),
            "logistic_mode": ml_order.get("logistic_mode"),
            "date_created": ml_order.get("date_created"),
            "last_updated": ml_order.get("last_updated"),
            "lead_time": ml_order.get("lead_time"),
            "total_amount": ml_order.get("total_amount"),
            "order_items": ml_order.get("order_items", []),
            "buyer": ml_order.get("buyer", {}),
            "tags": ml_order.get("tags", []),
            "numero_pedido_bling": "",
            "numero_nf": "",
            "transportadora": "",
            "data_faturamento": "",
            "destinatario": "",
            "cidade_destino": "",
            "uf_destino": "",
            "valor_pedido": "",
            "tem_bling": False,
        }

        if pedido_bling:
            enriquecido["tem_bling"] = True
            enriquecido["numero_pedido_bling"] = str(pedido_bling.get("numero", ""))
            enriquecido["numero_nf"] = _extrair_numero_nf(pedido_bling)
            enriquecido["transportadora"] = _extrair_transportadora(pedido_bling)
            enriquecido["data_faturamento"] = pedido_bling.get("data", "")

            contato = pedido_bling.get("contato", {})
            if contato:
                enriquecido["destinatario"] = contato.get("nome", "")
                endereco = _extrair_endereco(pedido_bling)
                enriquecido["cidade_destino"] = endereco.get("cidade", "")
                enriquecido["uf_destino"] = endereco.get("uf", "")

            itens = pedido_bling.get("itens", [])
            if itens:
                total = sum(
                    float(item.get("valor", 0)) * int(item.get("quantidade", 1))
                    for item in itens
                )
                enriquecido["valor_pedido"] = str(total)

        pedidos_enriquecidos.append(enriquecido)

    return pedidos_enriquecidos


def _extrair_todos_numeros(pedido: dict) -> list:
    """Extrai todos os números possíveis de identificação do pedido."""
    numeros = []
    
    numero_loja = pedido.get("numeroLoja", "")
    if numero_loja:
        numeros.append(str(numero_loja).strip())
    
    numero_pedido_loja = pedido.get("numeroPedidoLoja", "")
    if numero_pedido_loja:
        numeros.append(str(numero_pedido_loja).strip())
    
    numero = pedido.get("numero", "")
    if numero:
        numeros.append(str(numero).strip())
    
    return numeros


def _extrair_numero_nf(pedido: dict) -> str:
    """Extrai número da NF do pedido Bling."""
    nf = pedido.get("nf", {})
    if nf:
        return str(nf.get("numero", ""))

    nfe = pedido.get("nfe", {})
    if nfe:
        return str(nfe.get("numero", ""))

    return ""


def _extrair_transportadora(pedido: dict) -> str:
    """Extrai transportadora do pedido Bling."""
    transporte = pedido.get("transporte", {})
    if not transporte:
        return ""

    transportadora = transporte.get("transportadora", {})
    if transportadora:
        return transportadora.get("nome", "")

    return ""


def _extrair_endereco(pedido: dict) -> dict:
    """Extrai cidade/UF do destinatário."""
    contato = pedido.get("contato", {})
    if not contato:
        return {"cidade": "", "uf": ""}

    endereco = contato.get("endereco", {})
    if not endereco:
        return {"cidade": "", "uf": ""}

    return {
        "cidade": endereco.get("cidade", ""),
        "uf": endereco.get("uf", ""),
    }
