"""Funções de formatação para o dashboard."""

from datetime import datetime


def formatar_data_br(data_str: str) -> str:
    """Converte data ISO para formato brasileiro."""
    if not data_str:
        return "-"

    try:
        if "T" in data_str:
            dt = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y %H:%M")
        elif "/" in data_str:
            return data_str
        elif "-" in data_str:
            dt = datetime.strptime(data_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        return data_str
    except (ValueError, TypeError):
        return data_str


def formatar_valor(valor) -> str:
    """Formata valor em reais."""
    if valor is None or valor == "":
        return "-"

    try:
        valor_float = float(valor)
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(valor)


def formatar_dias(dias) -> str:
    """Formata quantidade de dias."""
    if dias is None:
        return "-"

    try:
        dias_int = int(dias)
        if dias_int < 0:
            return f"{abs(dias_int)}d atrasado"
        elif dias_int == 0:
            return "Vence hoje"
        elif dias_int == 1:
            return "1 dia"
        else:
            return f"{dias_int} dias"
    except (ValueError, TypeError):
        return str(dias)


def truncar_texto(texto: str, max_len: int = 30) -> str:
    """Trunga texto longo."""
    if not texto:
        return "-"
    if len(texto) <= max_len:
        return texto
    return texto[:max_len - 3] + "..."
