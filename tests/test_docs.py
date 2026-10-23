from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"


def test_every_document_is_listed_in_the_index():
    index = (DOCS / "INDICE.md").read_text(encoding="utf-8")
    documents = sorted(p.name for p in DOCS.glob("*.md") if p.name != "INDICE.md")
    missing = [name for name in documents if f"`{name}`" not in index]
    assert not missing, f"documentos fora do índice: {missing}"


def test_index_does_not_point_to_missing_documents():
    index = (DOCS / "INDICE.md").read_text(encoding="utf-8")
    listed = [
        line.split("`")[1]
        for line in index.splitlines()
        if line.startswith("| `") and line.split("`")[1].endswith(".md")
    ]
    assert listed and all((DOCS / name).exists() for name in listed)


def test_readme_points_to_the_index_and_has_no_stale_claims():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "docs/INDICE.md" in readme
    for stale in ["score 0–100 no eixo vertical", "O ZIP inclui um snapshot", "MVP integrado v0.2"]:
        assert stale not in readme


def test_readme_documents_the_public_data_sources_and_commands():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for needle in ["sistemas.anac.gov.br/sas/downloads", "dadosabertos", "cli fares", "cli vra"]:
        assert needle in readme
