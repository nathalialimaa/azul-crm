"""Importa documentos locais autorizados para o corpus versionado."""

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def import_document(path, root, document_id, title, source, is_demo=False):
    if not document_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", document_id):
        raise ValueError("document_id deve ter letras/números/hífen/underscore, até 80 caracteres")
    if not title or not source:
        raise ValueError("Título e fonte são obrigatórios")
    if not is_demo and urlparse(source).scheme != "https":
        raise ValueError("Documento público deve registrar URL HTTPS verificável")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Documento excede limite de 20 MiB")
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        text = "\n\n".join(
            f"Página {i + 1}\n{page.extract_text() or ''}"
            for i, page in enumerate(PdfReader(path).pages)
        )
    elif path.suffix.lower() in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8-sig")
    else:
        raise ValueError("Use PDF textual, TXT ou Markdown UTF-8")
    if len(text.strip()) < 50:
        raise ValueError("Texto insuficiente. PDF escaneado pode exigir OCR externo.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    target = root / "data/knowledge"
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "document_id": document_id,
        "title": title,
        "text": text,
        "source": source,
        "version": digest,
        "is_demo": is_demo,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    (target / (document_id + ".json")).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "document_id": document_id,
        "sha256": digest,
        "characters": len(text),
        "next_step": "Revise o texto e execute index. A importação não certifica vigência/eligibilidade.",
    }
