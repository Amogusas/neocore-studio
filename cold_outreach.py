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
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Обеспечение корректного вывода UTF-8 в Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
    Исключает повторные отправки при перезапуске скрипта.
    """
    leads = load_leads_from_csv(file_path)
    updated = False

    for row in leads:
        if row.get("contact_email", "").strip().lower() == contact_email.strip().lower():
            if row.get("status") != "sent":
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
# ОСНОВНОЙ РАБОЧИЙ ЦИКЛ
# ==============================================================================
def main():
    print("=" * 65)
    print(f"[{STUDIO_NAME}] Модуль автоматического B2B-аутрича")
    print(f"Источник базы: {CSV_FILE_PATH}")
    print(f"Модель генерации: {GEMINI_MODEL}")
    print(f"Задержка между отправками: {DISPATCH_DELAY_SECONDS} сек.")
    print("=" * 65)

    all_leads = load_leads_from_csv(CSV_FILE_PATH)
    pending_leads = [l for l in all_leads if l.get("status", "").strip().lower() != "sent"]

    # Автопополнение, если неотправленных лидов не осталось
    if not pending_leads and AUTO_REPLENISH_LEADS:
        print("[INFO] В базе leads.csv нет неотправленных лидов. Запуск автопополнения...")
        replenish_leads_from_finder(CSV_FILE_PATH, count=3)
        all_leads = load_leads_from_csv(CSV_FILE_PATH)
        pending_leads = [l for l in all_leads if l.get("status", "").strip().lower() != "sent"]

    if not pending_leads:
        print("[INFO] Очередь отправки пуста. Все контакты из leads.csv уже обработаны.")
        print("Для добавления новых лидов запустите: python lead_finder.py --niche \"Ваша ниша\"")
        return

    print(f"[QUEUE] Найдено {len(pending_leads)} лидов со статусом 'pending' (не отправлено).")

    for index, lead in enumerate(pending_leads, 1):
        company = lead.get("name", "Компания")
        niche = lead.get("niche", "Сфера услуг")
        site = lead.get("site", "официальный сайт")
        email = lead.get("contact_email", "").strip()

        print(f"\n[{index}/{len(pending_leads)}] Обработка: {company} | Ниша: {niche}")
        print(f"[TARGET] Адрес получателя: {email}")

        if not email or "@" not in email:
            print("[SKIP] Некорректный email. Пропуск записи.")
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
            update_lead_status(CSV_FILE_PATH, email, new_status="sent", sent_at=now_str)
            print(f"[UPDATED] Запись {email} помечена как 'sent' в {CSV_FILE_PATH}.")
        else:
            update_lead_status(CSV_FILE_PATH, email, new_status="failed")
            print(f"[WARN] Запись {email} помечена как 'failed' в {CSV_FILE_PATH}.")

        if index < len(pending_leads):
            print(f"[PAUSE] Ожидание {DISPATCH_DELAY_SECONDS} сек. для защиты от спам-фильтров...")
            time.sleep(DISPATCH_DELAY_SECONDS)

    print("\n" + "=" * 65)
    print("[COMPLETED] Вся очередь неотправленных лидов успешно обработана.")
    print(f"Актуальное состояние базы зафиксировано в {CSV_FILE_PATH}")
    print("=" * 65)

if __name__ == "__main__":
    main()
