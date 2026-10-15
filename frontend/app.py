import os

import httpx
import pandas as pd
import streamlit as st
from api_client import CrmApiClient

st.set_page_config(page_title="Inteligência de CRM", page_icon="✈️", layout="wide")
st.title("✈️ Inteligência de CRM")
st.caption("Protótipo privado • Hacka Business • Azul + Avanade")
st.warning(
    "Demonstração com dados fictícios e scores heurísticos. Risco sem calibração; "
    "não há modelo treinado, regras oficiais de fidelidade ou LLM conectado."
)
api = CrmApiClient(os.getenv("CRM_API_URL", "http://127.0.0.1:8000"))
try:
    metadata = api.metadata()
    with st.expander("Como interpretar esta demonstração"):
        st.write("Objetivo: priorizar clientes estratégicos e apoiar uma ação de relacionamento.")
        st.write(f"Observação: {metadata['observation_start']} a {metadata['observation_end']}.")
        policy = metadata["scoring_policy"]
        st.write(
            f"Alto valor: score ≥ {policy['high_value_threshold']}; "
            f"risco alto: índice ≥ {policy['high_risk_threshold']}."
        )
        st.caption(
            "Churn futuro: zero viagens nos seis meses seguintes, na configuração padrão. "
            "Contrato planejado; rótulos e modelo ainda não gerados. "
            "A recomendação atual usa documentos fictícios e template."
        )
    rows = api.priorities()
    if not rows:
        st.info("Nenhum cliente disponível.")
        st.stop()
    df = pd.DataFrame(rows)
    segments = st.sidebar.multiselect("Segmentos", sorted(df.segment.unique()))
    view = df[df.segment.isin(segments)] if segments else df
    a, b, c = st.columns(3)
    a.metric("Clientes no recorte", len(view))
    b.metric("Valor médio (score)", f"{view.value_score.mean():.1f}" if len(view) else "—")
    c.metric("Índice médio de risco", f"{view.churn_risk.mean():.0%}" if len(view) else "—")
    overview, detail, agent = st.tabs(["Priorização", "Cliente 360", "Recomendação"])
    with overview:
        st.dataframe(view.drop(columns=["drivers"]), hide_index=True, width="stretch")
        st.caption(
            "Prioridade = valor × índice de risco. Valor em risco usa gasto passado × risco; não é CLV."
        )
        st.bar_chart(view.groupby("segment").size())
    if view.empty:
        st.info("O filtro não retornou clientes.")
        st.stop()
    selected = st.sidebar.selectbox("Cliente", view.customer_id.tolist())
    customer = api.customer(selected)
    with detail:
        st.subheader(selected)
        st.json(customer["customer"])
        st.write("**Motivos dos scores**")
        for driver in customer["scores"]["drivers"]:
            st.write("• " + driver)
        st.caption("Versão: " + customer["scores"]["model_version"])
        st.dataframe(pd.DataFrame(customer["trips"]), hide_index=True, width="stretch")
    with agent:
        st.caption("Gerador de texto por template e recuperação lexical de uma fixture interna.")
        if st.button("Gerar rascunho para revisão", type="primary"):
            result = api.recommend(selected)
            st.subheader(result["action"]["title"])
            st.write(result["action"]["reason"])
            st.info(result["draft"])
            for evidence in result["evidence"]:
                with st.expander(evidence["title"]):
                    st.write(evidence["text"])
                    st.caption(f"Fonte: {evidence['source']} | versão {evidence['version']}")
            st.caption("Status: " + result["status"] + " • Nenhuma mensagem foi enviada.")
except httpx.HTTPError:
    st.error(
        "Não foi possível consultar a API. Confirme se o pipeline foi executado e "
        "se o FastAPI está ativo no endereço configurado em CRM_API_URL."
    )
