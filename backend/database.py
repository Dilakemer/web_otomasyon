from __future__ import annotations

import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
import re


DB_PATH = Path(__file__).with_name("data.db")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with closing(get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fiyatlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_adi TEXT NOT NULL,
                fiyat REAL NOT NULL,
                tarih TEXT NOT NULL,
                urun_url TEXT NOT NULL
            )
            """
        )
        connection.commit()


def insert_price_record(
    urun_adi: str,
    fiyat: float,
    urun_url: str,
    tarih: str | None = None,
) -> None:
    timestamp = tarih or datetime.now().isoformat(timespec="seconds")

    with closing(get_connection()) as connection:
        connection.execute(
            """
            INSERT INTO fiyatlar (urun_adi, fiyat, tarih, urun_url)
            VALUES (?, ?, ?, ?)
            """,
            (urun_adi, fiyat, timestamp, urun_url),
        )
        connection.commit()


def _resolve_product_and_seller(urun_adi_full: str, urun_url: str) -> tuple[str, str]:
    # Beklenen format: "Urun Adi [Satici]"
    m = re.match(r"^(.*) \[(.*)\]$", urun_adi_full)
    if m:
        urun_adi = m.group(1).strip()
        satici = m.group(2).strip()
        if re.match(r"^satici\s+\d+$", _normalize_text(satici)):
            return urun_adi, "Ana Satici"
        if satici and satici.lower() != "bilinmeyen":
            return urun_adi, satici

    return urun_adi_full.strip(), "Ana Satici"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_like = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_like.strip().lower()


def _is_invalid_seller_name(name: str) -> bool:
    n = _normalize_text(name)
    if not n:
        return True
    invalid_exact = {
        "urune git",
        "satici yok",
        "bilinmeyen",
    }
    if n in invalid_exact:
        return True
    if re.match(r"^satici\s+\d+$", n):
        return True

    invalid_contains = [
        "son 10 gun",
        "en dusuk fiyat",
        "tum saticilari goster",
    ]
    return any(token in n for token in invalid_contains)


def _rows_to_grouped_payload(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        urun_adi_full = row["urun_adi"]
        urun_adi, satici = _resolve_product_and_seller(urun_adi_full, row["urun_url"])
        if _is_invalid_seller_name(satici):
            continue
        product = grouped.setdefault(
            row["urun_url"],
            {
                "urun_adi": urun_adi,
                "urun_url": row["urun_url"],
                "saticilar": {},
            },
        )
        seller_list = product["saticilar"].setdefault(satici, [])
        seller_list.append(
            {
                "id": row["id"],
                "fiyat": row["fiyat"],
                "tarih": row["tarih"],
            }
        )
    return list(grouped.values())


def get_grouped_price_history(urun_url: str | None = None) -> list[dict[str, Any]]:
    base_query = """
        SELECT id, urun_adi, fiyat, tarih, urun_url
        FROM fiyatlar
    """
    params: tuple[Any, ...] = ()

    if urun_url:
        base_query += " WHERE urun_url = ?"
        params = (urun_url,)

    base_query += " ORDER BY tarih ASC"

    with closing(get_connection()) as connection:
        rows = connection.execute(base_query, params).fetchall()

    return _rows_to_grouped_payload(rows)


if __name__ == "__main__":
    init_database()
    print(f"Veritabani hazir: {DB_PATH}")
