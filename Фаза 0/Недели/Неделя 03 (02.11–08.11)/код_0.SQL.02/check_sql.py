"""Проверка своего SQL к заданию 2 занятия `0.SQL.02`.

1. Сохрани свой CREATE TABLE и ALTER TABLE в файл agent_actions.sql в этой папке.
2. Запусти:  python check_sql.py
База создаётся в памяти и сразу исчезает: на диске ничего не меняется.
"""
import sqlite3
from pathlib import Path

SQL_FILE = Path(__file__).with_name("agent_actions.sql")

if not SQL_FILE.exists():
    raise SystemExit(f"Нет файла {SQL_FILE.name} — сохрани в него свой запрос.")

con = sqlite3.connect(":memory:")
try:
    con.executescript(SQL_FILE.read_text(encoding="utf-8"))
except sqlite3.Error as err:
    raise SystemExit(f"Ошибка SQL: {err}")

for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
    print(f"Таблица {name}: OK")
    for _, col, col_type, notnull, default, pk in con.execute(f"PRAGMA table_info({name})"):
        flags = [f for f, on in (("PRIMARY KEY", pk), ("NOT NULL", notnull)) if on]
        if default is not None:
            flags.append(f"DEFAULT {default}")
        print(f"  {col} {col_type} {' '.join(flags)}".rstrip())
