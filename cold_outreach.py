#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEOCORE STUDIO // Automated B2B Cold Outreach Engine
Модуль автоматизированной отправки коммерческих предложений из leads.csv
с генерацией офферов через Google Gemini 3.8 Flash и доставкой через SMTP.

Установка зависимостей:
    pip install google-genai requests beautifulsoup4
"""

import os
import sys
import csv
import time
import smtplib
import argparse
import html
import urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outreach.log")

class DualLogger:
    """Дублирует весь вывод одновременно в консоль и в файл outreach.log."""
    def __init__(self, filepath, stream):
        self.stream = stream
        self.logfile = open(filepath, "a", encoding="utf-8", buffering=1)

    def write(self, message):
        try:
            self.stream.write(message)
        except Exception:
            pass
        try:
            self.logfile.write(message)
        except Exception:
            pass

    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass
        try:
            self.logfile.flush()
        except Exception:
            pass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.stdout = DualLogger(LOG_FILE_PATH, sys.stdout)
sys.stderr = DualLogger(LOG_FILE_PATH, sys.stderr)

# Автоматическая загрузка переменных окружения из .env
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

# ==============================================================================
# КОНФИГУРАЦИЯ СЕРВИСОВ И АВТОМАТИЗАЦИИ
# ==============================================================================

# 1. Ключ Google Gemini API и модель (Gemini 3.8 Flash)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# 2. SMTP-настройки почтового сервера (Gmail)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "stupapupa228777@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# 3. Данные студии NEOCORE
STUDIO_NAME = "NEOCORE Studio"
STUDIO_PORTFOLIO = "https://amogusas.github.io/neocore-studio/"
STUDIO_TELEGRAM = "https://t.me/neocore_studio"
STUDIO_EMAIL = os.getenv("SMTP_USER", "stupapupa228777@gmail.com")

# 4. Настройки работы с базой лидов
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads.csv")
CSV_FIELDNAMES = ["name", "niche", "site", "contact_email", "status", "added_at", "sent_at"]
DISPATCH_DELAY_SECONDS = 15
AUTO_REPLENISH_LEADS = True  # Автоматический вызов lead_finder, если база пуста

# Резервная тестовая база для безопасного старта
INITIAL_TEST_LEADS = [
    {
        "name": "Apex Detailing Lab",
        "niche": "Премиальный автодетейлинг и бронепленка",
        "site": "apex-detailing-demo.ru",
        "contact_email": "stupapupa228777@gmail.com",
        "status": "pending",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sent_at": ""
    },
    {
        "name": "Nordic Renovation",
        "niche": "Дизайнерский ремонт квартир и загородных коттеджей",
        "site": "nordic-remont-sample.ru",
        "contact_email": "stupapupa228777@gmail.com",
        "status": "pending",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sent_at": ""
    },
    {
        "name": "Krono Watches",
        "niche": "Интернет-магазин оригинальных наручных часов",
        "site": "krono-store-demo.ru",
        "contact_email": "stupapupa228777@gmail.com",
        "status": "pending",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sent_at": ""
    }
]

# ==============================================================================
# УПРАВЛЕНИЕ БАЗОЙ ЛИДОВ (LEADS.CSV)
# ==============================================================================
def init_leads_csv(file_path: str = CSV_FILE_PATH):
    """Инициализирует leads.csv тестовыми данными, если файл отсутствует."""
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
            for lead in INITIAL_TEST_LEADS:
                writer.writerow(lead)
        print(f"[INIT] Создан файл {file_path} с {len(INITIAL_TEST_LEADS)} начальными лидами.")

def load_leads_from_csv(file_path: str = CSV_FILE_PATH) -> list:
    """Загружает все записи из CSV файла."""
    if not os.path.exists(file_path):
        init_leads_csv(file_path)

    leads = []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(row)
    except Exception as e:
        print(f"[ERROR] Ошибка чтения {file_path}: {e}")
    return leads

def update_lead_status(file_path: str, contact_email: str, new_status: str, sent_at: str = "") -> bool:
    """
    Обновляет статус и время отправки конкретного лида в leads.csv.
    Поддерживает поиск как по сырому, так и по URL-декодированному email.
    """
    leads = load_leads_from_csv(file_path)
    updated = False
    clean_target = urllib.parse.unquote(html.unescape(contact_email)).strip().lower()

    for row in leads:
        row_mail = row.get("contact_email", "").strip().lower()
        clean_row_mail = urllib.parse.unquote(html.unescape(row_mail)).strip().lower()

        if row_mail == contact_email.strip().lower() or clean_row_mail == clean_target:
            row["contact_email"] = clean_target  # нормализуем email в базе к чистому виду
            if row.get("status") != "sent" or new_status == "sent":
                row["status"] = new_status
                if sent_at:
                    row["sent_at"] = sent_at
                updated = True
                break

    if updated:
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()
                for row in leads:
                    writer.writerow(row)
            return True
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить статус в {file_path}: {e}")
            return False
    return False

def replenish_leads_from_finder(file_path: str = CSV_FILE_PATH, count_per_niche: int = 2, count: int = None) -> int:
    """
    Вызывает модуль lead_finder для автоматического пополнения базы новых лидов по целевым нишам.
    """
    if count is not None:
        count_per_niche = count
    print(f"[AUTOLOAD] Запуск автоматического поиска новых контактов через lead_finder...")
    try:
        import lead_finder
        added = lead_finder.find_and_save_all_niches(
            count_per_niche=count_per_niche,
            output_csv=file_path
        )
        return added
    except Exception as e:
        print(f"[WARN] Не удалось выполнить автопополнение через lead_finder: {e}")
        return 0

def count_sent_today(file_path: str = CSV_FILE_PATH, day_str: str = "") -> int:
    """Подсчитывает количество успешно отправленных писем за указанную дату."""
    if not day_str:
        day_str = datetime.now().strftime("%Y-%m-%d")
    leads = load_leads_from_csv(file_path)
    count = 0
    for l in leads:
        if l.get("status", "").strip().lower() == "sent":
            sent_at = l.get("sent_at", "").strip()
            if sent_at.startswith(day_str):
                count += 1
    return count

# ==============================================================================
# ГЕНЕРАЦИЯ ОФФЕРА ЧЕРЕЗ GEMINI 3.8 FLASH
# ==============================================================================
def generate_pitch(company_name: str, niche: str, current_site: str) -> str:
    """
    Генерирует персонализированное коммерческое предложение через Google Gemini 3.8 Flash.
    При сбое API переключается на проверенный резервный шаблон.
    """
    prompt = f"""
Ты — ведущий консультант и технический архитектор веб-студии {STUDIO_NAME}.
Наше портфолио: {STUDIO_PORTFOLIO}
Наш Telegram: {STUDIO_TELEGRAM}

Составь короткое, строго персонализированное B2B-письмо руководителю компании.

Данные клиента:
- Компания: {company_name}
- Ниша: {niche}
- Сайт: {current_site}

Критерии качества:
1. Объем: строго 4-5 предложений. Максимальная концентрация фактов без воды.
2. Никаких эмодзи (строго запрещено использовать любые эмодзи).
3. Проблема: укажи, что в нише "{niche}" типовые шаблонные сайты страдают долгой загрузкой и теряют мобильный трафик до оформления заявки.
4. Решение: предложи стек NEOCORE — 3D WebGL интерактив со скоростью 60 FPS, калькулятор предварительного расчета и прямую мгновенную доставку заявок в Telegram.
5. Призыв к действию: мягко предложить записать 30-секундный видеоразбор с концептом экрана для их бренда или показать интерактивное демо.
6. Подпись: {STUDIO_NAME} с ссылкой на портфолио ({STUDIO_PORTFOLIO}) и Telegram ({STUDIO_TELEGRAM}).
7. Верни ТОЛЬКО готовый текст письма.
"""

    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
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
                    return response.text.strip()
            except Exception as e:
                continue

    # Надежный высококонверсионный шаблон (Fallback)
    fallback_pitch = (
        f"Здравствуйте, команда {company_name}.\n\n"
        f"Обратил внимание на ваш проект в сфере {niche}. Большинство типовых сайтов в вашей нише "
        f"страдают долгой загрузкой и перегруженными формами, теряя до 40% целевого мобильного трафика.\n\n"
        f"Мы в {STUDIO_NAME} создаем веб-платформы нового поколения: плавный 3D WebGL интерактив (60 FPS), "
        f"динамический калькулятор сметы и прямую доставку лидов в Telegram за 1 секунду.\n\n"
        f"Примеры наших реализованных решений доступны в портфолио: {STUDIO_PORTFOLIO}\n\n"
        f"Готовы записать для вас короткое 30-секундное видеодемо с концептом нового интерактивного экрана. "
        f"Подскажите, актуально ли сейчас усиление конверсии сайта?\n\n"
        f"С уважением,\n"
        f"{STUDIO_NAME}\n"
        f"Telegram: {STUDIO_TELEGRAM}\n"
        f"Email: {STUDIO_EMAIL}"
    )
    return fallback_pitch

# ==============================================================================
# ОТПРАВКА ЧЕРЕЗ SMTP
# ==============================================================================
def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Отправляет сформированное письмо через защищенный SMTP шлюз.
    """
    # Полное декодирование URL-escaped и HTML сущностей
    try:
        to_email = urllib.parse.unquote(html.unescape(to_email)).strip().lower()
    except Exception:
        to_email = to_email.strip().lower()

    if not to_email or "@" not in to_email or "%" in to_email or " " in to_email:
        print(f"[SKIP] Некорректный email адрес (RFC 5321): '{to_email}'. Отправка отменена.")
        return False

    if not SMTP_PASSWORD or SMTP_PASSWORD == "YOUR_APP_PASSWORD_HERE":
        print(f"[DRY-RUN] Пароль приложения SMTP не настроен. Симуляция успешной отправки на <{to_email}>.")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{STUDIO_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"[SUCCESS] Отправлено на email: {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка отправки на {to_email}: {e}")
        return False

# ==============================================================================
# АВТОНОМНЫЙ НЕПРЕРЫВНЫЙ ЦИКЛ 24/7
# ==============================================================================
def run_autonomous_loop(
    csv_file: str = CSV_FILE_PATH,
    daily_limit: int = 30,
    delay_seconds: int = DISPATCH_DELAY_SECONDS,
    start_hour: int = 9,
    end_hour: int = 19,
    ignore_hours: bool = False,
    idle_sleep_seconds: int = 1800
):
    """
    Непрерывный автономный демон рассылки 24/7 с контролем дневных лимитов,
    соблюдением рабочих часов и автоматическим добором лидов при пустой очереди.
    """
    print("=" * 65)
    print(f"[{STUDIO_NAME}] Запуск автономного режима аутрича 24/7")
    print(f"Источник базы: {csv_file}")
    print(f"Дневной лимит: {daily_limit} писем/сутки")
    if ignore_hours:
        print("Рабочие часы: круглосуточно (контроль времени отключен)")
    else:
        print(f"Рабочие часы отправки: с {start_hour:02d}:00 до {end_hour:02d}:00")
    print(f"Интервал между отправками: {delay_seconds} сек.")
    print("=" * 65)

    current_day = datetime.now().strftime("%Y-%m-%d")
    sent_today = count_sent_today(csv_file, current_day)
    print(f"[STATUS] За сегодня ({current_day}) уже отправлено: {sent_today}/{daily_limit} писем.")

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # Смена календарного дня - сброс дневного счетчика
            if today_str != current_day:
                current_day = today_str
                sent_today = count_sent_today(csv_file, current_day)
                print(f"\n[NEW DAY] Наступил новый день: {current_day}. Дневной счетчик сброшен.")

            # Проверка рабочих часов (B2B этика: не слать в нерабочее время)
            if not ignore_hours and not (start_hour <= now.hour < end_hour):
                if now.hour >= end_hour:
                    next_run = (now.replace(hour=start_hour, minute=0, second=0, microsecond=0) + timedelta(days=1))
                else:
                    next_run = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)

                sleep_secs = max(60, int((next_run - now).total_seconds()))
                hours_sleep = round(sleep_secs / 3600, 1)
                print(f"[NIGHT MODE] Вне рабочих часов ({start_hour:02d}:00 - {end_hour:02d}:00). Пауза до {next_run.strftime('%Y-%m-%d %H:%M:%S')} (~{hours_sleep} ч.)...")
                time.sleep(min(sleep_secs, 1800))
                continue

            # Проверка исчерпания дневного лимита
            if sent_today >= daily_limit:
                tomorrow = (now + timedelta(days=1)).replace(hour=start_hour if not ignore_hours else 0, minute=0, second=0, microsecond=0)
                sleep_secs = max(60, int((tomorrow - now).total_seconds()))
                hours_sleep = round(sleep_secs / 3600, 1)
                print(f"[LIMIT REACHED] Дневной лимит ({daily_limit} писем) исчерпан. Ожидание следующего дня до {tomorrow.strftime('%Y-%m-%d %H:%M:%S')} (~{hours_sleep} ч.)...")
                time.sleep(min(sleep_secs, 1800))
                continue

            # Загрузка базы
            all_leads = load_leads_from_csv(csv_file)
            pending_leads = [l for l in all_leads if l.get("status", "").strip().lower() != "sent"]

            # Если база исчерпана - автопополнение
            if not pending_leads and AUTO_REPLENISH_LEADS:
                print("\n[AUTOLOAD] В базе нет неотправленных контактов. Запуск lead_finder по всем нишам...")
                added = replenish_leads_from_finder(csv_file, count_per_niche=2)
                all_leads = load_leads_from_csv(csv_file)
                pending_leads = [l for l in all_leads if l.get("status", "").strip().lower() != "sent"]
                print(f"[AUTOLOAD] Добавлено {added} новых лидов в очередь.")

            if not pending_leads:
                print(f"[IDLE] Новых лидов в очереди нет. Ожидание {round(idle_sleep_seconds / 60)} мин. перед повторной проверкой...")
                time.sleep(idle_sleep_seconds)
                continue

            # Обрабатываем один лид из очереди
            lead = pending_leads[0]
            company = lead.get("name", "Компания")
            niche = lead.get("niche", "Сфера услуг")
            site = lead.get("site", "официальный сайт")
            raw_email = lead.get("contact_email", "").strip()
            email = urllib.parse.unquote(html.unescape(raw_email)).strip().lower()

            print(f"\n[DISPATCH] [{sent_today + 1}/{daily_limit}] Обработка: {company} ({niche})")
            print(f"[TARGET] Адрес получателя: {email}")

            if not email or "@" not in email or "%" in email:
                print(f"[SKIP] Некорректный email адрес: '{email}'. Статус: invalid_email.")
                update_lead_status(csv_file, raw_email, new_status="invalid_email")
                continue

            print(f"[AI] Генерация персонализированного оффера ({GEMINI_MODEL})...")
            subject = f"{company} // Увеличение конверсии сайта и 3D-интерактив"
            pitch = generate_pitch(company, niche, site)

            print(f"[SEND] Отправка через SMTP-сервер ({SMTP_SERVER})...")
            is_sent = send_email(email, subject, pitch)

            if is_sent:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                update_lead_status(csv_file, email, new_status="sent", sent_at=now_str)
                sent_today += 1
                print(f"[PROGRESS] Успешно отправлено. Сегодняшний прогресс: {sent_today}/{daily_limit} писем.")
            else:
                update_lead_status(csv_file, email, new_status="failed")
                print(f"[WARN] Ошибка отправки на {email}. Статус обновлен на failed.")

            if sent_today < daily_limit:
                print(f"[PAUSE] Пауза {delay_seconds} сек. для защиты репутации домена...")
                time.sleep(delay_seconds)

        except KeyboardInterrupt:
            print("\n[STOP] Автономный режим 24/7 остановлен пользователем.")
            break
        except Exception as e:
            print(f"[ERROR] Ошибка в автономном цикле: {e}")
            time.sleep(60)

# ==============================================================================
# РАЗОВЫЙ ПАКЕТНЫЙ ЗАПУСК
# ==============================================================================
def run_single_batch(csv_file: str = CSV_FILE_PATH, delay_seconds: int = DISPATCH_DELAY_SECONDS):
    """
    Обрабатывает текущую очередь leads.csv один раз и завершает выполнение.
    """
    print("=" * 65)
    print(f"[{STUDIO_NAME}] Модуль разового B2B-аутрича")
    print(f"Источник базы: {csv_file}")
    print(f"Модель генерации: {GEMINI_MODEL}")
    print(f"Задержка между отправками: {delay_seconds} сек.")
    print("=" * 65)

    all_leads = load_leads_from_csv(csv_file)
    pending_leads = [l for l in all_leads if l.get("status", "").strip().lower() != "sent"]

    # Автопополнение, если неотправленных лидов не осталось
    if not pending_leads and AUTO_REPLENISH_LEADS:
        print("[INFO] В базе leads.csv нет неотправленных лидов. Запуск автопополнения...")
        replenish_leads_from_finder(csv_file, count_per_niche=2)
        all_leads = load_leads_from_csv(csv_file)
        pending_leads = [l for l in all_leads if l.get("status", "").strip().lower() != "sent"]

    if not pending_leads:
        print("[INFO] Очередь отправки пуста. Все контакты из базы уже обработаны.")
        print("Для запуска непрерывного режима используйте: python cold_outreach.py --loop")
        return

    print(f"[QUEUE] Найдено {len(pending_leads)} лидов со статусом 'pending' (не отправлено).")

    for index, lead in enumerate(pending_leads, 1):
        company = lead.get("name", "Компания")
        niche = lead.get("niche", "Сфера услуг")
        site = lead.get("site", "официальный сайт")
        raw_email = lead.get("contact_email", "").strip()
        email = urllib.parse.unquote(html.unescape(raw_email)).strip().lower()

        print(f"\n[{index}/{len(pending_leads)}] Обработка: {company} | Ниша: {niche}")
        print(f"[TARGET] Адрес получателя: {email}")

        if not email or "@" not in email or "%" in email:
            print(f"[SKIP] Некорректный email адрес: '{email}'. Пропуск записи.")
            update_lead_status(csv_file, raw_email, new_status="invalid_email")
            continue

        print(f"[AI] Генерация оффера через {GEMINI_MODEL}...")
        subject = f"{company} // Увеличение конверсии сайта и 3D-интерактив"
        pitch = generate_pitch(company, niche, site)

        print("\n--- СФОРМИРОВАННЫЙ ТЕКСТ ПИСЬМА ---")
        print(pitch)
        print("------------------------------------\n")

        print(f"[SEND] Отправка через SMTP-сервер ({SMTP_SERVER})...")
        is_sent = send_email(email, subject, pitch)

        if is_sent:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_lead_status(csv_file, email, new_status="sent", sent_at=now_str)
            print(f"[UPDATED] Запись {email} помечена как 'sent' в {csv_file}.")
        else:
            update_lead_status(csv_file, email, new_status="failed")
            print(f"[WARN] Запись {email} помечена как 'failed' в {csv_file}.")

        if index < len(pending_leads):
            print(f"[PAUSE] Ожидание {delay_seconds} сек. для защиты от спам-фильтров...")
            time.sleep(delay_seconds)

    print("\n" + "=" * 65)
    print("[COMPLETED] Вся очередь неотправленных лидов успешно обработана.")
    print(f"Актуальное состояние базы зафиксировано в {csv_file}")
    print("=" * 65)

# ==============================================================================
# ТОЧКА ВХОДА
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Автоматизированный B2B-аутрич NEOCORE STUDIO")
    parser.add_argument("--loop", action="store_true", help="Запустить автономный непрерывный режим 24/7")
    parser.add_argument("--daily-limit", type=int, default=30, help="Дневной лимит отправок (по умолчанию: 30)")
    parser.add_argument("--delay", type=int, default=DISPATCH_DELAY_SECONDS, help="Задержка между письмами в сек. (по умолчанию: 15)")
    parser.add_argument("--start-hour", type=int, default=9, help="Час начала отправки (по умолчанию: 9)")
    parser.add_argument("--end-hour", type=int, default=19, help="Час завершения отправки (по умолчанию: 19)")
    parser.add_argument("--ignore-hours", action="store_true", help="Отправлять в любое время, игнорируя ночные часы")
    parser.add_argument("--idle-sleep", type=int, default=1800, help="Пауза при пустой очереди в сек. (по умолчанию: 1800)")
    parser.add_argument("--csv", type=str, default=CSV_FILE_PATH, help="Путь к файлу базы leads.csv")

    args = parser.parse_args()

    if args.loop:
        run_autonomous_loop(
            csv_file=args.csv,
            daily_limit=args.daily_limit,
            delay_seconds=args.delay,
            start_hour=args.start_hour,
            end_hour=args.end_hour,
            ignore_hours=args.ignore_hours,
            idle_sleep_seconds=args.idle_sleep
        )
    else:
        run_single_batch(
            csv_file=args.csv,
            delay_seconds=args.delay
        )

if __name__ == "__main__":
    main()
