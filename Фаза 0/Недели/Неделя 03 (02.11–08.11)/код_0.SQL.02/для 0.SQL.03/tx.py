"""Транзакция на уровне «зачем» — к заданию 3 занятия `0.SQL.02`.

Запуск из этой папки:  python tx.py
Меняй только три флага ниже — остальное трогать не нужно.
"""
import sqlite3
from pathlib import Path

USE_TRANSACTION = False  # шаг б: поставь True — всё внутри BEGIN … COMMIT / ROLLBACK
CRASH = True             # сбой между двумя UPDATE (как будто программа упала)
OOPS_DELETE = False      # шаг в: поставь True — вместо перевода DELETE без WHERE

DB = Path(__file__).with_name("bank.db")


def reset() -> None:
    """Каждый запуск начинается с чистой базы: Склад 1000, Цех 0."""
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(
        """
        CREATE TABLE accounts (
            name    TEXT PRIMARY KEY,
            balance INTEGER NOT NULL CHECK (balance >= 0)
        );
        INSERT INTO accounts VALUES ('Склад', 1000), ('Цех', 0);
        """
    )
    con.close()


def show(title: str) -> None:
    """Читает базу новым подключением — так её увидит программа после перезапуска."""
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT name, balance FROM accounts ORDER BY name").fetchall()
    con.close()
    total = sum(balance for _, balance in rows)
    print(f"{title}: {rows} · всего денег: {total}")


def transfer(con: sqlite3.Connection, src: str, dst: str, amount: int) -> None:
    con.execute("UPDATE accounts SET balance = balance - ? WHERE name = ?", (amount, src))
    if CRASH:
        raise RuntimeError("сбой между двумя UPDATE")
    con.execute("UPDATE accounts SET balance = balance + ? WHERE name = ?", (amount, dst))


def main() -> None:
    reset()
    show("До    ")
    # isolation_level=None: без BEGIN каждая команда сохраняется в базе сразу же
    con = sqlite3.connect(DB, isolation_level=None)
    try:
        if USE_TRANSACTION:
            con.execute("BEGIN")
        if OOPS_DELETE:
            con.execute("DELETE FROM accounts")  # забыли WHERE
            raise RuntimeError("заметили, что удалили всё")
        transfer(con, "Склад", "Цех", 300)
        if USE_TRANSACTION:
            con.execute("COMMIT")
    except RuntimeError as err:
        print(f"Ошибка: {err}")
        if USE_TRANSACTION:
            con.execute("ROLLBACK")
            print("ROLLBACK — всё, что было после BEGIN, отменено")
    finally:
        con.close()
    show("После ")


if __name__ == "__main__":
    main()
