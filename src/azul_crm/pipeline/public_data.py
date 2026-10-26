"""Download limitado, Bronze imutável e Silver de tarifas ANAC."""

import collections
import csv
import hashlib
import io
import json
import math
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.anac import EXPECTED_COLUMNS, SOURCE_PAGE

AIRPORT_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url, directory, max_mb=50, refresh=False):
    """Cache por URL + checksum; só HTTPS. Não contorna bloqueios do provedor."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Fonte deve ser HTTPS")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (hashlib.sha256(url.encode()).hexdigest()[:16] + ".download")
    meta = target.with_suffix(".json")
    if target.exists() and meta.exists() and not refresh:
        prior = json.loads(meta.read_text())
        if prior["sha256"] == sha(target):
            return target, prior
    for attempt in range(3):
        part = target.with_suffix(".part")
        try:
            with httpx.stream("GET", url, timeout=30, follow_redirects=True) as response:
                response.raise_for_status()
                if response.url.scheme != "https":
                    raise ValueError("Redirecionamento inseguro")
                size = 0
                with part.open("wb") as out:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > max_mb * 1024 * 1024:
                            raise ValueError("Download excede --max-mb; aumente conscientemente")
                        out.write(chunk)
                if not size:
                    raise ValueError("Download vazio")
            part.replace(target)
            data = {
                "url": url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "sha256": sha(target),
                "bytes": size,
            }
            meta.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return target, data
        except (httpx.HTTPError, ValueError):
            part.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2**attempt)


def csv_payload(path, max_mb=100):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            entries = [x for x in z.infolist() if x.filename.lower().endswith(".csv")]
            if len(entries) != 1 or entries[0].file_size > max_mb * 1024 * 1024:
                raise ValueError("ZIP deve conter um único CSV dentro do limite")
            raw = z.read(entries[0])
    else:
        if path.stat().st_size > max_mb * 1024 * 1024:
            raise ValueError("CSV excede limite")
        raw = path.read_bytes()
    for enc in ["utf-8-sig", "latin-1"]:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text.lstrip().startswith("<"):
        raise ValueError("Fonte retornou HTML, não CSV; obtenha o arquivo oficial manualmente")
    stream = io.StringIO(text)
    header = stream.readline()
    for _ in range(5):  # alguns arquivos da ANAC têm linhas de aviso antes do cabeçalho
        if header.count(";") >= 2 or header.count(",") >= 2:
            break
        header = stream.readline()
    else:
        stream.seek(0)
        header = stream.readline()
    delimiter = ";" if header.count(";") > header.count(",") else ","
    stream.seek(stream.tell() - len(header))  # volta ao início do cabeçalho
    return csv.DictReader(stream, delimiter=delimiter)


class AirportDimension:
    def __init__(self, rows):
        self.version = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        self.mapping = defaultdict(list)
        for r in rows:
            code = (r.get("icao_code") or r.get("ident") or "").strip().upper()
            if len(code) == 4:
                self.mapping[code].append(r)

    def lookup(self, code):
        code = code.strip().upper()
        matches = self.mapping.get(code, [])
        if len(matches) != 1:
            return None, "ambiguous" if matches else "unknown"
        iata = (matches[0].get("iata_code") or "").strip().upper()
        if len(iata) != 3 or not iata.isalpha():
            return None, "without_iata"
        return iata, "matched"


def import_airports(path, store):
    rows = list(csv_payload(path))
    if not rows or not {"ident", "iata_code", "name"}.issubset(rows[0]):
        raise ValueError("Dimensão deve seguir schema OurAirports")
    version = sha(path)
    payload = [
        (str(r.get("id") or i), {**r, "mapping_sha256": version, "source": AIRPORT_URL})
        for i, r in enumerate(rows)
    ]
    store.publish({"airports": payload})
    return {"airports": len(rows), "sha256": version}


def ingest_fares(path, root, period=None, source_url=SOURCE_PAGE, max_rows=1000000):
    """Compatível com schema tradicional de 7 campos; extras preservados, ausências rejeitadas."""
    store = Store(root)
    digest = sha(path)
    prior = next((r for r in store.read("sources") if r["sha256"] == digest), None)
    if prior:
        if period and prior["period"] != period:
            raise ValueError("Período solicitado diverge do arquivo já ingerido")
        return {**prior, "already_ingested": True}
    dimension = AirportDimension(store.read("airports"))
    reader = csv_payload(path)
    if not reader.fieldnames or not set(EXPECTED_COLUMNS).issubset(reader.fieldnames):
        raise ValueError("Schema ANAC não suportado: " + str(reader.fieldnames))
    silver, raw_rows, unmatched = [], [], []
    periods = set()
    for i, r in enumerate(reader):
        if i >= max_rows:
            raise ValueError("Arquivo excede max_rows; nenhuma carga parcial foi publicada")
        year, month = int(r["nr_ano_referencia"]), int(r["nr_mes_referencia"])
        if not 2002 <= year <= 2100 or not 1 <= month <= 12:
            raise ValueError(f"Período inválido na linha {i + 2}")
        p = f"{year:04d}-{month:02d}"
        periods.add(p)
        fare = float(r["nr_tarifa"].replace(",", "."))
        seats = int(r["nr_assentos"])
        if not math.isfinite(fare) or fare <= 0 or seats <= 0:
            raise ValueError(f"Tarifa/assentos inválidos na linha {i + 2}")
        orig, dest = r["sg_icao_origem"].strip().upper(), r["sg_icao_destino"].strip().upper()
        if len(orig) != 4 or len(dest) != 4 or orig == dest:
            raise ValueError("ICAO inválido ou rota circular")
        oi, os = dimension.lookup(orig)
        di, ds = dimension.lookup(dest)
        item = {
            "period": p,
            "airline": r["sg_empresa_icao"].strip().upper(),
            "origin_icao": orig,
            "destination_icao": dest,
            "origin": oi,
            "destination": di,
            "origin_status": os,
            "destination_status": ds,
            "fare": fare,
            "seats": seats,
            "source_sha256": digest,
            "mapping_version": dimension.version,
            "is_synthetic": False,
            "period_kind": "sale_month",
        }
        row_id = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
        raw_rows.append((digest + ":" + str(i), {"row": r, "sha256": digest, "line": i + 2}))
        silver.append((row_id, item))
        if os != "matched" or ds != "matched":
            unmatched.append(item)
    if not silver or len(periods) != 1 or (period and period not in periods):
        raise ValueError("Arquivo vazio ou período divergente/misto")
    # Duplicatas exatas mantidas na Bronze e deduplicadas na Silver sem somar assentos duas vezes.
    silver = list(dict(silver).items())
    bronze = root / "data/bronze/anac" / digest
    bronze.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copyfile(path, bronze / path.name)
    meta = {
        "sha256": digest,
        "period": next(iter(periods)),
        "source_url": source_url,
        "rows": len(raw_rows),
        "silver_rows": len(silver),
        "unmatched": len(unmatched),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "fares",
    }
    (bronze / "source.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (bronze / "unmatched.json").write_text(json.dumps(unmatched, indent=2), encoding="utf-8")
    # Revisões substituem somente o mês correspondente. Um escritor por vez.
    existing = [
        (hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest(), r)
        for r in store.read("fares")
        if r["period"] != meta["period"]
    ]
    store.publish(
        {"raw_rows": raw_rows, "sources": [(digest, meta)], "fares": existing + silver},
        replace={"fares"},
    )
    return meta


def calibrated_routes(store, airline="AZU"):
    groups = defaultdict(lambda: [0.0, 0])
    for batch in store.iter_batches("fares"):
        for r in batch:
            if r["origin"] and r["destination"] and r["airline"] == airline:
                key = (r["origin"], r["destination"])
                groups[key][0] += r["fare"] * r["seats"]
                groups[key][1] += r["seats"]
    return [
        {"origin": a, "destination": b, "mean_fare": v / n, "weight": n}
        for (a, b), (v, n) in sorted(groups.items())
    ]


def discover_fares_url(period):
    """Usa links publicados; não adivinha caminho de arquivo mensal."""
    import re
    from html.parser import HTMLParser
    from urllib.parse import urljoin

    if not period or not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", period):
        raise ValueError("Período deve ser YYYY-MM")

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.urls.extend(v for k, v in attrs if k == "href" and v)

    page = "https://sistemas.anac.gov.br/sas/downloads/"
    response = httpx.get(page, timeout=30, follow_redirects=True)
    response.raise_for_status()
    parser = Links()
    parser.feed(response.text)
    urls = [urljoin(page, u) for u in parser.urls]
    matches = [
        u
        for u in urls
        if period.replace("-", "") in u
        and urlparse(u).path.lower().endswith((".zip", ".csv"))
        and (urlparse(u).hostname or "").endswith(".anac.gov.br")
        and u.startswith("https://")
    ]
    if len(matches) != 1:
        raise ValueError(
            "Não foi possível resolver um arquivo mensal único no portal oficial. Use --url ou --file; nenhum caminho foi presumido."
        )
    return matches[0]


VRA_ALIASES = {
    "airline": ("sigla icao empresa aerea", "icao empresa aerea"),
    "flight": ("numero voo",),
    "origin": ("sigla icao aeroporto origem", "icao aerodromo origem"),
    "destination": ("sigla icao aeroporto destino", "icao aerodromo destino"),
    "scheduled": ("partida prevista",),
    "actual": ("partida real",),
}
VRA_OPTIONAL = {
    "status": ("situacao voo", "situacao do voo"),
    "line_type": ("codigo tipo linha",),
}
MISSING_MARKERS = {"", "null", "n/a", "na", "none"}
MAX_REJECTED_SHARE = 0.05


def _vra_timestamp(value):
    """Horários do VRA vêm em UTC. Ausência (``null``, ``N/A``) vira ``None``."""
    from datetime import timezone

    if value is None or value.strip().lower() in MISSING_MARKERS:
        return None
    text = value.strip().split(".")[0]  # alguns registros trazem frações de segundo
    for fmt in ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError("Data VRA inválida: " + value)


def ingest_vra(path, root, period, source_url):
    """VRA: horários em UTC; ausência de horário fica nula, nunca vira atraso zero.

    Linhas sem data ou fora do período são rejeitadas e contadas, não derrubam a carga. Se mais
    de 5% das linhas forem rejeitadas, a carga inteira é recusada (arquivo ou período errado).
    """
    import shutil
    import unicodedata

    def norm(s):
        return "".join(
            c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c)
        ).strip()

    store = Store(root)
    dimension = AirportDimension(store.read("airports"))
    digest = sha(path)
    prior = next(
        (r for r in store.read("sources")
         if r["sha256"] == digest and r.get("dataset") == "vra"), None
    )
    if prior:
        if prior["period"] != period:
            raise ValueError("Período solicitado diverge do arquivo VRA já ingerido")
        return {"already_ingested": True, "sha256": digest}
    reader = csv_payload(path)
    present = {norm(k): k for k in (reader.fieldnames or []) if k}
    columns = {}
    for key, names in {**VRA_ALIASES, **VRA_OPTIONAL}.items():
        found = next((n for n in names if n in present), None)
        if found is None and key in VRA_ALIASES:
            raise ValueError("Schema VRA não suportado: " + str(reader.fieldnames))
        columns[key] = present.get(found) if found else None

    def field(row, key):
        name = columns[key]
        return (row.get(name) or "").strip() if name else ""

    records, raw, rejected = [], [], collections.Counter()
    unmatched = 0
    for i, row in enumerate(reader):
        if i >= 1000000:
            raise ValueError("VRA excede limite de 1 milhão de linhas")
        scheduled = _vra_timestamp(field(row, "scheduled"))
        actual = _vra_timestamp(field(row, "actual"))
        when = scheduled or actual
        if not when:
            rejected["sem_data"] += 1
            continue
        if when.strftime("%Y-%m") != period:
            rejected["fora_do_periodo"] += 1
            continue
        orig = field(row, "origin").upper()
        dest = field(row, "destination").upper()
        oi, os = dimension.lookup(orig)
        di, ds = dimension.lookup(dest)
        status = norm(field(row, "status") or "nao informado")
        cancelled = True if status == "cancelado" else False if status == "realizado" else None
        delay = (actual - scheduled).total_seconds() / 60 if scheduled and actual else None
        records.append(
            (
                hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest(),
                {
                    "period": period,
                    "airline": field(row, "airline").upper(),
                    "flight_number": field(row, "flight"),
                    "line_type": field(row, "line_type").upper() or None,
                    "origin_icao": orig,
                    "destination_icao": dest,
                    "origin": oi,
                    "destination": di,
                    "origin_status": os,
                    "destination_status": ds,
                    "scheduled_departure": scheduled.isoformat() if scheduled else None,
                    "actual_departure": actual.isoformat() if actual else None,
                    "delay_minutes": delay,
                    "cancelled": cancelled,
                    "source_sha256": digest,
                    "mapping_version": dimension.version,
                    "is_synthetic": False,
                },
            )
        )
        raw.append(("vra:" + digest + ":" + str(i), {"row": row, "sha256": digest, "line": i + 2}))
        unmatched += int(os != "matched" or ds != "matched")
    total_rejected = sum(rejected.values())
    seen = len(records) + total_rejected
    if not records or total_rejected / seen > MAX_REJECTED_SHARE:
        raise ValueError(
            f"VRA recusado: {total_rejected} de {seen} linhas rejeitadas {dict(rejected)}. "
            "Confira o arquivo e o --period."
        )
    records = list(dict(records).items())
    previous = [
        (hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest(), r)
        for r in store.read("operations")
        if r["period"] != period
    ]
    meta = {
        "dataset": "vra",
        "sha256": digest,
        "period": period,
        "rows": len(raw),
        "silver_rows": len(records),
        "unmatched": unmatched,
        "rejected_rows": total_rejected,
        "rejected_reasons": dict(rejected),
        "source_url": source_url,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    bronze = root / "data/bronze/vra" / digest
    bronze.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, bronze / path.name)
    (bronze / "source.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    store.publish(
        {"operations": previous + records, "raw_rows": raw, "sources": [(digest, meta)]},
        replace={"operations"},
    )
    return meta
