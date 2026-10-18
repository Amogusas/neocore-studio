#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEOCORE STUDIO // Automated Lead Finder & Website Email Parser
Модуль автоматического поиска компаний по заданной нише, парсинга их сайтов на наличие email-контактов
и сохранения уникальных записей в leads.csv без дубликатов по домену или почте.

Установка зависимостей:
    pip install requests beautifulsoup4
"""

import os
import re
import sys
import csv
import time
import base64
import argparse
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import urllib3

# Отключаем предупреждения о непроверенных SSL-сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка вывода UTF-8 для Windows консоли
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==============================================================================
# КОНФИГУРАЦИЯ ПОИСКОВИКА И ПАРСЕРА
# ==============================================================================
CSV_FILE_PATH = "leads.csv"
CSV_FIELDNAMES = ["name", "niche", "site", "contact_email", "status", "added_at", "sent_at"]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Регулярное выражение для поиска email-адресов
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Пресеты целевых ниш для автопополнения базы
DEFAULT_TARGET_NICHES = [
    "Детейлинг авто студия Москва",
    "Дизайнерский ремонт квартир Москва",
    "Ландшафтный дизайн студия Москва",
    "Архитектурное бюро Москва",
    "Премиальная стоматология Москва"
]

# Черный список агрегаторов, СМИ, маркетплейсов и информационных порталов
AGGREGATOR_DOMAINS = {
    "yandex.ru", "ya.ru", "google.com", "google.ru", "vk.com", "2gis.ru", "avito.ru",
    "hh.ru", "t.me", "youtube.com", "dzen.ru", "wikipedia.org", "habr.com", "zoon.ru",
    "otzovik.com", "fl.ru", "kwork.ru", "profi.ru", "orgpage.ru", "yp.ru", "wildberries.ru",
    "ozon.ru", "aliexpress.ru", "sberbank.ru", "tinkoff.ru", "gosuslugi.ru", "bing.com",
    "yahoo.com", "duckduckgo.com", "expertology.ru", "kp.ru", "vc.ru", "dtf.ru", "pikabu.ru",
    "rbc.ru", "lenta.ru", "ria.ru", "gazeta.ru", "drive2.ru", "auto.ru", "drom.ru", "cian.ru",
    "realty.yandex.ru", "domclick.ru", "kommersant.ru", "irecommend.ru", "banki.ru",
    "championat.com", "sport-express.ru", "livejournal.com", "tripadvisor.ru"
}

# Черный список недопустимых расширений файлов, похожих на email
INVALID_EMAIL_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css", ".js", ".woff", ".woff2", ".ttf", ".ico"
}

# Домены заглушек или служебных систем
IGNORED_EMAIL_DOMAINS = {
    "example.com", "domain.com", "sentry.io", "wixpress.com", "schema.org", "w3.org",
    "bootstrap.com", "cloudflare.com", "googleapis.com", "tilda.ws", "wordpress.org"
}

# ==============================================================================
# РАБОТА С ХРАНИЛИЩЕМ LEADS.CSV
# ==============================================================================
def init_leads_csv(file_path: str = CSV_FILE_PATH):
    """Инициализирует CSV-файл с заголовками, если файл еще не создан."""
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
        print(f"[INIT] Создан файл базы лидов: {file_path}")

def get_existing_leads_keys(file_path: str = CSV_FILE_PATH):
    """
    Возвращает множества существующих доменов и email для предотвращения дубликатов.
    """
    existing_domains = set()
    existing_emails = set()

    if not os.path.exists(file_path):
        return existing_domains, existing_emails

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                site = row.get("site", "").strip()
                email = row.get("contact_email", "").strip().lower()
                if site:
                    dom = extract_root_domain(site)
                    if dom:
                        existing_domains.add(dom)
                if email:
                    existing_emails.add(email)
    except Exception as e:
        print(f"[WARN] Ошибка чтения существующего {file_path}: {e}")

    return existing_domains, existing_emails

def append_lead_to_csv(lead: dict, file_path: str = CSV_FILE_PATH):
    """Добавляет одну уникальную запись в CSV."""
    init_leads_csv(file_path)
    with open(file_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writerow(lead)

# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================================
def extract_root_domain(url: str) -> str:
    """Извлекает чистый домен из URL."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.split(":")[0]
    except Exception:
        return ""

def decode_bing_url(url: str) -> str:
    """Декодирует прямой целевой URL из поисковой выдачи Bing."""
    if "u=a1" in url:
        try:
            b64_part = url.split("u=a1")[1].split("&")[0]
            b64_part += "=" * ((4 - len(b64_part) % 4) % 4)
            return base64.b64decode(b64_part).decode("utf-8", errors="ignore")
        except Exception:
            return url
    return url

def clean_company_name(raw_title: str, domain: str) -> str:
    """Очищает заголовок страницы от рекламных суффиксов, оставляя чистое имя бренда."""
    if not raw_title:
        return domain.capitalize()
    parts = re.split(r"[\s\t]*[|—\-–•::][\s\t]*", raw_title)
    if parts:
        clean = parts[0].strip()
        if len(clean) > 2 and len(clean) < 45:
            return clean
    clean = raw_title.strip()[:45]
    return clean if clean else domain.capitalize()

def is_valid_email(email: str) -> bool:
    """Проверяет валидность email-адреса и отсеивает мусорные расширения и домены."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return False
    if len(email) < 6 or len(email) > 60:
        return False
    if any(email.endswith(ext) for ext in INVALID_EMAIL_EXTENSIONS):
        return False
    domain_part = email.split("@")[-1]
    if domain_part in IGNORED_EMAIL_DOMAINS:
        return False
    return True

# ==============================================================================
# ПАРСИНГ САЙТА НА НАЛИЧИЕ EMAIL
# ==============================================================================
def parse_emails_from_html(html_text: str) -> set:
    """Извлекает email-адреса из mailto: ссылок и текста страницы."""
    found = set()
    if not html_text:
        return found

    soup = BeautifulSoup(html_text, "html.parser")

    # 1. Поиск ссылок mailto:
    for a in soup.select('a[href^="mailto:"]'):
        href = a.get("href", "")
        clean_mail = href.replace("mailto:", "").split("?")[0].strip().lower()
        if is_valid_email(clean_mail):
            found.add(clean_mail)

    # 2. Поиск по тексту и атрибутам через регулярное выражение
    matches = EMAIL_REGEX.findall(html_text)
    for m in matches:
        clean_m = m.strip(".,;:!? \t\r\n'\"").lower()
        if is_valid_email(clean_m):
            found.add(clean_m)

    return found

def find_contact_page_url(soup: BeautifulSoup, base_url: str) -> str:
    """Ищет ссылку на раздел контактов внутри HTML страницы."""
    keywords = ["kontakt", "contact", "контакт", "о нас", "about", "связь", "rekvizit", "реквизит"]
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(strip=True).lower()
        href_lower = href.lower()

        if any(k in href_lower or k in text for k in keywords):
            if not href.startswith("mailto:") and not href.startswith("tel:") and not href.startswith("javascript:"):
                return urllib.parse.urljoin(base_url, href)
    return ""

def extract_lead_from_website(url: str, default_name: str = "") -> dict:
    """
    Загружает главную страницу (и при необходимости страницу контактов)
    и извлекает контактный email и название организации.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    domain = extract_root_domain(url)
    if not domain or domain in AGGREGATOR_DOMAINS:
        return None

    emails = set()
    company_name = default_name

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=8, verify=False)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        # Определение названия бренда
        if not company_name:
            title_tag = soup.find("title")
            raw_title = title_tag.get_text(strip=True) if title_tag else ""
            company_name = clean_company_name(raw_title, domain)

        # Сбор email с главной страницы
        emails.update(parse_emails_from_html(r.text))

        # Если на главной нет email, парсим страницу контактов
        if not emails:
            contact_url = find_contact_page_url(soup, url)
            if contact_url and contact_url != url:
                try:
                    rc = requests.get(contact_url, headers=DEFAULT_HEADERS, timeout=7, verify=False)
                    if rc.status_code == 200:
                        emails.update(parse_emails_from_html(rc.text))
                except Exception:
                    pass

    except Exception:
        return None

    if emails:
        # Приоритет корпоративным адресам
        preferred_prefixes = ("info@", "contact@", "mail@", "hello@", "sales@", "director@", "office@")
        selected_email = None
        for pref in preferred_prefixes:
            for em in emails:
                if em.startswith(pref):
                    selected_email = em
                    break
            if selected_email:
                break

        if not selected_email:
            selected_email = sorted(emails)[0]

        return {
            "name": company_name,
            "site": domain,
            "contact_email": selected_email
        }

    return None

# ==============================================================================
# ПОИСК КОМПАНИЙ ПО НИШЕ
# ==============================================================================
def search_websites_by_niche(niche: str, max_results: int = 15) -> list:
    """
    Ищет сайты компаний в заданной нише через веб-поиск Bing.
    """
    search_queries = [
        f"{niche} официальный сайт",
        f"{niche} студия контакты",
        f"{niche} услуги компания"
    ]

    discovered_candidates = []
    seen_domains = set()

    for query in search_queries:
        if len(discovered_candidates) >= max_results:
            break

        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=9)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            for h2 in soup.find_all("h2"):
                a = h2.find("a")
                if not a:
                    continue
                raw_href = a.get("href", "")
                raw_title = a.get_text(strip=True)

                dest_url = decode_bing_url(raw_href)
                domain = extract_root_domain(dest_url)

                if domain and domain not in AGGREGATOR_DOMAINS and domain not in seen_domains:
                    seen_domains.add(domain)
                    discovered_candidates.append({
                        "name": clean_company_name(raw_title, domain),
                        "url": dest_url
                    })

            time.sleep(1.2)
        except Exception as e:
            print(f"[WARN] Ошибка поискового запроса '{query}': {e}")

    return discovered_candidates[:max_results]

# ==============================================================================
# ОСНОВНОЙ ПРОЦЕСС ПОИСКА И ДОБАВЛЕНИЯ В CSV
# ==============================================================================
def find_and_save_leads(niche: str = "", target_count: int = 3, output_csv: str = CSV_FILE_PATH) -> int:
    """
    Ищет компании по нише, извлекает контакты и добавляет уникальные записи в CSV.
    Возвращает количество добавленных лидов.
    """
    if not niche or "\ufffd" in niche or "?" in niche:
        # Автоматический выбор из качественных пресетов, если передан поврежденный аргумент
        niche = DEFAULT_TARGET_NICHES[0]

    print("=" * 65)
    print(f"[LEAD FINDER] Поиск компаний в нише: '{niche}'")
    print(f"Цель: найти до {target_count} уникальных контактов")
    print("=" * 65)

    init_leads_csv(output_csv)
    existing_domains, existing_emails = get_existing_leads_keys(output_csv)
    print(f"[INFO] Текущая база {output_csv} содержит {len(existing_emails)} email и {len(existing_domains)} доменов.")

    print(f"[SEARCH] Сканирование поисковой выдачи...")
    candidates = search_websites_by_niche(niche, max_results=target_count * 4)
    print(f"[FOUND] Найдено {len(candidates)} потенциальных сайтов компаний.")

    new_leads_saved = 0

    for idx, cand in enumerate(candidates, 1):
        if new_leads_saved >= target_count:
            break

        cand_url = cand["url"]
        domain = extract_root_domain(cand_url)

        if domain in existing_domains or domain in AGGREGATOR_DOMAINS:
            continue

        print(f"[{idx}/{len(candidates)}] [SCAN] Проверка сайта {cand_url}...")
        lead_data = extract_lead_from_website(cand_url, default_name=cand["name"])

        if lead_data:
            email = lead_data["contact_email"]
            if email in existing_emails:
                print(f"  -> [SKIP] Email {email} уже есть в базе.")
                continue

            lead_record = {
                "name": lead_data["name"],
                "niche": niche,
                "site": lead_data["site"],
                "contact_email": email,
                "status": "pending",
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sent_at": ""
            }

            append_lead_to_csv(lead_record, output_csv)
            existing_domains.add(domain)
            existing_emails.add(email)
            new_leads_saved += 1

            print(f"  -> [SUCCESS] Добавлен лид: {lead_data['name']} ({domain}) -> {email}")
        else:
            print(f"  -> [INFO] На сайте {domain} прямой email не обнаружен.")

        time.sleep(1.0)

    print("\n" + "=" * 65)
    print(f"[COMPLETED] Поиск завершен. Добавлено новых уникальных лидов: {new_leads_saved}")
    print(f"Файл сохранен: {os.path.abspath(output_csv)}")
    print("=" * 65)
    return new_leads_saved

# ==============================================================================
# ТОЧКА ВХОДА
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Автоматический поиск лидов и парсер контактов NEOCORE STUDIO")
    parser.add_argument("--niche", type=str, default="", help="Ниша и регион для поиска компаний")
    parser.add_argument("--count", type=int, default=3, help="Сколько уникальных лидов с почтами требуется найти")
    parser.add_argument("--csv", type=str, default=CSV_FILE_PATH, help="Путь к файлу leads.csv")

    args = parser.parse_args()
    find_and_save_leads(niche=args.niche, target_count=args.count, output_csv=args.csv)

if __name__ == "__main__":
    main()
