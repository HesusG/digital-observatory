from observatory.processing.embedder import build_embedding_text


def test_distinct_titles_produce_distinct_text():
    a = build_embedding_text("Waislitz Award 2026", "Apply now for funding.")
    b = build_embedding_text("Mandela Rhodes Prize", "Apply now for funding.")
    assert a != b
    assert a.startswith("Waislitz Award 2026")


def test_empty_title_falls_back_to_text():
    assert build_embedding_text("", "Some body text") == "Some body text"
