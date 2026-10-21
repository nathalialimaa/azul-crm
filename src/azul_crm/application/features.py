from datetime import date

from azul_crm.domain.models import Features, Trip


class FeatureBuilder:
    def build(self, customer_id: str, trips: list[Trip], start: date, end: date) -> Features:
        """Usa exclusivamente a janela inclusiva de observação."""
        if start > end:
            raise ValueError("Janela de observação inválida")
        observed = [
            t for t in trips if t.customer_id == customer_id and start <= t.flight_date <= end
        ]
        last = max((t.flight_date for t in observed), default=None)
        return Features(
            customer_id,
            round(sum(t.fare_amount for t in observed), 2),
            len(observed),
            (end - last).days if last else (end - start).days + 1,
            sum(t.delay_minutes >= 60 for t in observed) / len(observed) if observed else 0,
            end,
        )
