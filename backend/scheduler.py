from __future__ import annotations

import time

import schedule

from scraper import scrape_all_products


def run_scheduled_scrape() -> None:
    print("Zamanlanmis gorev basladi...")

    try:
        results = scrape_all_products()
        print(f"Gorev tamamlandi. Islenen urun sayisi: {len(results)}")
    except Exception as exc:
        print(f"Zamanlayici hatasi: {exc}")


def start_scheduler() -> None:
    schedule.every().day.at("09:00").do(run_scheduled_scrape)
    schedule.every().day.at("21:00").do(run_scheduled_scrape)

    print("Zamanlayici aktif. Gorevler her gun 09:00 ve 21:00 saatlerinde calisacak.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    start_scheduler()
