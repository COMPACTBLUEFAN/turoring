"""Один и тот же лог LLM-вызовов в SQLite (хранит строками) и DuckDB (хранит колонками).

К заданию 2 занятия `0.SQL.02`. Запуск из этой папки:
    uv run --with duckdb python compare.py      (или: pip install duckdb, затем python compare.py)

Первый запуск создаёт обе базы (~20–40 с), следующие берут готовые.
Меняй только флаг QUERY — запросы уже написаны, писать свои не нужно.
"""
import csv
import random
import sqlite3
import statistics
import time
from pathlib import Path

import duckdb

QUERY = "aggregate"  # шаг б: "lookup", шаг в: "wide"
ROWS = 300_000
RUNS = 5

QUERIES = {
    # средняя стоимость вызова по дням — читает 2 колонки из 11, но все строки
    "aggregate": "SELECT day, round(avg(cost_rub), 2) FROM calls GROUP BY day ORDER BY day",
    # одна строка целиком по ключу — читает все колонки, но одну строку
    "lookup": "SELECT * FROM calls WHERE id = 123456",
    # поиск по тексту ответа — самая «толстая» колонка, все строки
    "wide": "SELECT count(*) FROM calls WHERE response LIKE '%ошибка%'",
}

HERE = Path(__file__).parent
SQLITE = HERE / "calls.sqlite"
DUCK = HERE / "calls.duckdb"
CSV = HERE / "calls.csv"

SCHEMA = """CREATE TABLE calls (
    id INTEGER PRIMARY KEY, day TEXT, model TEXT, user_id INTEGER,
    tokens_in INTEGER, tokens_out INTEGER, cost_rub DOUBLE, latency_ms INTEGER,
    status TEXT, prompt TEXT, response TEXT)"""

WORDS = ("заметка", "сводка", "агент", "поиск", "тег", "ссылка", "ответ", "контекст",
         "модель", "запрос", "хранилище", "файл", "неделя", "занятие", "проверка")
MODELS = ("opus-5.5", "sonnet-5.5", "haiku-5.5", "local-qwen", "gigachat")


def text(n: int, rnd: random.Random, error: bool = False) -> str:
    words = [rnd.choice(WORDS) for _ in range(n)]
    if error:
        words[rnd.randrange(n)] = "ошибка"
    return " ".join(words)


def build() -> None:
    """Синтетический лог: одинаковые данные в обеих базах."""
    print(f"Создаю базы на {ROWS:,} строк…".replace(",", " "))
    rnd = random.Random(42)
    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for i in range(1, ROWS + 1):
            tin, tout = rnd.randint(200, 8000), rnd.randint(50, 2000)
            w.writerow([i, f"2026-11-{rnd.randint(1, 30):02d}", rnd.choice(MODELS), rnd.randint(1, 50),
                        tin, tout, round((tin * 0.3 + tout * 1.5) / 1000, 4), rnd.randint(300, 9000),
                        "ok" if rnd.random() > 0.03 else "fail",
                        text(15, rnd), text(30, rnd, error=rnd.random() < 0.05)])
    con = sqlite3.connect(SQLITE)
    con.execute(SCHEMA)
    with CSV.open(encoding="utf-8") as f, con:
        con.executemany("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?)", csv.reader(f))
    con.close()
    dcon = duckdb.connect(str(DUCK))
    dcon.execute(SCHEMA)
    dcon.execute(f"INSERT INTO calls SELECT * FROM read_csv('{CSV.as_posix()}', header=false)")
    dcon.execute("CHECKPOINT")
    dcon.close()
    CSV.unlink()


def median_ms(run) -> tuple[float, object]:
    times, result = [], None
    for _ in range(RUNS):
        t = time.perf_counter()
        result = run()
        times.append((time.perf_counter() - t) * 1000)
    return statistics.median(times), result


def main() -> None:
    if not (SQLITE.exists() and DUCK.exists()):
        build()
    sql = QUERIES[QUERY]
    print(f"Запрос «{QUERY}»: {sql}\n")

    con = sqlite3.connect(SQLITE)
    t_sqlite, r_sqlite = median_ms(lambda: con.execute(sql).fetchall())
    con.close()
    dcon = duckdb.connect(str(DUCK), read_only=True)
    t_duck, r_duck = median_ms(lambda: dcon.execute(sql).fetchall())
    dcon.close()

    same = "да" if len(r_sqlite) == len(r_duck) else "НЕТ"
    print(f"{'':10}{'время, мс (медиана из ' + str(RUNS) + ')':>30}{'размер файла, МБ':>20}")
    print(f"{'SQLite':10}{t_sqlite:>30.2f}{SQLITE.stat().st_size / 2**20:>20.1f}")
    print(f"{'DuckDB':10}{t_duck:>30.2f}{DUCK.stat().st_size / 2**20:>20.1f}")
    print(f"\nВо сколько раз быстрее DuckDB: {t_sqlite / t_duck:.2f} (меньше 1 — значит, медленнее)")
    first = str(r_duck[0]) if r_duck else "—"
    print(f"Число строк в ответе совпало: {same}; первая строка — {first[:100]}{'…' if len(first) > 100 else ''}")


if __name__ == "__main__":
    main()
