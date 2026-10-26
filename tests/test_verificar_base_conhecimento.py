from scripts.verificar_base_conhecimento import provenance_label


def test_non_demo_documents_are_labeled_public_imported():
    assert provenance_label(False) == "público/importado"
    assert provenance_label(True) == "demonstração"
