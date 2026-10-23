"""Distribui os clientes sintéticos pelas rotas reais na proporção da demanda (assentos).

O gerador original usa a rota na posição ``índice % total``. Com poucas rotas isso é inofensivo,
mas com os dados reais da ANAC (milhares de rotas, ordenadas por código) usaria só as primeiras
em ordem alfabética: uma fração mínima da demanda, sem os grandes aeroportos. Aqui a rota de
cada cliente é sorteada com peso igual aos assentos comercializados, com semente fixa.
O comportamento do cliente (frequência, recência, atrasos) continua vindo do gerador original.
"""

import random
from dataclasses import replace

from azul_crm.pipeline.stages import DemoSyntheticGenerator


class PublicDemandGenerator(DemoSyntheticGenerator):
    def __init__(self, delays=None):
        """``delays``: distribuição real de atrasos (``EmpiricalDelays``); sem ela, o padrão antigo."""
        self.delays = delays

    def generate(self, routes, count, seed, start, end):
        if not routes:
            raise ValueError("Sem rotas para distribuir os clientes")
        weights = [r.get("weight") for r in routes]
        if any(w is None or w <= 0 for w in weights):
            raise ValueError("Toda rota calibrada precisa de peso de demanda positivo")
        chosen = random.Random(seed + 101).choices(routes, weights=weights, k=count)
        customers, trips = super().generate(chosen, count, seed, start, end)
        if self.delays is not None:
            rng = random.Random(seed + 202)
            trips = [replace(t, delay_minutes=self.delays.sample(t.origin, rng)) for t in trips]
        return customers, trips
