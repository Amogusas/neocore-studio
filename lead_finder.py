#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEOCORE STUDIO // Automated Multi-Niche Lead Discovery & Verification Engine
Интеллектуальный модуль автоматического поиска компаний по всем коммерческим нишам,
парсинга их официальных сайтов на контактные email и пополнения базы leads.csv без дубликатов.

Установка зависимостей:
    pip install google-genai requests beautifulsoup4
"""

import os
import re
import sys
import csv
import json
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
# ЗАГРУЗКА ОКРУЖЕНИЯ И КОНФИГУРАЦИЯ
# ==============================================================================
def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.csv")
CSV_FIELDNAMES = ["name", "niche", "site", "contact_email", "status", "added_at", "sent_at"]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# ==============================================================================
# ПОЛНЫЙ КАТАЛОГ ВЫСОКОДОХОДНЫХ КОММЕРЧЕСКИХ НИШ
# ==============================================================================
COMMERCIAL_NICHES_CATALOG = [
    # 1. Автобизнес и премиальный детейлинг
    "Детейлинг студия премиум Москва",
    "Оклейка авто бронепленкой Москва",
    "Тюнинг ателье премиум Москва",

    # 2. Недвижимость, элитный ремонт и архитектура
    "Дизайнерский ремонт квартир Москва",
    "Студия дизайна интерьера Москва",
    "Архитектурное бюро проектирование Москва",
    "Ландшафтный дизайн загородных участков Москва",
    "Строительство загородных коттеджей Москва",

    # 3. Премиальная медицина и эстетика
    "Премиальная стоматология виниры Москва",
    "Клиника эстетической медицины косметология Москва",
    "Центр лазерной коррекции зрения Москва",

    # 4. Премиальные заказные товары и производство
    "Дизайнерская мебель на заказ Москва",
    "Интернет-магазин оригинальных наручных часов Москва",
    "Студия элитного освещения Москва",

    # 5. B2B консалтинг, право и логистика
    "Юридическая компания для бизнеса Москва",
    "Аудиторская компания консалтинг Москва",
    "Таможенное оформление логистика ВЭД Москва",

    # 6. Мероприятия и сфера гостеприимства
    "Event агентство организация мероприятий Москва",
    "Премиальный кейтеринг банкеты Москва"
]

# Проверенные каталоги компаний для каждой ниши (резервный источник высокой надежности)
SEED_CATALOG_COMPANIES = {
    "Детейлинг студия премиум Москва": [
        {"name": "Brooklands Detailing", "site": "brooklands.ru"},
        {"name": "Advance Star", "site": "advancestar.ru"},
        {"name": "Brothers Style", "site": "brothers-style.ru"},
        {"name": "Detailer", "site": "detailer.ru"},
        {"name": "Fast and Shine", "site": "fastnshine.ru"}
    ],
    "Оклейка авто бронепленкой Москва": [
        {"name": "Autosecurity", "site": "autosecurity.ru"},
        {"name": "Car-Stile", "site": "car-stile.ru"},
        {"name": "VinylRussia", "site": "vinylrussia.ru"},
        {"name": "Wrap Team", "site": "wrapteam.ru"},
        {"name": "PTM Studio", "site": "ptmstudio.ru"}
    ],
    "Тюнинг ателье премиум Москва": [
        {"name": "Morendi", "site": "morendi.ru"},
        {"name": "Seven Force", "site": "sevenforce.ru"},
        {"name": "Level Performance", "site": "level-p.ru"},
        {"name": "Gosha Turbo Tech", "site": "goshapb.ru"},
        {"name": "K8 Strasse", "site": "k8-strasse.com"}
    ],
    "Дизайнерский ремонт квартир Москва": [
        {"name": "СВ-Сервис", "site": "svservice.ru"},
        {"name": "Domeo", "site": "domeo.ru"},
        {"name": "Авальремонт", "site": "avalremont.ru"},
        {"name": "Фундамент", "site": "remont-f.ru"},
        {"name": "Вира-АртСтрой", "site": "eremont.ru"}
    ],
    "Студия дизайна интерьера Москва": [
        {"name": "Geometrix Design", "site": "geometrix.ru"},
        {"name": "Studia 54", "site": "studia-54.ru"},
        {"name": "Chado", "site": "chado.pro"},
        {"name": "Buro 108", "site": "buro108.ru"},
        {"name": "Artlebedev", "site": "artlebedev.ru"}
    ],
    "Архитектурное бюро проектирование Москва": [
        {"name": "Архитектурное бюро SPEECH", "site": "speech.su"},
        {"name": "Wowhaus", "site": "wowhaus.ru"},
        {"name": "Цимайло Ляшенко и Партнеры", "site": "tlp-architects.ru"},
        {"name": "Атриум", "site": "atrium.ru"},
        {"name": "Сергей Скуратов Architects", "site": "skuratov-arch.ru"}
    ],
    "Ландшафтный дизайн загородных участков Москва": [
        {"name": "Imperial Garden", "site": "imperialgarden.ru"},
        {"name": "Илья Мочалов и Партнеры", "site": "mochalov.pro"},
        {"name": "L-Beauty", "site": "l-beauty.ru"},
        {"name": "Гармония Сада", "site": "harmony-garden.ru"},
        {"name": "Art Green Design", "site": "art-green.ru"}
    ],
    "Строительство загородных коттеджей Москва": [
        {"name": "GOOD WOOD", "site": "gwd.ru"},
        {"name": "Honka", "site": "honka.ru"},
        {"name": "Ренессанс Строительство", "site": "ren-build.ru"},
        {"name": "Мера-Строй", "site": "mera-stroy.ru"},
        {"name": "Visilla", "site": "visilla.com"}
    ],
    "Премиальная стоматология виниры Москва": [
        {"name": "Kraftway Clinic", "site": "kraftway.ru"},
        {"name": "EMC Dental", "site": "emcmos.ru"},
        {"name": "Президент Дент", "site": "president-dent.ru"},
        {"name": "Ильинская больница", "site": "ihospital.ru"},
        {"name": "Немецкий Имплантологический Центр", "site": "gic-dent.ru"}
    ],
    "Клиника эстетической медицины косметология Москва": [
        {"name": "Remedy Lab", "site": "remedylab.ru"},
        {"name": "Сенсави", "site": "sensavi.ru"},
        {"name": "Эстелаб", "site": "estelab.ru"},
        {"name": "Gen87", "site": "gen87.ru"},
        {"name": "Tori Clinic", "site": "toriclinic.ru"}
    ],
    "Центр лазерной коррекции зрения Москва": [
        {"name": "Клиника 3Z", "site": "3z.ru"},
        {"name": "МНТК Микрохирургия глаза", "site": "mntk.ru"},
        {"name": "Клиника Сфера", "site": "sferaeyecenter.ru"},
        {"name": "Эксимер", "site": "excimerclinic.ru"},
        {"name": "Восток-Прозрение", "site": "vostok-prozrenie.ru"}
    ],
    "Дизайнерская мебель на заказ Москва": [
        {"name": "Dantone Home", "site": "dantonehome.ru"},
        {"name": "Mr.Doors", "site": "mrdoors.ru"},
        {"name": "Giulia Novars", "site": "giulianovars.ru"},
        {"name": "Archpole", "site": "archpole.ru"},
        {"name": "Wooddi", "site": "wooddi.ru"}
    ],
    "Интернет-магазин оригинальных наручных часов Москва": [
        {"name": "Conquest Watches", "site": "conquest-watches.ru"},
        {"name": "AllTime", "site": "alltime.ru"},
        {"name": "Harold", "site": "haroldltd.ru"},
        {"name": "Bestwatch", "site": "bestwatch.ru"},
        {"name": "SwissTime Club", "site": "swisstime-club.ru"}
    ],
    "Студия элитного освещения Москва": [
        {"name": "Центрсвет", "site": "centrsvet.ru"},
        {"name": "Massive Light", "site": "massive-light.ru"},
        {"name": "Свет Онлайн", "site": "svet-online.ru"},
        {"name": "Artlight", "site": "artlight.ru"},
        {"name": "Palantir", "site": "palantirsvet.ru"}
    ],
    "Юридическая компания для бизнеса Москва": [
        {"name": "Vegas Lex", "site": "vegaslex.ru"},
        {"name": "Пепеляев Групп", "site": "pgplaw.ru"},
        {"name": "АЛРУД", "site": "alrud.ru"},
        {"name": "ЕПАМ", "site": "epam.ru"},
        {"name": "BGP Litigation", "site": "bgplaw.com"}
    ],
    "Аудиторская компания консалтинг Москва": [
        {"name": "Б1 (Бизнес Решения)", "site": "b1.ru"},
        {"name": "Kept", "site": "kept.ru"},
        {"name": "ТеДо (Технологии Доверия)", "site": "tedo.ru"},
        {"name": "ФинЭкспертиза", "site": "finexpertiza.ru"},
        {"name": "Юникон", "site": "unicon.ru"}
    ],
    "Таможенное оформление логистика ВЭД Москва": [
        {"name": "Major Cargo Service", "site": "mjr.ru"},
        {"name": "Русмарин", "site": "rusmarine.ru"},
        {"name": "Транзит Логистик", "site": "transitllc.ru"},
        {"name": "КВТ Сервис", "site": "kvtservice.ru"},
        {"name": "ВЭД Агент", "site": "vedagent.ru"}
    ],
    "Event агентство организация мероприятий Москва": [
        {"name": "Подъёжики", "site": "eventpod.ru"},
        {"name": "MAXIMICE", "site": "maximice.ru"},
        {"name": "Redday", "site": "redday.ru"},
        {"name": "Departament New&Wow", "site": "departament.com"},
        {"name": "Darsy", "site": "darsy-event.ru"}
    ],
    "Премиальный кейтеринг банкеты Москва": [
        {"name": "Dellos Catering", "site": "delloscatering.ru"},
        {"name": "Novikov Catering", "site": "novikovcatering.ru"},
        {"name": "Diamond Catering", "site": "diamondcatering.ru"},
        {"name": "Corso Catering", "site": "corsocatering.ru"},
        {"name": "ChanteCler", "site": "chantecler.ru"}
    ]
}

# Черный список агрегаторов, СМИ и каталогов
AGGREGATOR_DOMAINS = {
    "yandex.ru", "ya.ru", "google.com", "google.ru", "vk.com", "2gis.ru", "avito.ru",
    "hh.ru", "t.me", "youtube.com", "dzen.ru", "wikipedia.org", "habr.com", "zoon.ru",
    "otzovik.com", "fl.ru", "kwork.ru", "profi.ru", "orgpage.ru", "yp.ru", "wildberries.ru",
    "ozon.ru", "aliexpress.ru", "sberbank.ru", "tinkoff.ru", "gosuslugi.ru", "bing.com",
    "yahoo.com", "duckduckgo.com", "expertology.ru", "kp.ru", "vc.ru", "dtf.ru", "pikabu.ru",
    "rbc.ru", "lenta.ru", "ria.ru", "gazeta.ru", "drive2.ru", "auto.ru", "drom.ru", "cian.ru",
    "realty.yandex.ru", "domclick.ru", "kommersant.ru", "irecommend.ru", "banki.ru",
    "championat.com", "sport-express.ru", "livejournal.com", "tripadvisor.ru", "allcafe.ru"
}

INVALID_EMAIL_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css", ".js", ".woff", ".woff2", ".ttf", ".ico"
}

IGNORED_EMAIL_DOMAINS = {
    "example.com", "domain.com", "sentry.io", "wixpress.com", "schema.org", "w3.org",
    "bootstrap.com", "cloudflare.com", "googleapis.com", "tilda.ws", "wordpress.org"
}

# ==============================================================================
# УПРАВЛЕНИЕ ХРАНИЛИЩЕМ LEADS.CSV
# ==============================================================================
def init_leads_csv(file_path: str = CSV_FILE_PATH):
    """Создает CSV файл с заголовками, если файл еще не создан."""
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
        print(f"[INIT] Создан файл базы лидов: {file_path}")

def get_existing_leads_keys(file_path: str = CSV_FILE_PATH):
    """Возвращает множества существующих доменов и email для дедупликации."""
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
        print(f"[WARN] Ошибка чтения {file_path}: {e}")

    return existing_domains, existing_emails

def append_lead_to_csv(lead: dict, file_path: str = CSV_FILE_PATH):
    """Добавляет одну уникальную запись в CSV."""
    init_leads_csv(file_path)
    with open(file_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writerow(lead)

# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ОЧИСТКА ДАННЫХ
# ==============================================================================
def extract_root_domain(url: str) -> str:
    """Извлекает чистый домен из URL."""
    try:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.split(":")[0]
    except Exception:
        return ""

def clean_company_name(raw_title: str, domain: str) -> str:
    """Очищает заголовок сайта до чистого названия бренда."""
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
    """Проверяет валидность email-адреса и фильтрует мусор."""
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
# ПАРСИНГ ЖИВОГО САЙТА НА НАЛИЧИЕ EMAIL
# ==============================================================================
def parse_emails_from_html(html_text: str) -> set:
    """Извлекает email-адреса из mailto: и регулярных выражений."""
    found = set()
    if not html_text:
        return found

    soup = BeautifulSoup(html_text, "html.parser")

    # 1. Ссылки mailto:
    for a in soup.select('a[href^="mailto:"]'):
        href = a.get("href", "")
        clean_mail = href.replace("mailto:", "").split("?")[0].strip().lower()
        if is_valid_email(clean_mail):
            found.add(clean_mail)

    # 2. Поиск по тексту регулярным выражением
    matches = EMAIL_REGEX.findall(html_text)
    for m in matches:
        clean_m = m.strip(".,;:!? \t\r\n'\"").lower()
        if is_valid_email(clean_m):
            found.add(clean_m)

    return found

def find_contact_page_url(soup: BeautifulSoup, base_url: str) -> str:
    """Ищет ссылку на раздел контактов внутри HTML."""
    keywords = ["kontakt", "contact", "контакт", "о нас", "about", "связь", "rekvizit", "реквизит", "feedback"]
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
    Загружает официальный сайт компании, проверяет доступность,
    обходит контакты и возвращает проверенный email.
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

        if not company_name:
            title_tag = soup.find("title")
            raw_title = title_tag.get_text(strip=True) if title_tag else ""
            company_name = clean_company_name(raw_title, domain)

        emails.update(parse_emails_from_html(r.text))

        # Если на главной нет email, ищем страницу контактов
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
        # Приоритет официальным корпоративным почтам
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
# ПОИСК ЦЕЛЕВЫХ КОМПАНИЙ ЧЕРЕЗ ИНТЕЛЛЕКТУАЛЬНЫЙ МОДУЛЬ GEMINI
# ==============================================================================
def discover_companies_via_gemini(niche: str, count: int = 5) -> list:
    """
    Использует Gemini 3.8 Flash для мгновенного нахождения реальных компаний
    и их официальных сайтов в заданной нише без блокировок и капч.
    """
    if not GEMINI_API_KEY:
        return []

    prompt = f"""
Ты — профессиональный B2B-исследователь рынка.
Найди {count + 2} реальных действующих компаний/студий/бюро в регионе Москва и РФ в нише: "{niche}".
Для каждой компании укажи ее реальное точное название и действующий официальный сайт (домен).
Не указывай агрегаторы (2GIS, Авито, Яндекс, Zoon, Отзовик, HH). Только прямые сайты бизнесов!

Верни результат СТРОГО в формате валидного JSON-массива:
[
  {{"name": "Название компании", "site": "domain.ru"}},
  ...
]
"""
    models_to_try = [GEMINI_MODEL, "gemini-3.5-flash", "gemini-3.5-flash-lite"]
    seen_models = []
    for m in models_to_try:
        if m and m not in seen_models:
            seen_models.append(m)

    for model_name in seen_models:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": 10.0})
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                text = response.text.strip()
                # Извлечение JSON блока из ответа
                json_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if parsed:
                        return parsed
        except Exception as e:
            continue

    return []

# ==============================================================================
# ОСНОВНОЙ ПРОЦЕСС ОБРАБОТКИ ОДНОЙ НИШИ
# ==============================================================================
def find_and_save_leads(niche: str = "", target_count: int = 3, output_csv: str = CSV_FILE_PATH) -> int:
    """
    Ищет компании по заданной нише, верифицирует их сайты и сохраняет новые лиды в CSV.
    """
    if not niche or "\ufffd" in niche or "?" in niche:
        niche = COMMERCIAL_NICHES_CATALOG[0]

    init_leads_csv(output_csv)
    existing_domains, existing_emails = get_existing_leads_keys(output_csv)

    print(f"\n[SCAN] Ниша: '{niche}' (цель: до {target_count} уникальных контактов)")

    # 1. Интеллектуальный поиск кандидатов (Gemini + надежная база ниши)
    candidates = discover_companies_via_gemini(niche, count=target_count * 2)
    seed_candidates = SEED_CATALOG_COMPANIES.get(niche, [])

    combined_candidates = []
    seen_sites = set()
    for cand in candidates + seed_candidates:
        s = cand.get("site", "").strip().lower()
        if s and s not in seen_sites:
            seen_sites.add(s)
            combined_candidates.append(cand)

    new_leads_saved = 0

    # 2. Обход каждого сайта и парсинг реальной контактной почты
    for cand in combined_candidates:
        if new_leads_saved >= target_count:
            break

        cand_site = cand.get("site", "").strip()
        cand_name = cand.get("name", "").strip()
        domain = extract_root_domain(cand_site)

        if not domain or domain in existing_domains or domain in AGGREGATOR_DOMAINS:
            continue

        lead_data = extract_lead_from_website(domain, default_name=cand_name)

        if lead_data:
            email = lead_data["contact_email"]
            if email in existing_emails:
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

            print(f"  + [ЛИД] {lead_data['name']} ({domain}) -> {email}")

        time.sleep(0.6)

    print(f"  -> Итог по нише: добавлено {new_leads_saved} новых уникальных лидов.")
    return new_leads_saved

# ==============================================================================
# АВТОМАТИЧЕСКИЙ ПАЙПЛАЙН ПО ВСЕМ НИШАМ
# ==============================================================================
def find_and_save_all_niches(count_per_niche: int = 3, output_csv: str = CSV_FILE_PATH, delay_between_niches: float = 1.5) -> int:
    """
    Автоматически сканирует все 19 целевых коммерческих ниш каталога
    и наполняет leads.csv уникальными лидами.
    """
    print("=" * 65)
    print("[ALL-NICHES PIPELINE] Запуск автоматического поиска по всем нишам")
    print(f"Всего ниш в очереди: {len(COMMERCIAL_NICHES_CATALOG)}")
    print(f"Цель на каждую нишу: {count_per_niche} уникальных контактов")
    print(f"Файл назначения: {os.path.abspath(output_csv)}")
    print("=" * 65)

    init_leads_csv(output_csv)
    start_domains, start_emails = get_existing_leads_keys(output_csv)
    print(f"[STATUS] До старта в базе уже есть: {len(start_emails)} email и {len(start_domains)} доменов.")

    total_added = 0
    start_time = time.time()

    for idx, niche in enumerate(COMMERCIAL_NICHES_CATALOG, 1):
        print(f"\n[{idx}/{len(COMMERCIAL_NICHES_CATALOG)}] Обработка ниши...")
        try:
            added = find_and_save_leads(niche=niche, target_count=count_per_niche, output_csv=output_csv)
            total_added += added
        except Exception as e:
            print(f"[ERROR] Ошибка сканирования ниши '{niche}': {e}")

        if idx < len(COMMERCIAL_NICHES_CATALOG):
            time.sleep(delay_between_niches)

    elapsed_minutes = round((time.time() - start_time) / 60, 1)
    end_domains, end_emails = get_existing_leads_keys(output_csv)

    print("\n" + "=" * 65)
    print("[COMPLETED] Автоматический сбор по всем нишам успешно завершен!")
    print(f"Время выполнения: {elapsed_minutes} мин.")
    print(f"Всего добавлено новых лидов за прогон: {total_added}")
    print(f"Итоговый размер базы {output_csv}: {len(end_emails)} уникальных контактов")
    print("=" * 65)
    return total_added

# ==============================================================================
# ТОЧКА ВХОДА
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Автоматический сбор лидов по всем нишам NEOCORE STUDIO")
    parser.add_argument("--all", action="store_true", help="Запустить автоматический поиск по ВСЕМ нишам каталога")
    parser.add_argument("--niche", type=str, default="", help="Конкретная ниша (если не указано --all)")
    parser.add_argument("--count", type=int, default=3, help="Количество контактов на каждую нишу")
    parser.add_argument("--csv", type=str, default=CSV_FILE_PATH, help="Путь к файлу базы leads.csv")

    args = parser.parse_args()

    # По умолчанию запускаем сканирование по всем нишам
    if args.all or not args.niche or args.niche.strip().lower() in ("all", "*", "все"):
        find_and_save_all_niches(count_per_niche=args.count, output_csv=args.csv)
    else:
        find_and_save_leads(niche=args.niche, target_count=args.count, output_csv=args.csv)

if __name__ == "__main__":
    main()
