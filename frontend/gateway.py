import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from azul_crm.application.dashboard import overview, simulation, strategy
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.rag import DocumentIndex
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store


class Gateway:
    def __init__(self):
        self.settings = Settings.load()
        self.http = os.getenv("CRM_UI_MODE", "local") == "http"
        self.base = os.getenv("CRM_API_URL", "http://127.0.0.1:8000").rstrip("/")
        self.c = None if self.http else build_container(self.settings)

    def request(self, method, path, **kwargs):
        r = httpx.request(method, self.base + "/api/v1" + path, timeout=150, **kwargs)
        r.raise_for_status()
        return r.json()

    def metadata(self):
        return self.request("GET", "/metadata") if self.http else self.c.metadata

    def dashboard(self, months=12, segment=None, route=None):
        if self.http:
            return self.request(
                "GET",
                "/dashboard",
                params={k: v for k, v in locals().items() if k not in {"self"} and v is not None},
            )
        return overview(self.c, months, segment, route)

    def customer(self, cid):
        if self.http:
            return self.request("GET", "/customers/" + cid)
        return {
            "customer": asdict(self.c.crm.customer(cid)),
            "trips": [asdict(t) for t in self.c.crm.trips(cid)],
            "scores": asdict(self.c.crm.scores(cid)),
        }

    def recommend(self, cid):
        return (
            self.request("POST", "/agent/recommend", json={"customer_id": cid})
            if self.http
            else asdict(self.c.recommendations.recommend(cid))
        )

    def ask(self, question, cid=None):
        if self.http:
            return self.request(
                "POST", "/agent/ask", json={"question": question, "customer_id": cid}
            )
        if cid and any(w in question.lower() for w in ["risco", "prioriz", "valor", "fator"]):
            s = self.c.crm.scores(cid)
            return {
                "answer": "\n".join(s.drivers) + "\nVersão: " + s.model_version,
                "evidence": [],
                "mode": "structured_customer_facts",
            }
        return DocumentIndex(self.settings.root).answer(question)

    def models(self):
        if self.http:
            return self.request("GET", "/models")
        p = self.settings.root / "artifacts/metrics.json"
        return (
            json.loads(p.read_text()) if p.exists() else {"selected": "heuristic", "trained": False}
        )

    def personas(self):
        if self.http:
            return self.request("GET", "/personas")
        p = self.settings.root / "artifacts/personas.json"
        if not p.exists():
            return {"trained": False, "method": "rules"}
        hidden = {"centroids", "scaler_mean", "scaler_scale", "clip_low", "clip_high"}
        artifact = json.loads(p.read_text(encoding="utf-8"))
        return {"trained": True, **{k: v for k, v in artifact.items() if k not in hidden}}

    def playbook(self, months=12):
        if self.http:
            return self.request("GET", "/playbook", params={"months": months})
        return strategy(self.c, months)

    def lake(self):
        if self.http:
            return self.request("GET", "/lake")
        from azul_crm.infrastructure.lake import load_dictionary

        return load_dictionary(self.settings.root)

    def clv(self):
        if self.http:
            return self.request("GET", "/clv")
        from azul_crm.pipeline.clv_report import load_clv_report

        return load_clv_report(self.settings.root, Store(self.settings.root))

    def bias(self):
        if self.http:
            return self.request("GET", "/bias")
        from azul_crm.pipeline.bias_audit import load_report

        return load_report(self.settings.root, Store(self.settings.root))

    def loyalty(self, cid):
        if self.http:
            return self.request("GET", "/customers/" + cid + "/loyalty")
        return next(
            (r for r in Store(self.settings.root).read("loyalty") if r["customer_id"] == cid), {}
        )

    def decide(self, cid, status, note, confirmed=None):
        confirmed = list(confirmed or [])
        if self.http:
            return self.request(
                "POST",
                "/decisions",
                json={
                    "customer_id": cid,
                    "status": status,
                    "note": note,
                    "confirmed_checklist": confirmed,
                },
            )
        rec = self.recommend(cid)
        if status == "APPROVED" and rec["action"]["code"] == "NO_ACTION":
            raise ValueError("Sem evidências; aprovação bloqueada")
        if status == "APPROVED":
            missing = [
                i["code"] for i in rec.get("review_checklist", []) if i["code"] not in confirmed
            ]
            if missing:
                raise ValueError(
                    "Confirme o checklist de revisão antes de aprovar: " + ", ".join(missing)
                )
        row = {
            "id": str(uuid4()),
            "customer_id": cid,
            "status": status,
            "note": note,
            "confirmed_checklist": confirmed,
            "recommendation": rec,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sent": False,
        }
        Store(self.settings.root).publish({"decisions": [(row["id"], row)]}, replace=False)
        return row

    def simulate(self, cost, retention, months, segment, route):
        if self.http:
            return self.request(
                "POST",
                "/simulations",
                json={
                    "cost_per_customer": cost,
                    "assumed_retention": retention,
                    "months": months,
                    "segment": segment,
                    "route": route,
                },
            )
        return simulation(self.dashboard(months, segment, route)["rows"], cost, retention)
