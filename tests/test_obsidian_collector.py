import asyncio

from observatory.collectors.obsidian import ObsidianNotesCollector


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_collects_md_with_and_without_frontmatter(tmp_path):
    folder = "Pedagogía"
    base = tmp_path / folder
    _write(base / "note1.md", "---\ntitle: Mi nota\n---\nCuerpo de la nota uno.")
    _write(base / "note2.md", "Solo cuerpo, sin frontmatter.")

    collector = ObsidianNotesCollector(
        vault_path=tmp_path,
        folders=[{"path": folder, "recursive": True}],
    )
    items = asyncio.run(collector.collect())

    assert len(items) == 2
    by_title = {i.title: i for i in items}
    # frontmatter title wins
    assert "Mi nota" in by_title
    # no-frontmatter falls back to filename stem
    assert "note2" in by_title
    for it in items:
        assert it.kind == "article"
        assert it.source_type == "markdown"
        assert it.source_group == "pedagogy_notes"
        assert it.raw_text.strip() != ""


def test_ignores_non_md_and_missing_folder(tmp_path):
    base = tmp_path / "Notas"
    _write(base / "a.md", "uno")
    _write(base / "b.txt", "no soy markdown")
    collector = ObsidianNotesCollector(
        vault_path=tmp_path,
        folders=[{"path": "Notas"}, {"path": "NoExiste"}],
    )
    items = asyncio.run(collector.collect())
    assert len(items) == 1
    assert items[0].raw_text.strip() == "uno"


def test_list_vault_folders_depth_and_hidden(tmp_path):
    from observatory.collectors.obsidian import list_vault_folders

    (tmp_path / "Pedagogía" / "Sub").mkdir(parents=True)
    (tmp_path / ".obsidian" / "plugins").mkdir(parents=True)
    (tmp_path / "A" / "B" / "C" / "D").mkdir(parents=True)

    folders = list_vault_folders(tmp_path, max_depth=3)
    assert "Pedagogía" in folders
    assert "Pedagogía/Sub" in folders
    # hidden tree excluded
    assert not any(f.startswith(".obsidian") for f in folders)
    # depth>3 excluded (A/B/C/D is depth 4)
    assert "A/B/C/D" not in folders
    assert "A/B/C" in folders
