"""Entrada de deploy privado.

* Prepara a demonstração (dados, modelo, personas e auditoria) uma vez por processo.
* Se ``CRM_APP_PASSWORD`` estiver definida, exige a senha antes de mostrar qualquer coisa.
  É uma camada extra, não substitui o controle de acesso da hospedagem.
"""

import hmac
import os
import runpy

import streamlit as st

from azul_crm.infrastructure.settings import Settings

settings = Settings.load()


def _gate() -> None:
    expected = os.getenv("CRM_APP_PASSWORD")
    if not expected or st.session_state.get("crm_authenticated"):
        return
    # Só nesta tela o set_page_config é daqui; autenticado, quem chama é o frontend/app.py.
    st.set_page_config(page_title="Acesso restrito", page_icon="✈")
    st.title("Acesso restrito")
    st.caption("Protótipo confidencial. Informe a senha recebida para continuar.")
    typed = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(typed.encode(), expected.encode()):
            st.session_state["crm_authenticated"] = True
            st.rerun()
        st.error("Senha incorreta.")
    st.stop()


@st.cache_resource(show_spinner=False)  # sem spinner: nada pode vir antes do set_page_config
def _prepare() -> dict:
    if os.getenv("CRM_STORAGE", "sqlite") != "sqlite":
        return {"steps": []}
    from azul_crm.pipeline.demo import prepare_demo

    return prepare_demo(settings)


_gate()
_prepare()
runpy.run_path(str(settings.root / "frontend/app.py"), run_name="__main__")
