"""Sistema visual Azul Flight Deck: tipografia local e tokens responsivos."""

import base64
from html import escape
from pathlib import Path

import plotly.io as pio
import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"


def apply_theme():
    css = (ASSETS / "theme.css").read_text(encoding="utf-8")
    font = ASSETS / "manrope.ttf"
    if font.exists():
        data = base64.b64encode(font.read_bytes()).decode()
        css = (
            "@font-face{font-family:Manrope;src:url(data:font/ttf;base64,"
            + data
            + ") format('truetype');font-display:swap;font-weight:400 800;}"
            + css
        )
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)
    pio.templates["azul"] = {
        "layout": {
            "font": {"family": "Manrope, Segoe UI, sans-serif", "color": "#173557", "size": 12},
            "paper_bgcolor": "#ffffff",
            "plot_bgcolor": "#ffffff",
            "colorway": ["#0076c8", "#00a6bf", "#bd425a", "#417774"],
            "margin": {"l": 24, "r": 24, "t": 30, "b": 24},
        }
    }
    pio.templates.default = "azul"


def masthead(page, status):
    summaries = {
        "Visão geral": (
            "Decisões que aproximam.",
            "Valor, risco e relacionamento em uma única visão de voo.",
        ),
        "Clientes": (
            "Cada jornada tem uma história.",
            "Conheça os sinais e o contexto por trás de cada cliente.",
        ),
        "Segmentos": (
            "Perfis diferentes. Cuidado certo.",
            "Transforme comportamento em estratégias de relacionamento.",
        ),
        "Ações de CRM": (
            "Da inteligência ao próximo contato.",
            "Planeje, personalize e revise cada decisão antes de agir.",
        ),
        "Assistente IA": (
            "Uma nova perspectiva para decidir.",
            "Converse com os dados da carteira e com fontes verificáveis.",
        ),
        "Sentimento": (
            "Escute o que a jornada revela.",
            "Identifique temas, sinais de atrito e oportunidades de cuidado.",
        ),
        "Auditoria de viés": (
            "Confiança também é inteligência.",
            "Avalie diferenças entre grupos com critérios transparentes.",
        ),
        "Dados e modelos": (
            "Clareza em cada camada.",
            "Explore a origem dos dados, os modelos e suas limitações.",
        ),
    }
    title, subtitle = summaries[page]
    llm = (
        "Gemini configurado"
        if status.get("provider") == "gemini" and status.get("configured")
        else "Inteligência local"
    )
    st.markdown(
        f'<div class="flight-masthead"><div><div class="workspace-label">Azul CRM · {escape(page)}</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div><div class="masthead-meta"><span class="status-dot"></span>{llm}<small>Carteira sintética · Revisão humana</small></div></div>',
        unsafe_allow_html=True,
    )
