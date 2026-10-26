"""Atrasos reais do VRA (ANAC) para o gerador sintético.

Sem esta calibração os atrasos são sorteados de uma lista arbitrária (40% das viagens com 60 min
ou mais). Com ela, cada viagem sintética recebe um atraso sorteado da distribuição **observada**
da companhia no VRA, por aeroporto de origem quando há voos suficientes e no conjunto geral caso
contrário. Antecipação (partida antes do previsto) conta como zero de atraso. Cancelamentos não
entram nas viagens: só aparecem na taxa registrada no resumo.
"""

import random
from collections import defaultdict

MIN_FLIGHTS = 100  # abaixo disso a amostra não representa a operação
MIN_ORIGIN = 200  # voos mínimos para um aeroporto ter distribuição própria


class EmpiricalDelays:
    def __init__(self, overall: list[int], by_origin: dict[str, list[int]], summary: dict):
        self.overall, self.by_origin, self.summary = overall, by_origin, summary

    def sample(self, origin: str, rng: random.Random) -> int:
        return rng.choice(self.by_origin.get(origin) or self.overall)

    @classmethod
    def from_store(
        cls, store, airline="AZU", line_type="N", min_origin=MIN_ORIGIN, min_flights=MIN_FLIGHTS
    ):
        """Constrói a partir de ``silver.operations``. Devolve None se não houver voos suficientes."""
        overall, by_origin = [], defaultdict(list)
        periods, scheduled, cancelled = set(), 0, 0
        for batch in store.iter_batches("operations"):
            for r in batch:
                if r.get("airline") != airline or r.get("line_type") != line_type:
                    continue
                scheduled += 1
                periods.add(r["period"])
                if r.get("cancelled") is True:
                    cancelled += 1
                elif r.get("cancelled") is False and r.get("delay_minutes") is not None:
                    minutes = max(0, int(round(r["delay_minutes"])))
                    overall.append(minutes)
                    if r.get("origin"):
                        by_origin[r["origin"]].append(minutes)
        if len(overall) < min_flights:
            return None
        own = {k: v for k, v in by_origin.items() if len(v) >= min_origin}
        share = lambda t: round(sum(m >= t for m in overall) / len(overall), 4)  # noqa: E731
        summary = {
            "source": "VRA (ANAC)",
            "airline": airline,
            "line_type": line_type,
            "periods": sorted(periods),
            "flights": len(overall),
            "cancellation_rate": round(cancelled / scheduled, 4),
            "share_delay_ge_15": share(15),
            "share_delay_ge_60": share(60),
            "airports_with_own_distribution": len(own),
        }
        return cls(overall, own, summary)
