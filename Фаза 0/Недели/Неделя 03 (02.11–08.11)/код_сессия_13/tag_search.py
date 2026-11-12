"""Поиск заметок по тегу. Ядро: ничего не печатает, об ошибках сообщает исключением."""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_NOTE_SIZE = 10 * 1024 * 1024  # 10 МБ
TAG_RE = re.compile(r"(?<![\w/])#([\w/-]+)")
FENCE = "```"


class TagSearchError(Exception):
    """Базовая ошибка поиска."""


class EmptyTag(TagSearchError):
    """Пустой тег в запросе."""


class OutsideVault(TagSearchError):
    """Папка поиска лежит вне хранилища."""


class FolderNotFound(TagSearchError):
    """Папки поиска нет."""


@dataclass
class SearchResult:
    paths: list = field(default_factory=list)
    skipped: int = 0
    warnings: list = field(default_factory=list)


def normalize_tag(tag):
    """'#Python' и 'python' — один тег."""
    clean = tag.strip().lstrip("#").lower()
    if not clean:
        raise EmptyTag("пустой тег")
    return clean


def extract_tags(text):
    """Все теги заметки в нижнем регистре, кроме тегов внутри блоков кода."""
    tags = set()
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith(FENCE):
            in_code = not in_code
            continue
        if in_code:
            continue
        for match in TAG_RE.finditer(line):
            tags.add(match.group(1).lower())
    return tags


def _resolve_folder(root, folder):
    """Папка поиска: внутри корня, иначе OutsideVault."""
    if folder is None:
        return root
    candidate = (root / folder).resolve()
    if not str(candidate).startswith(str(root)):
        raise OutsideVault("папка поиска вне хранилища")
    if not candidate.is_dir():
        raise FolderNotFound("папка поиска не найдена")
    return candidate


def _iter_notes(start):
    """Все .md под start: служебные папки и симлинки пропускаем."""
    for current, dirs, files in os.walk(start, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            path = Path(current) / name
            if path.suffix.lower() == ".md" and not path.is_symlink():
                yield path


def _rel(path, root):
    """Путь заметки относительно корня, с прямыми слэшами."""
    return Path(os.path.relpath(path, root)).as_posix()


def _load(path):
    """Текст заметки или None, если заметка больше лимита."""
    text = path.read_text(encoding="utf-8")
    if len(text) > MAX_NOTE_SIZE:
        return None
    return text


def find_by_tag(root, tag, folder=None):
    """Заметки с тегом tag под root (или под root/folder)."""
    assert Path(root).is_dir(), "root must be a directory"
    wanted = normalize_tag(tag)
    root = Path(root).resolve()
    start = _resolve_folder(root, folder)

    result = SearchResult()
    for path in _iter_notes(start):
        try:
            text = _load(path)
        except (OSError, UnicodeDecodeError):
            continue
        if text is None:
            result.skipped += 1
            result.warnings.append(f"слишком большой файл: {_rel(path, root)}")
            continue
        if wanted in extract_tags(text):
            result.paths.append(_rel(path, root))
    result.paths.sort()
    return result
