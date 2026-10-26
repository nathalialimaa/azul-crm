import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from azul_crm.application.dashboard import overview, simulation, strategy
from azul_crm.bootstrap import build_container
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

    def sentiment(self, content):
        from azul_crm.application.sentiment import analyze_csv

        result = analyze_csv(content)
        if self.http:
            import csv
            import io

            reviews = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            for review in reviews:
                review["is_synthetic"] = review["is_synthetic"].strip().lower() == "true"
            return self.request("POST", "/sentiment/analyze", json={"reviews": reviews})
        return result

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

    def explanation(self, cid):
        if self.http:
            return self.request("GET", "/customers/" + cid + "/explanation")
        from azul_crm.application.explanations import explain_customer

        return explain_customer(self.c, self.settings.root, cid)

    def customer(self, cid):
        if self.http:
            return self.request("GET", "/customers/" + cid)
        return {
            "customer": asdict(self.c.crm.customer(cid)),
            "trips": [asdict(t) for t in self.c.crm.trips(cid)],
            "scores": asdict(self.c.crm.scores(cid)),
        }

    def recommend(self, cid, generate=True):
        return (
            self.request("POST", "/agent/recommend", json={"customer_id": cid, "generate": generate})
            if self.http
            else asdict(self.c.recommendations.recommend(cid, generate=generate))
        )

    def ask(self, question, cid=None):
        if self.http:
            return self.request(
                "POST", "/agent/ask", json={"question": question, "customer_id": cid}
            )
        from azul_crm.application.assistant import answer_question

        return answer_question(self.c, self.settings.root, question, cid)

    def llm_status(self):
        if self.http:
            return self.request("GET", "/llm/status")
        from azul_crm.infrastructure.gemini import provider_status

        return provider_status()

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

    def decide(self, cid, status, note, confirmed=None, draft_id=None):
        if status not in {"APPROVED", "REJECTED"}:
            raise ValueError("Status deve ser APPROVED ou REJECTED")
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
                    "draft_id": draft_id,
                },
            )
        rec = asdict(self.c.recommendations.for_review(cid, draft_id))
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
            "draft_id": rec.get("draft_id"),
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
