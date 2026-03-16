from __future__ import annotations


import re
import sys
import time
import unicodedata
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from database import init_database, insert_price_record


TARGET_PRODUCTS = [
    "https://www.trendyol.com/the-purest-solutions/yagli-ve-karma-ciltler-icin-ve-siyah-nokta-karsiti-salisilik-asit-tonik-200-ml-p-146938263?boutiqueId=61&merchantId=164987",
    "https://www.trendyol.com/so-fly/bright-glow-toner-serum-150-ml-p-765306351?boutiqueId=61&merchantId=924716"
]

TITLE_SELECTORS = [
    "h1.pr-new-br",
    "h1.product-name",
    "h1[data-testid='product-name-text']",
    "h1",
]

PRICE_SELECTORS = [
    ".price-view .discounted",  # En güncel indirimli fiyat
    ".prc-box-dscntd",         # Alternatif eski seçici
    "[data-testid='current-price']",
    "[data-testid='price-current-price']",
    ".price-current-price",
    ".product-price-container span",
]

SELLER_CARD_SELECTORS = [
    ".merchant-list .merchant-box",
    ".other-sellers-list .merchant-box",
    ".seller-container",
    ".seller-box-container",
    ".seller-card",
    "[data-testid='seller-card']",
    "[class*='merchant'] [class*='seller']",
    "[class*='seller']",
]

SELLER_NAME_SELECTORS = [
    ".seller-name-text",
    "[class*='seller-name']",
    ".merchant-name",
    ".merchant-text",
    "a",
]

SELLER_PRICE_SELECTORS = [
    ".prc-box-dscntd",
    ".price",
    ".discounted",
    "[class*='price']",
]


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,2200")
    options.add_argument("--lang=tr-TR")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def accept_cookies_if_present(driver: webdriver.Chrome) -> None:
    selectors = [
        (By.ID, "onetrust-accept-btn-handler"),
        (By.XPATH, "//button[contains(., 'Kabul')]"),
    ]

    for by, value in selectors:
        buttons = driver.find_elements(by, value)
        if not buttons:
            continue

        try:
            buttons[0].click()
            time.sleep(1)
            return
        except Exception:
            continue


def open_all_sellers_if_present(driver: webdriver.Chrome) -> None:
    candidates = driver.find_elements(
        By.XPATH,
        "//button[contains(., 'Tüm Satıcıları Göster') or contains(., 'TÜM SATICILARI GÖSTER')]"
        " | //a[contains(., 'Tüm Satıcıları Göster') or contains(., 'TÜM SATICILARI GÖSTER')]"
    )
    if not candidates:
        return
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", candidates[0])
        time.sleep(0.4)
        driver.execute_script("arguments[0].click();", candidates[0])
        time.sleep(1.5)
    except Exception:
        return


def find_first_visible_text(
    driver: webdriver.Chrome,
    selectors: list[str],
    timeout: int = 20,
) -> str:
    wait = WebDriverWait(driver, timeout)

    def locate_text(active_driver: webdriver.Chrome) -> str | bool:
        for selector in selectors:
            elements = active_driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.strip()
                if text:
                    return text
        return False

    return wait.until(locate_text)


def clean_price(raw_price: str) -> float:
    # Sadece ilk bulunan fiyatı al (ör: 315,53 TL)
    normalized = raw_price.replace("TL", "").replace("₺", "")
    normalized = normalized.replace(".", "").replace(",", ".")
    matches = re.findall(r"(\d+(?:\.\d+)?)", normalized)
    if not matches:
        raise ValueError(f"Fiyat çözümlenemedi: {raw_price}")
    return float(matches[0])


def find_first_visible_text_in_element(element, selectors: list[str]) -> str:
    for selector in selectors:
        nodes = element.find_elements(By.CSS_SELECTOR, selector)
        for node in nodes:
            text = node.text.strip()
            if text:
                return text
    return ""


def parse_tl_values(text: str) -> list[float]:
    # Kart metninden sadece TL ile biten fiyatlari yakala.
    matches = re.findall(r"(\d[\d\.]*(?:,\d+)?)\s*TL", text)
    prices: list[float] = []
    for match in matches:
        try:
            prices.append(clean_price(match))
        except ValueError:
            continue
    return prices


def parse_seller_name_from_card_text(card_text: str) -> str:
    for raw_line in card_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if "hizli satici" in lower or "basarili satici" in lower:
            continue
        if "kargo" in lower or "fatura" in lower or "urun" in lower or "ürün" in lower:
            continue
        if "ürüne git" in lower or "urune git" in lower or "tüm satıcıları göster" in lower:
            continue
        if "son 10 gün" in lower or "en düşük fiyat" in lower:
            continue
        if "tl" in lower:
            continue
        if re.match(r"^[0-9]+([\.,][0-9]+)?$", line):
            continue
        return line
    return ""


def is_invalid_seller_name(name: str) -> bool:
    if not name:
        return True
    normalized = unicodedata.normalize("NFKD", name)
    ascii_like = "".join(ch for ch in normalized if not unicodedata.combining(ch)).strip().lower()

    invalid_tokens = {
        "urune git",
        "bilinmeyen",
        "satici yok",
        "son 10 gunun en dusuk fiyati!",
    }
    if ascii_like in invalid_tokens:
        return True
    if re.match(r"^satici\s+\d+$", ascii_like):
        return True
    if "son 10 gun" in ascii_like or "en dusuk fiyat" in ascii_like:
        return True
    return False


def extract_sellers_from_page_source(page_source: str) -> list[tuple[str, float]]:
    # Trendyol'un gomulu JSON'unda satici adi ve variant fiyatlari bulunuyor.
    # Ornek kalip: {"id":123,"name":"Farmagarage","sellerScore":...,"variants":[{"price":{"discountedPrice":{"value":393.91
    pattern = re.compile(
        r'\{"id":\d+,"name":"(?P<name>[^"]+)","sellerScore".*?'
        r'"discountedPrice":\{"value":(?P<price>\d+(?:\.\d+)?)',
        re.DOTALL,
    )

    items: list[tuple[str, float]] = []
    for match in pattern.finditer(page_source):
        seller = match.group("name").strip()
        if is_invalid_seller_name(seller):
            continue
        try:
            price = float(match.group("price"))
        except ValueError:
            continue
        items.append((seller, price))
    return items


def resolve_main_seller_name(page_source: str, product_url: str) -> str:
    merchant_id = parse_qs(urlparse(product_url).query).get("merchantId", [None])[0]
    if not merchant_id:
        return "Ana Satıcı"
    m = re.search(rf'"id":{re.escape(merchant_id)},"name":"([^"]+)"', page_source)
    if m:
        return m.group(1)
    return "Ana Satıcı"


def scrape_product(url: str) -> list[dict[str, str | float]]:
    driver = build_driver()
    results = []
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            lambda active_driver: active_driver.execute_script("return document.readyState") == "complete"
        )
        accept_cookies_if_present(driver)
        title = find_first_visible_text(driver, TITLE_SELECTORS)

        # Ana satıcı (üstteki kutu)
        try:
            main_price = find_first_visible_text(driver, PRICE_SELECTORS)
            price = clean_price(main_price)
            seller_name = ""
            main_seller_nodes = driver.find_elements(By.CSS_SELECTOR, ".merchant-text, .merchant-name, .merchant-info")
            if main_seller_nodes:
                seller_name = main_seller_nodes[0].text.strip()
            if not seller_name or is_invalid_seller_name(seller_name):
                seller_name = resolve_main_seller_name(driver.page_source, url)
            insert_price_record(urun_adi=f"{title} [{seller_name}]", fiyat=price, urun_url=url)
            results.append({"urun_adi": f"{title} [{seller_name}]", "fiyat": price, "urun_url": url})
        except Exception as exc:
            print(f"Ana satıcı fiyatı bulunamadı: {exc}")

        # Diger saticilar bolumu bazen lazy-load ile geldigi icin asagi kaydir.
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
        time.sleep(1.2)
        open_all_sellers_if_present(driver)

        seller_boxes = []
        for selector in SELLER_CARD_SELECTORS:
            seller_boxes.extend(driver.find_elements(By.CSS_SELECTOR, selector))

        seen_pairs: set[tuple[str, float]] = set()
        for box in seller_boxes:
            try:
                card_text = box.text.strip()
                if not card_text:
                    continue

                seller = find_first_visible_text_in_element(box, SELLER_NAME_SELECTORS)
                if is_invalid_seller_name(seller):
                    seller = ""
                if not seller:
                    seller = parse_seller_name_from_card_text(card_text)
                if is_invalid_seller_name(seller):
                    continue

                price_text = find_first_visible_text_in_element(box, SELLER_PRICE_SELECTORS)
                tl_prices = parse_tl_values(price_text) if price_text else []
                if not tl_prices:
                    tl_prices = parse_tl_values(card_text)
                if not tl_prices:
                    continue
                price = min(tl_prices)

                pair = (seller, price)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                insert_price_record(urun_adi=f"{title} [{seller}]", fiyat=price, urun_url=url)
                results.append({"urun_adi": f"{title} [{seller}]", "fiyat": price, "urun_url": url})
            except Exception as exc:
                print(f"Satici kutusunda hata: {exc}")

        # DOM'da gorunmeyen saticilari gomulu JSON kaynagindan da al.
        for seller, price in extract_sellers_from_page_source(driver.page_source):
            pair = (seller, price)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            insert_price_record(urun_adi=f"{title} [{seller}]", fiyat=price, urun_url=url)
            results.append({"urun_adi": f"{title} [{seller}]", "fiyat": price, "urun_url": url})

        return results
    except TimeoutException as exc:
        raise RuntimeError(f"Sayfa zaman aşımına uğradı: {url}") from exc
    finally:
        driver.quit()


def scrape_all_products(product_urls: Iterable[str] | None = None) -> list[dict[str, str | float]]:
    init_database()
    urls = list(product_urls or TARGET_PRODUCTS)
    results: list[dict[str, str | float]] = []
    for url in urls:
        results.extend(scrape_product(url))
    return results


if __name__ == "__main__":
    urls = sys.argv[1:] or None
    items = scrape_all_products(urls)
    for item in items:
        print(f"{item['urun_adi']} | {item['fiyat']} TL | {item['urun_url']}")
