"""Script principal - Sincronização diária ML ↔ Bling."""

import sys
import os
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml_api import get_access_token as get_ml_token, get_me1_orders
from src.bling_api import (
    get_access_token as get_bling_token,
    get_all_pedidos_faturados,
    get_all_pedidos_recentes,
    get_all_nfe_saida,
    enriquecer_pedidos_com_nfe,
    enrichir_pedidos_detalhes,
)
from src.correlacao import correlacionar_pedidos
from src.calculo_prazo import calcular_prazos, gerar_resumo
from src.sheets_api import setup_sheet, upsert_pedido, write_log, read_all_pedidos


def run_sync(days_back: int = 15):
    """Executa a sincronização completa."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando sincronização...")

    errors = []

    try:
        setup_sheet()
        print("  ✓ Planilha configurada")
    except Exception as e:
        errors.append(f"Setup planilha: {str(e)}")
        print(f"  ✗ Erro ao configurar planilha: {e}")

    print("\n[1/5] Buscando token ML...")
    try:
        ml_token = get_ml_token()
        print("  ✓ Token ML obtido")
    except Exception as e:
        errors.append(f"Token ML: {str(e)}")
        print(f"  ✗ Erro ao obter token ML: {e}")
        ml_token = None

    print("\n[2/5] Buscando pedidos ML (ME1)...")
    pedidos_ml = []
    if ml_token:
        try:
            pedidos_ml = get_me1_orders(ml_token, days_back)
            print(f"  ✓ {len(pedidos_ml)} pedidos ME1 encontrados")
        except Exception as e:
            errors.append(f"Pedidos ML: {str(e)}")
            print(f"  ✗ Erro ao buscar pedidos ML: {e}")

    print("\n[3/5] Buscando token Bling...")
    try:
        bling_token = get_bling_token()
        print("  ✓ Token Bling obtido")
    except Exception as e:
        errors.append(f"Token Bling: {str(e)}")
        print(f"  ✗ Erro ao obter token Bling: {e}")
        bling_token = None

    print("\n[4/5] Buscando pedidos recentes no Bling...")
    pedidos_bling = []
    if bling_token:
        try:
            pedidos_bling = get_all_pedidos_recentes(bling_token, days_back)
            print(f"  ✓ {len(pedidos_bling)} pedidos Bling encontrados")
        except Exception as e:
            errors.append(f"Pedidos Bling: {str(e)}")
            print(f"  ✗ Erro ao buscar pedidos Bling: {e}")

    print("\n[4.1] Buscando NF de saída no Bling...")
    nfe_list = []
    if bling_token:
        try:
            nfe_list = get_all_nfe_saida(bling_token, days_back)
            print(f"  ✓ {len(nfe_list)} NF de saída encontradas")
        except Exception as e:
            errors.append(f"NF Bling: {str(e)}")
            print(f"  ✗ Erro ao buscar NF: {e}")

    if bling_token and pedidos_bling:
        try:
            pedidos_bling = enriquecer_pedidos_com_nfe(bling_token, pedidos_bling, nfe_list)
            print(f"  ✓ Pedidos enriquecidos com dados NF")
        except Exception as e:
            print(f"  ✗ Erro ao enriquecer com NF: {e}")

    print("\n[5/5] Correlacionando e calculando prazos...")
    pedidos_enriquecidos = correlacionar_pedidos(pedidos_ml, pedidos_bling)
    print(f"  ✓ {len(pedidos_enriquecidos)} pedidos correlacionados")

    if bling_token:
        try:
            pedidos_bling_map = {}
            for p in pedidos_bling:
                num = str(p.get("numero", "")).strip()
                if num:
                    pedidos_bling_map[num] = p
            matched = [p for p in pedidos_enriquecidos if p.get("tem_bling")]
            if matched:
                print(f"  ↳ Buscando detalhes de {len(matched)} pedidos Bling...")
                import time as _time
                for i, p in enumerate(matched):
                    bling_num = p.get("numero_pedido_bling", "")
                    bling_data = pedidos_bling_map.get(bling_num, {})
                    pedido_id = bling_data.get("id")
                    if pedido_id:
                        try:
                            from src.bling_api import get_pedido_venda
                            detalhe = get_pedido_venda(bling_token, int(pedido_id))
                            if detalhe:
                                pd = detalhe.get("data", detalhe)
                                nf = pd.get("nf")
                                if nf:
                                    p["numero_nf"] = str(nf.get("numero", ""))
                                transp = pd.get("transporte", {}).get("transportadora")
                                if transp:
                                    p["transportadora"] = transp.get("nome", "")
                                contato = pd.get("contato", {})
                                if contato:
                                    if not p["destinatario"]:
                                        p["destinatario"] = contato.get("nome", "")
                                    end = contato.get("endereco", {})
                                    if end:
                                        if not p["cidade_destino"]:
                                            p["cidade_destino"] = end.get("cidade", "")
                                        if not p["uf_destino"]:
                                            p["uf_destino"] = end.get("uf", "")
                                if i < 3:
                                    print(f"    ✓ {bling_num}: NF={p['numero_nf']}, Transp={p['transportadora']}, UF={p['uf_destino']}")
                            _time.sleep(0.15)
                        except Exception as e:
                            if i < 3:
                                print(f"    ✗ {bling_num}: {e}")
                print(f"  ✓ Detalhes obtidos para {len(matched)} pedidos")
        except Exception as e:
            print(f"  ✗ Erro ao buscar detalhes: {e}")

    for pedido in pedidos_enriquecidos:
        calcular_prazos(pedido)

    print("\n[6/6] Atualizando Google Sheets...")
    erros_upsert = 0
    for pedido in pedidos_enriquecidos:
        try:
            upsert_pedido(pedido)
        except Exception as e:
            erros_upsert += 1
            errors.append(f"Upsert pedido {pedido.get('order_id_ml')}: {str(e)}")
            print(f"  ✗ Erro ao atualizar pedido {pedido.get('order_id_ml')}: {e}")

    if erros_upsert == 0:
        print(f"  ✓ {len(pedidos_enriquecidos)} pedidos atualizados na planilha")

    resumo = gerar_resumo(pedidos_enriquecidos)

    log_detalhes = (
        f"ML: {len(pedidos_ml)} pedidos | "
        f"Bling: {len(pedidos_bling)} faturados | "
        f"Correlacionados: {len(pedidos_enriquecidos)} | "
        f"Erros upsert: {erros_upsert}"
    )

    write_log(
        tipo_operacao="SYNC_DIARIO",
        registros=len(pedidos_enriquecidos),
        erros="; ".join(errors) if errors else "",
        detalhes=log_detalhes,
    )

    print("\n" + "=" * 50)
    print("RESUMO DA SINCRONIZAÇÃO")
    print("=" * 50)
    print(f"  Total de pedidos: {resumo['total']}")
    for status, count in resumo["por_status"].items():
        print(f"  {status}: {count}")
    print(f"\n  Por transportadora:")
    for transp, count in resumo["por_transportadora"].items():
        print(f"    {transp}: {count}")

    if resumo["em_risco"]:
        print(f"\n  ⚠️  {len(resumo['em_risco'])} pedidos em risco de atraso!")
    if resumo["atrasados"]:
        print(f"  ❌ {len(resumo['atrasados'])} pedidos já atrasados!")

    if errors:
        print(f"\n  ⚠️  {len(errors)} erros durante a sincronização:")
        for err in errors:
            print(f"    - {err}")

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sincronização concluída!")
    return resumo


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sincronizar ML ↔ Bling")
    parser.add_argument("--days", type=int, default=15, help="Dias para buscar")
    args = parser.parse_args()

    run_sync(days_back=args.days)
