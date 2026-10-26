import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
import plotly.express as px
import streamlit as st
from gateway import Gateway

st.set_page_config(page_title="Azul | CRM Intelligence", page_icon="✈", layout="wide")
st.markdown(
    """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp {font-family:Inter,Arial,sans-serif;color:#0a244b}
.stApp {background:#f3f8fd} header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:2rem;padding-bottom:2rem;max-width:1680px}
[data-testid="stSidebar"]{background:linear-gradient(165deg,#03254c,#031d3d);color:white;min-width:235px;max-width:235px}
[data-testid="stSidebar"] *{color:#e1efff} [data-testid="stSidebar"] label{font-size:15px}
[data-testid="stSidebar"] .stRadio>div{gap:18px}
h1{font-size:2rem!important;letter-spacing:-.8px;color:#08234c} h2,h3{color:#08234c}
.hero-sub{color:#527098;margin-top:-12px;font-size:16px;margin-bottom:22px}
.badge{font-size:12px;background:#e7f0fa;padding:9px 14px;border-radius:20px;color:#456183;display:inline-block}
.brand{font-size:48px;font-weight:800;letter-spacing:-2px;color:white;padding-top:8px}
.brand-sub{color:#9fbbd6;font-size:14px;margin-bottom:45px}
.kpi{background:white;border:1px solid #e0edf9;border-radius:13px;padding:23px 20px;min-height:142px;box-shadow:0 3px 14px #123e6505;margin-bottom:20px}
.kpi .label{font-size:13px;font-weight:600}.kpi .value{font-size:30px;font-weight:800;margin:8px 0 3px}.kpi .sub{font-size:12px;color:#6982a3}
.kpi .icon{float:left;width:45px;height:45px;background:#e7f5ff;color:#008ff2;border-radius:50%;text-align:center;line-height:45px;margin-right:14px;font-size:22px}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#e0edf9!important;background:white;border-radius:12px}
.stButton>button[kind="primary"]{background:#087bfa;border:0;color:#fff} .stButton>button{border-radius:7px}
.stButton>button[kind="primary"]:disabled{background:#c9d6e6;cursor:not-allowed}
.stButton>button[kind="primary"]:disabled *{color:#5d7390!important}
.stButton>button[kind="primary"]:not(:disabled) *{color:#fff!important}
[data-testid="stSidebar"] .stButton>button *{color:#08234c!important}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"],[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"]>div{background:#0b3a6e!important;border-color:#2f6aa8!important}
[data-testid="stSidebar"] [data-testid="stSelectbox"] input{color:#e1efff!important;-webkit-text-fill-color:#e1efff!important;opacity:1!important}
.action{background:#eaf5ff;border-radius:10px;padding:16px;margin-bottom:14px;color:#0068df}
.small{font-size:12px;color:#6380a4}.factors{background:#fff2f3;color:#bf3844;padding:12px;border-radius:9px;font-size:13px;margin:8px 0}
[data-testid="stMetric"]{background:#f6faff;border:1px solid #e6eff8;border-radius:10px;padding:12px}
</style>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="brand">✈ azul</div><div class="brand-sub">CRM Intelligence</div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navegação",
        [
            "Visão geral",
            "Clientes",
            "Segmentos",
            "Ações de CRM",
            "Assistente IA",
            "Sentimento",
            "Auditoria de viés",
            "Dados e modelos",
        ],
        label_visibility="collapsed",
    )
    st.markdown(
        '<br><br><br><div class="small">HACKATHON · MVP PRIVADO<br>Inteligência que aproxima.</div>',
        unsafe_allow_html=True,
    )
    if st.button("Atualizar dados"):
        st.cache_resource.clear()
        st.rerun()


@st.cache_resource
def gateway():
    return Gateway()


def money(x):
    return "R$ " + f"{x:,.0f}".replace(",", ".")


def evidence_ui(evidence):
    for e in evidence:
        with st.expander(e["title"] + (" · demonstrativo" if e["is_demo"] else " · fonte pública")):
            st.write(e["text"])
            st.caption(e["source"] + " | " + e["version"])


def ask_ui(api, cid):
    with st.form("chat"):
        question = st.text_input(
            "Pergunte sobre a carteira ou metodologia",
            placeholder="Por que este cliente está em risco?",
        )
        submit = st.form_submit_button("Consultar fontes", type="primary")
    if submit and question:
        with st.spinner("Consultando indicadores e evidências…"):
            result = api.ask(question, cid)
        st.write(result["answer"])
        st.caption("Modo: " + result["mode"])
        evidence_ui(result["evidence"])


try:
    with st.spinner("Carregando a carteira…"):
        api = gateway()
        meta = api.metadata()
        full = api.dashboard()
    h1, h2 = st.columns([4, 1])
    with h1:
        st.title("Inteligência para cuidar de quem mais importa")
        st.markdown(
            '<div class="hero-sub">Priorize clientes, entenda os sinais e transforme dados em relacionamento.</div>',
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            '<span class="badge">Demonstração · Dados sintéticos</span>', unsafe_allow_html=True
        )
    if not full["rows"]:
        st.info("Nenhum cliente com viagens na janela. Execute o gerador e atualize os dados.")
        st.stop()
    f1, f2, f3 = st.columns([1, 1, 1.2])
    months = f1.selectbox(
        "Período de viagens", [12, 6, 3], format_func=lambda n: f"Últimos {n} meses"
    )
    segment = f2.selectbox("Segmento", ["Todos"] + sorted({r["segment"] for r in full["rows"]}))
    route = f3.selectbox("Rota", ["Todas"] + sorted({r["route"] for r in full["rows"]}))
    seg = None if segment == "Todos" else segment
    rt = None if route == "Todas" else route
    data = api.dashboard(months, seg, rt)
    df = pd.DataFrame(data["rows"])
    if df.empty:
        st.info(
            "Nenhum cliente corresponde a esses filtros. Amplie o período ou remova os filtros."
        )
        st.stop()
    cid = st.sidebar.selectbox("Cliente em foco", df.customer_id.tolist())
    focus = next(r for r in data["rows"] if r["customer_id"] == cid)
    k = data["kpis"]
    share = meta.get("clv_policy", {}).get("top_share", 0.2)
    labels = [
        (
            "♟",
            "Clientes de alto valor",
            str(k["high_value"]),
            f"top {share:.0%} por valor potencial",
        ),
        ("△", "Alto valor em risco", str(k["high_value_at_risk"]), "prioridade de retenção"),
        ("▥", "CLV 12 meses (margem)", money(k["clv_12m"]), "margem esperada, com desconto"),
        ("◉", "CLV em risco", money(k["clv_at_risk"]), "margem que se perde se saírem"),
    ]
    for col, (icon, label, val, sub) in zip(st.columns(4), labels):
        col.markdown(
            f'<div class="kpi"><span class="icon">{icon}</span><div class="label">{label}</div><div class="value">{val}</div><div class="sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )
    if page == "Visão geral":
        left, right = st.columns([1.38, 1])
        with left, st.container(border=True):
            st.subheader("Onde concentrar os esforços?")
            st.caption(
                "Valor potencial (margem em 12 meses) × risco de evasão · divisória = corte do alto valor"
            )
            threshold = meta["scoring_policy"]["high_risk_threshold"]
            value_threshold = k["high_value_cutoff"]
            ymax = max(float(df["potential_value_12m"].max()), value_threshold) * 1.08
            fig = px.scatter(
                df,
                x="churn_risk",
                y="potential_value_12m",
                color="segment",
                hover_name="customer_id",
                hover_data=["clv_12m", "route"],
                color_discrete_sequence=["#ff6670", "#00bc9c", "#13b9d4", "#078afa"],
            )
            for x0, x1, y0, y1, color in [
                (0, threshold, value_threshold, ymax, "#eaf5ff"),
                (threshold, 1, value_threshold, ymax, "#fff0f2"),
                (0, threshold, 0, value_threshold, "#eafaf5"),
                (threshold, 1, 0, value_threshold, "#fff7df"),
            ]:
                fig.add_shape(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    fillcolor=color,
                    line_width=0,
                    layer="below",
                )
            fig.add_scatter(
                x=[focus["churn_risk"]],
                y=[focus["potential_value_12m"]],
                mode="markers",
                showlegend=False,
                marker={
                    "size": 19,
                    "color": "rgba(0,0,0,0)",
                    "line": {"width": 2, "color": "#08234c"},
                },
                hoverinfo="skip",
            )
            for x, y, t, color in [
                (0.04, 0.96 * ymax, "Encantar", "#0079f3"),
                (0.96, 0.96 * ymax, "Reter agora", "#ef465d"),
                (0.04, 0.05 * ymax, "Nutrir", "#00a88a"),
                (0.96, 0.05 * ymax, "Reativar", "#ce9205"),
            ]:
                fig.add_annotation(
                    x=x,
                    y=y,
                    text=t,
                    showarrow=False,
                    font={"size": 14, "color": color},
                    xanchor="left" if x < 0.5 else "right",
                )
            fig.update_layout(
                height=390,
                margin=dict(l=10, r=10, t=10, b=5),
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                font={"color": "#496384"},
                xaxis_title="Risco de evasão →",
                yaxis_title="Valor potencial 12 meses (margem, R$) →",
            )
            fig.update_xaxes(range=[0, 1], tickformat=".0%", gridcolor="#edf2f7")
            fig.update_yaxes(range=[0, ymax], gridcolor="#edf2f7")
            st.plotly_chart(fig, width="stretch")
        with right, st.container(border=True):
            st.subheader("Próxima melhor ação")
            st.markdown("**" + cid + " · " + focus["segment"] + "**")
            st.caption("Cliente sintético · " + focus["route"])
            a, b = st.columns(2)
            a.metric("Valor", f"{focus['value_score']:.0f}/100")
            b.metric("Risco", f"{focus['churn_risk']:.0%}")
            st.caption(
                f"CLV 12m: {money(focus['clv_12m'])} · "
                + ("alto valor" if focus["is_high_value"] else "fora do grupo de alto valor")
            )
            st.markdown("**Principais fatores**")
            for driver in focus["drivers"][:3]:
                st.markdown(
                    '<div class="factors">' + escape(driver) + "</div>", unsafe_allow_html=True
                )
            rec = api.recommend(cid)
            st.markdown(
                '<div class="action"><b>'
                + escape(rec["action"]["title"])
                + '</b><br><span class="small">'
                + escape(rec["action"]["reason"])
                + "</span></div>",
                unsafe_allow_html=True,
            )
            with st.expander("Ver evidências e regras"):
                evidence_ui(rec["evidence"])
            if st.button("Gerar mensagem para revisão", type="primary", width="stretch"):
                st.info(rec["draft"])
                if rec.get("review_checklist"):
                    st.caption(
                        "Antes de qualquer contato, confirme o consentimento de comunicação "
                        "do cliente (Regulamento do Azul Fidelidade, item 3.6). "
                        "A revisão completa fica em Ações de CRM."
                    )
        left, right = st.columns([1.6, 1])
        with left, st.container(border=True):
            st.subheader("Quem precisa de atenção agora?")
            st.caption("Ordenado por prioridade · seleção no menu lateral")
            table = df[["customer_id", "segment", "clv_12m", "churn_risk", "priority_score"]].head(
                8
            )
            st.dataframe(
                table,
                hide_index=True,
                width="stretch",
                column_config={
                    "customer_id": "Cliente",
                    "segment": "Segmento",
                    "clv_12m": st.column_config.NumberColumn("CLV 12m (margem)", format="R$ %.0f"),
                    "churn_risk": st.column_config.ProgressColumn(
                        "Risco", min_value=0, max_value=1, format="%.2f"
                    ),
                    "priority_score": "Prioridade",
                },
            )
        with right, st.container(border=True):
            st.subheader("✧ Copiloto de CRM")
            ask_ui(api, cid)
    elif page == "Clientes":
        st.subheader("Visão 360 · " + cid)
        detail = api.customer(cid)
        st.write("**Fatores:**")
        for driver in detail["scores"]["drivers"]:
            st.markdown("- " + driver)
        trips = pd.DataFrame(detail["trips"])
        st.dataframe(trips, hide_index=True, width="stretch")
        st.subheader("Fidelidade simulada")
        loyalty = api.loyalty(cid)
        if loyalty:
            o, a, b, c = st.columns(4)
            o.metric("Saldo inicial (simulado)", loyalty["opening_points"])
            a.metric("Pontos acumulados", loyalty["earned"])
            b.metric("Pontos resgatados", loyalty["redeemed"])
            c.metric("Saldo", loyalty["balance"])
            st.caption(
                "Saldo = saldo inicial simulado + acumulados − resgatados. O acúmulo segue 1 ponto por "
                "real (Regulamento do Azul Fidelidade, item 5.5.3); resgates e saldo inicial são "
                "simulados. Tier: " + loyalty["tier"] + " · sem elegibilidade oficial inferida"
            )
            st.dataframe(pd.DataFrame(loyalty["transactions"]), hide_index=True, width="stretch")
    elif page == "Segmentos":
        st.subheader("Perfis e oportunidades")
        agg = df.groupby("segment", as_index=False).agg(
            clientes=("customer_id", "count"),
            valor=("clv_12m", "sum"),
            risco=("churn_risk", "mean"),
        )
        st.plotly_chart(
            px.bar(
                agg,
                x="segment",
                y="clientes",
                color="segment",
                color_discrete_sequence=["#087bfa", "#00beac", "#ff7080", "#f4b849"],
            ),
            width="stretch",
        )
        st.dataframe(agg, hide_index=True, width="stretch")
        info = api.personas()
        if info.get("trained"):
            st.markdown("**Perfil de cada persona (média do grupo)**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Persona": p["name"],
                            "Clientes": p["size"],
                            "% da base": f"{p['share']:.0%}",
                            "Gasto médio": money(p["profile"]["spend"]),
                            "Viagens": round(p["profile"]["frequency"]),
                            "Dias sem voar": round(p["profile"]["recency_days"]),
                            "Viagens com atraso ≥ 60 min": f"{p['profile']['incident_rate']:.0%}",
                        }
                        for p in info["personas"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            q = info["quality"]
            st.caption(
                f"KMeans com k={info['k']} · silhouette {q['silhouette']:.2f} · "
                f"estabilidade (ARI em reamostragem) {q['bootstrap_ari_mean']:.2f} · "
                "fora do agrupamento: "
                + ", ".join(info["excluded_attributes"])
                + ". "
                + info["limitation"]
            )
        else:
            st.caption(
                "Segmentação por regras explícitas de valor e risco; "
                "execute `azul-crm personas` para treinar as personas."
            )
        st.divider()
        st.subheader("Definição de alto valor (CLV)")
        clv = api.clv()
        if not clv.get("available"):
            st.info("Relatório de CLV ainda não gerado. Rode `azul-crm clv-report` e atualize.")
        else:
            if clv.get("stale"):
                st.warning("Relatório desatualizado: a base mudou depois do cálculo.")
            assumptions, summary = clv["assumptions"], clv["summary"]
            st.markdown(
                f"**Alto valor = os {assumptions['top_share']:.0%} clientes de maior valor "
                f"potencial.** Valor potencial = gasto em dinheiro dos últimos 12 meses × margem "
                f"({assumptions['margin']:.0%}) × desconto ({assumptions['discount_rate']:.0%} ao "
                "ano). CLV = valor potencial × (1 − risco de evasão)."
            )
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Clientes de alto valor", summary["high_value_customers"])
            m2.metric("Corte (valor potencial/ano)", money(summary["cutoff_potential_12m"]))
            m3.metric("Parcela do valor total", f"{summary['top_value_share']:.0%}")
            m4.metric("Alto valor em risco", summary["high_value_at_risk_customers"])
            st.markdown("**Concentração de valor (Pareto)**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Top": f"{x['top_share']:.0%}",
                            "Clientes": x["customers"],
                            "Parcela do valor potencial": f"{x['value_share']:.0%}",
                        }
                        for x in clv["concentration"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            st.markdown("**Por persona**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Persona": p["persona"],
                            "Clientes": p["customers"],
                            "De alto valor": p["high_value_customers"],
                            "Risco médio": f"{p['mean_churn_risk']:.0%}",
                            "CLV 12m": money(p["clv_12m"]),
                            "CLV em risco": money(p["clv_at_risk"]),
                        }
                        for p in clv["by_persona"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            st.markdown("**Sensibilidade às premissas (CLV total de 12 meses)**")
            table = pd.DataFrame(clv["sensitivity"]).pivot(
                index="margin", columns="discount_rate", values="total_clv_12m"
            )
            table.index = [f"margem {m:.0%}" for m in table.index]
            table.columns = [f"desconto {d:.0%}" for d in table.columns]
            st.dataframe(table.map(money), width="stretch")
            st.caption(clv["ranking_note"])
            for text in clv["limitations"]:
                st.caption("• " + text)
    elif page == "Ações de CRM":
        st.subheader("Estratégia por persona")
        plan = api.playbook(months)
        if plan.get("available"):
            st.caption(plan["note"])
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Persona": r["persona"],
                            "Clientes": r["customers"],
                            "Ação principal": r["action"],
                            "Oferta sugerida (hipótese)": r["offer"] or "—",
                            "Custo assumido": money(r["cost"]),
                            "Valor protegido (hipótese)": money(r["protected_value"]),
                            "Saldo hipotético": money(r["net"]),
                        }
                        for r in plan["rows"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(plan["disclaimer"])
        st.divider()
        st.subheader("Revisar antes de agir · " + cid)
        rec = api.recommend(cid)
        channels = {"app": "notificação no app", "email": "e-mail"}
        st.markdown(
            f"**Persona:** {rec.get('persona') or '—'} · "
            f"**Canal sugerido:** {channels.get(rec.get('channel'), rec.get('channel') or '—')}"
        )
        st.markdown("**Ação principal:** " + rec["action"]["title"])
        st.caption(rec["action"]["reason"])
        st.info(rec["draft"])
        if rec.get("offer"):
            with st.container(border=True):
                st.markdown("**Oferta sugerida · hipótese a validar (não entra na mensagem)**")
                st.write(rec["offer"]["title"])
                st.caption(rec["offer"]["description"])
                st.caption("Requer: " + rec["offer"]["requires"])
        evidence_ui(rec["evidence"])
        checklist = rec.get("review_checklist") or []
        confirmed = []
        if checklist:
            st.markdown("**Checklist de revisão** · marque cada item para poder aprovar")
            for item in checklist:
                label = item["text"] + " Fonte: " + item["source"] + "."
                if st.checkbox(label, key="chk-" + cid + "-" + item["code"]):
                    confirmed.append(item["code"])
        ready = len(confirmed) == len(checklist)
        note = st.text_area("Observação da revisão")
        a, b = st.columns(2)
        if a.button("Aprovar rascunho", type="primary", disabled=not ready):
            api.decide(cid, "APPROVED", note, confirmed)
            st.success("Aprovação registrada. Nenhuma mensagem enviada.")
        if b.button("Rejeitar rascunho"):
            api.decide(cid, "REJECTED", note, confirmed)
            st.success("Rejeição registrada.")
        st.subheader("Simular um cenário")
        cost = st.number_input("Custo por cliente (R$)", min_value=0.0, value=10.0)
        retention = st.slider("Fração hipotética do valor em risco protegida", 0.0, 1.0, 0.10)
        result = api.simulate(cost, retention, months, seg, rt)
        a, b, c = st.columns(3)
        a.metric("Custo do cenário", money(result["cost"]))
        b.metric("Valor protegido hipotético", money(result["hypothetical_protected_value"]))
        c.metric("Saldo hipotético", money(result["net_scenario"]))
        st.caption(result["note"])
        st.json(result)
    elif page == "Sentimento":
        st.subheader("Sentimento de avaliações")
        st.caption("Análise lexical explicável. Avaliações públicas e sintéticas são identificadas separadamente; os resultados não alteram o risco dos clientes.")
        sample = (Path(__file__).resolve().parents[1] / "data/fixtures/reviews.csv").read_bytes()
        st.download_button("Baixar CSV de exemplo sintético", sample, "reviews.csv", "text/csv")
        upload = st.file_uploader("CSV UTF-8: review_id, text, source_url, is_synthetic", type=["csv"])
        if st.button("Analisar avaliações"):
            content = upload.getvalue() if upload else sample
            result = api.sentiment(content)
            st.json({"total": result["total"], "sintéticas": result["synthetic"], "contagens": result["counts"]})
            st.dataframe(pd.DataFrame(result["reviews"]), hide_index=True)
            st.caption(result["limitations"])
            st.download_button("Exportar análise de sentimento", json.dumps(result, ensure_ascii=False, indent=2), "sentimento.json", "application/json")
    elif page == "Assistente IA":
        st.subheader("Respostas com evidências")
        st.caption(
            "Indicadores são calculados por código. O corpus disponível contém metodologia e catálogo interno, sem regulamento oficial validado."
        )
        ask_ui(api, cid)
    elif page == "Auditoria de viés":
        st.subheader("IA responsável · auditoria de viés")
        report = api.bias()
        if not report.get("available"):
            st.info(
                "Auditoria ainda não executada. Rode `azul-crm bias-audit` e atualize os dados."
            )
        else:
            if report.get("stale"):
                st.warning("Relatório desatualizado: a base mudou depois da auditoria.")
            s = report["settings"]
            st.caption(
                f"Resultado favorável: {s['favorable_outcome']} ({s['selected_customers']} de "
                f"{s['customers']} clientes). Alarme pela regra dos 4/5."
            )
            icon = {"ok": "🟢 OK", "atencao": "🟡 Atenção", "alerta": "🔴 Alerta"}
            icon["confundido"] = "🟠 Confundido"
            icon["amostra_insuficiente"] = "⚪ Amostra pequena"
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Atributo": a["label"],
                            "Resultado": icon[a["verdict"]],
                            "Razão bruta": a["selection_ratio"],
                            "Recall (iguais oportunidades)": a["recall_ratio"],
                            "Associação com persona (V)": (a["persona_association"] or {}).get(
                                "cramers_v"
                            ),
                        }
                        for a in report["attributes"].values()
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            for key, a in report["attributes"].items():
                with st.expander(a["label"] + " · " + icon[a["verdict"]]):
                    st.write(a["verdict_text"])
                    st.dataframe(
                        pd.DataFrame(a["groups"]).drop(columns=["persona_mix"]),
                        hide_index=True,
                        width="stretch",
                    )
                    if a["within_persona"]:
                        st.markdown("**Mesma persona, grupos diferentes (razão menor/maior):**")
                        st.dataframe(
                            pd.DataFrame(
                                [
                                    {
                                        "Persona": w["persona"],
                                        "Selecionados": w["selected"],
                                        "Razão": w["selection_ratio"],
                                        "p-valor": w["p_value"],
                                        "Alerta": "sim"
                                        if w["flag"]
                                        else "inconclusivo"
                                        if w["inconclusive"]
                                        else "não",
                                    }
                                    for w in a["within_persona"]
                                ]
                            ),
                            hide_index=True,
                            width="stretch",
                        )
                    if a["skipped_small_groups"]:
                        st.caption(
                            "Grupos pequenos, não comparados: "
                            + ", ".join(
                                f"{g['group']} ({g['customers']})"
                                for g in a["skipped_small_groups"]
                            )
                        )
            st.markdown("**Limitações**")
            for text in report["limitations"]:
                st.caption("• " + text)
    else:
        st.subheader("Dados e modelos")
        st.json(meta)
        st.json(api.models())
        st.caption(
            "Persistência: "
            + meta.get("storage", "legacy")
            + " · atualização exige recarregar o snapshot."
        )
        lake = api.lake()
        st.subheader("Data lake e dicionário de dados")
        if not lake.get("available"):
            st.info("Lake ainda não exportado. Rode `azul-crm export-lake` e atualize os dados.")
        else:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Camada": t["layer"],
                            "Tabela": t["name"],
                            "Linhas": t["rows"],
                            "Situação": "exportada" if t["exported"] else "sem dados",
                            "Colunas": len(t["columns"]),
                            "Descrição": t["description"],
                        }
                        for t in lake["tables"].values()
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            choice = st.selectbox("Ver colunas de", list(lake["tables"]))
            st.dataframe(
                pd.DataFrame(lake["tables"][choice]["columns"])[
                    ["name", "type", "nullable", "description"]
                ],
                hide_index=True,
                width="stretch",
            )
            st.caption("Parquet em data/lake · esquema validado no código · DDL Snowflake gerado.")
    st.divider()
    st.caption(data["notes"])
    st.caption(
        "Risco: "
        + meta.get("risk_method", "heuristic_not_calibrated")
        + " · dados sintéticos · recomendações sujeitas a revisão."
    )
    st.download_button(
        "↓ Exportar relatório do recorte",
        df.to_csv(index=False).encode("utf-8-sig"),
        "carteira-demonstrativa.csv",
        "text/csv",
    )
    st.download_button(
        "↓ Exportar premissas e indicadores",
        json.dumps(
            {"metadata": meta, "kpis": k, "notes": data["notes"]},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        "premissas.json",
        "application/json",
    )
except Exception as exc:
    st.error(
        "Não foi possível concluir a operação. Confira a configuração e a disponibilidade dos dados."
    )
    st.code(str(exc))
    st.info(
        "Primeira execução: python -m azul_crm.cli demo; depois reinicie ou use Atualizar dados."
    )
