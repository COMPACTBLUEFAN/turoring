"""Тесты от агента. Все зелёные."""
import pytest

from tag_search import (
    EmptyTag,
    FolderNotFound,
    MAX_NOTE_SIZE,
    OutsideVault,
    extract_tags,
    find_by_tag,
    normalize_tag,
)
from tags_cli import main


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    (root / "неделя 1").mkdir(parents=True)
    (root / ".obsidian").mkdir()
    (root / "a.md").write_text("текст #python и #SQL", encoding="utf-8")
    (root / "неделя 1" / "b.md").write_text("#Python на старте", encoding="utf-8")
    (root / ".obsidian" / "c.md").write_text("#python служебное", encoding="utf-8")
    (root / "d.txt").write_text("#python не заметка", encoding="utf-8")
    return root


def test_finds_tag_in_all_folders(vault):
    assert find_by_tag(vault, "python").paths == ["a.md", "неделя 1/b.md"]


def test_case_and_hash_in_query(vault):
    assert find_by_tag(vault, "#PyThOn").paths == ["a.md", "неделя 1/b.md"]


def test_skips_service_folders_and_not_md(vault):
    paths = find_by_tag(vault, "python").paths
    assert ".obsidian/c.md" not in paths
    assert "d.txt" not in paths


def test_folder_limits_search(vault):
    assert find_by_tag(vault, "python", "неделя 1").paths == ["неделя 1/b.md"]


def test_folder_outside_is_rejected(vault, tmp_path):
    (tmp_path / "outside").mkdir()
    with pytest.raises(OutsideVault):
        find_by_tag(vault, "python", "../outside")
    with pytest.raises(OutsideVault):
        find_by_tag(vault, "python", str(tmp_path / "outside"))


def test_folder_not_found(vault):
    with pytest.raises(FolderNotFound):
        find_by_tag(vault, "python", "нет такой")


def test_empty_tag():
    with pytest.raises(EmptyTag):
        normalize_tag("  # ")


def test_tags_in_code_block_ignored():
    text = "#снаружи\n```\n#внутри\n```\n"
    assert extract_tags(text) == {"снаружи"}


def test_url_fragment_and_heading_are_not_tags():
    assert extract_tags("# Заголовок\nhttp://a.example/#frag\n") == set()


def test_big_file_is_skipped(vault):
    (vault / "big.md").write_text("#python " + "а" * MAX_NOTE_SIZE, encoding="utf-8")
    result = find_by_tag(vault, "python")
    assert "big.md" not in result.paths
    assert result.skipped == 1


def test_broken_file_does_not_crash(vault):
    (vault / "broken.md").write_bytes(b"#python \xff\xfe")
    assert "broken.md" not in find_by_tag(vault, "python").paths


def test_symlink_is_not_followed(vault, tmp_path):
    secret = tmp_path / "secret.md"
    secret.write_text("#python секрет", encoding="utf-8")
    try:
        (vault / "link.md").symlink_to(secret)
    except OSError:
        pytest.skip("нет прав на симлинк")
    assert "link.md" not in find_by_tag(vault, "python").paths


def test_cli_prints_paths(vault, monkeypatch, capsys):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    assert main(["python"]) == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines() == ["a.md", "неделя 1/b.md"]
    assert "пропущено: 0" in captured.err
