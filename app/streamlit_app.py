"""Dashboard de Monitoramento de Fretes - Streamlit."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.sheets_api import read_all_pedidos
from src.calculo_prazo import gerar_resumo

st.set_page_config(
    page_title="Monitor de Fretes",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

AUTO_REFRESH_INTERVAL = 300

if time.time() - st.session_state.last_refresh > AUTO_REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.cache_data.clear()

st.markdown("""
<style>
    .status-no-prazo { color: #28a745; font-weight: bold; }
    .status-em-risco { color: #ffc107; font-weight: bold; }
    .status-atencao { color: #fd7e14; font-weight: bold; }
    .status-atrasado { color: #dc3545; font-weight: bold; }
    .status-entregue { color: #6c757d; font-weight: bold; }

    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .kpi-card h2 { margin: 0; font-size: 2.5rem; }
    .kpi-card p { margin: 5px 0 0 0; font-size: 0.9rem; opacity: 0.9; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    """Carrega dados do Google Sheets."""
    try:
        pedidos = read_all_pedidos()
        return pedidos
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return []


def get_status_color(status):
    """Retorna cor baseada no status."""
    colors = {
        "No Prazo": "#28a745",
        "Em Risco": "#ffc107",
        "Atenção": "#fd7e14",
        "Atrasado": "#dc3545",
        "Entregue": "#6c757d",
        "Cancelado": "#343a40",
        "Sem Prazo": "#17a2b8",
        "Erro": "#dc3545",
        "Fechado": "#6c757d",
    }
    return colors.get(status, "#6c757d")


def main():
    col_title, col_refresh = st.columns([4, 1])

    with col_title:
        st.title("🚚 Monitor de Fretes - ML ↔ Bling")
        st.caption("Sollar Sul | Monitoramento de prazos de entrega")

    with col_refresh:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.session_state.last_refresh = time.time()
            st.rerun()

    auto_refresh_msg = f"Auto-refresh a cada {AUTO_REFRESH_INTERVAL // 60} min | Última atualização: {datetime.now().strftime('%H:%M:%S')}"
    st.caption(auto_refresh_msg)

    pedidos = load_data()

    if not pedidos:
        st.warning("Nenhum dado encontrado. Execute a sincronização primeiro.")
        return

    resumo = gerar_resumo(pedidos)

    st.subheader("📊 Visão Geral")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = resumo["total"]
        st.metric("📦 Total de Pedidos", total)

    with col2:
        no_prazo = resumo["por_status"].get("No Prazo", 0)
        st.metric("✅ No Prazo", no_prazo)

    with col3:
        em_risco = resumo["por_status"].get("Em Risco", 0) + resumo["por_status"].get("Atenção", 0)
        st.metric("⚠️ Em Risco", em_risco)

    with col4:
        atrasados = resumo["por_status"].get("Atrasado", 0)
        st.metric("❌ Atrasados", atrasados)

    if resumo["em_risco"]:
        st.warning(f"⚠️ **{len(resumo['em_risco'])} pedidos** estão em risco de atraso! Verifique a aba de detalhes.")
    if resumo["atrasados"]:
        st.error(f"❌ **{len(resumo['atrasados'])} pedidos** já estão atrasados!")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📋 Pedidos por Status")
        status_data = pd.DataFrame(
            list(resumo["por_status"].items()),
            columns=["Status", "Quantidade"]
        )
        if not status_data.empty:
            fig_status = px.pie(
                status_data,
                values="Quantidade",
                names="Status",
                color="Status",
                color_discrete_map={s: get_status_color(s) for s in status_data["Status"]},
                hole=0.4,
            )
            fig_status.update_layout(
                height=350,
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),
            )
            st.plotly_chart(fig_status, use_container_width=True)

    with col_right:
        st.subheader("🚚 Pedidos por Transportadora")
        transp_data = pd.DataFrame(
            list(resumo["por_transportadora"].items()),
            columns=["Transportadora", "Quantidade"]
        )
        if not transp_data.empty:
            fig_transp = px.bar(
                transp_data.sort_values("Quantidade", ascending=True),
                x="Quantidade",
                y="Transportadora",
                orientation="h",
                color="Quantidade",
                color_continuous_scale="viridis",
            )
            fig_transp.update_layout(
                height=350,
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=False,
            )
            st.plotly_chart(fig_transp, use_container_width=True)

    st.divider()

    st.subheader("📋 Detalhe dos Pedidos")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
        filtro_status = st.multiselect(
            "Filtrar por Status",
            options=sorted(set(p.get("status_prazo", "") for p in pedidos if p.get("status_prazo"))),
            default=[],
        )

    with col_f2:
        filtro_transp = st.multiselect(
            "Filtrar por Transportadora",
            options=sorted(set(p.get("transportadora", "") for p in pedidos if p.get("transportadora"))),
            default=[],
        )

    with col_f3:
        filtro_uf = st.multiselect(
            "Filtrar por UF",
            options=sorted(set(p.get("uf_destino", "") for p in pedidos if p.get("uf_destino"))),
            default=[],
        )

    with col_f4:
        buscar = st.text_input("🔍 Buscar por NF, ML# ou destinatário")

    pedidos_filtrados = pedidos.copy()

    if filtro_status:
        pedidos_filtrados = [p for p in pedidos_filtrados if p.get("status_prazo") in filtro_status]

    if filtro_transp:
        pedidos_filtrados = [p for p in pedidos_filtrados if p.get("transportadora") in filtro_transp]

    if filtro_uf:
        pedidos_filtrados = [p for p in pedidos_filtrados if p.get("uf_destino") in filtro_uf]

    if buscar:
        buscar_lower = buscar.lower()
        pedidos_filtrados = [
            p for p in pedidos_filtrados
            if buscar_lower in (p.get("numero_nf", "") or "").lower()
            or buscar_lower in (p.get("order_id_ml", "") or "").lower()
            or buscar_lower in (p.get("destinatario", "") or "").lower()
            or buscar_lower in (p.get("numero_pedido_bling", "") or "").lower()
        ]

    if pedidos_filtrados:
        df = pd.DataFrame(pedidos_filtrados)

        colunas_exibir = [
            "order_id_ml",
            "numero_nf",
            "transportadora",
            "status_prazo",
            "prazo_final",
            "dias_restantes",
            "destinatario",
            "uf_destino",
            "status_ml",
        ]

        colunas_existentes = [c for c in colunas_exibir if c in df.columns]

        df_exibir = df[colunas_existentes].copy()

        rename_map = {
            "order_id_ml": "Pedido ML",
            "numero_nf": "NF",
            "transportadora": "Transportadora",
            "status_prazo": "Status Prazo",
            "prazo_final": "Prazo Final",
            "dias_restantes": "Dias Restantes",
            "destinatario": "Destinatário",
            "uf_destino": "UF",
            "status_ml": "Status ML",
        }
        df_exibir.rename(columns=rename_map, inplace=True)

        def highlight_status(row):
            styles = [""] * len(row)
            if "Status Prazo" in row.index:
                status = row["Status Prazo"]
                color = get_status_color(status)
                styles[row.index.get_loc("Status Prazo")] = f"color: {color}; font-weight: bold"
            return styles

        st.dataframe(
            df_exibir.style.apply(highlight_status, axis=1),
            height=500,
            use_container_width=True,
        )

        st.caption(f"Mostrando {len(pedidos_filtrados)} de {len(pedidos)} pedidos")
    else:
        st.info("Nenhum pedido encontrado com os filtros selecionados.")

    st.divider()

    st.subheader("📈 Pedidos por UF")
    uf_data = pd.DataFrame(
        list(resumo["por_uf"].items()),
        columns=["UF", "Quantidade"]
    )
    if not uf_data.empty:
        fig_uf = px.bar(
            uf_data.sort_values("Quantidade", ascending=False),
            x="UF",
            y="Quantidade",
            color="Quantidade",
            color_continuous_scale="blues",
        )
        fig_uf.update_layout(
            height=300,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
        )
        st.plotly_chart(fig_uf, use_container_width=True)

    st.divider()
    st.caption(f"Última atualização: {resumo['ultima_atualizacao']}")
    st.caption("Desenvolvido por IsRa Bot | Sollar Sul")


if __name__ == "__main__":
    main()
