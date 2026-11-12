"""CLI: python tags_cli.py <тег> [--folder ПАПКА]. Тонкая обёртка над ядром."""
import argparse
import json
import os
import sys

from tag_search import TagSearchError, find_by_tag


def main(argv=None):
    parser = argparse.ArgumentParser(description="Поиск заметок по тегу")
    parser.add_argument("tag")
    parser.add_argument("--folder", default=None)
    args = parser.parse_args(argv)

    root = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not root:
        print("ошибка: не задан OBSIDIAN_VAULT_PATH", file=sys.stderr)
        return 2

    try:
        result = find_by_tag(root, args.tag, args.folder)
    except TagSearchError as err:
        print(f"ошибка: {err}", file=sys.stderr)
        return 1

    for path in result.paths:
        print(path)
    for warning in result.warnings:
        print(f"предупреждение: {warning}", file=sys.stderr)
    print(f"пропущено: {result.skipped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
