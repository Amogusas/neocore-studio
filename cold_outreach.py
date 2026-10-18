#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NEOCORE STUDIO // Automated B2B Cold Outreach Engine
Модуль автоматизированной генерации персонализированных коммерческих предложений через Google Gemini и отправки через SMTP.

Установка зависимостей:
    pip install google-genai
"""

import os
import sys
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Обеспечение корректного вывода кириллицы в Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==============================================================================
# КОНФИГУРАЦИЯ СЕРВИСОВ
# ==============================================================================

# 1. Ключ Google Gemini API (получите бесплатно: https://aistudio.google.com/)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
GEMINI_MODEL = "gemini-2.5-flash"  # Актуальная модель Flash-серии

# 2. SMTP-настройки почтового сервера (по умолчанию Gmail)
# Для Gmail создайте "Пароль приложения" (16 символов без пробелов):
# https://myaccount.google.com/apppasswords
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", "stupapupa228777@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "YOUR_APP_PASSWORD_HERE")

# 3. Данные студии NEOCORE
STUDIO_NAME = "NEOCORE Studio"
STUDIO_PORTFOLIO = "https://amogusas.github.io/neocore-studio/"
STUDIO_TELEGRAM = "https://t.me/neocore_studio"
STUDIO_EMAIL = "stupapupa228777@gmail.com"

# 4. Интервал задержки между отправками писем (в секундах)
DISPATCH_DELAY_SECONDS = 15

# ==============================================================================
# БАЗА ЛИДОВ (ЦЕЛЕВЫЕ КОМПАНИИ)
# ==============================================================================
LEADS_DATABASE = [
    {
        "name": "Apex Detailing Lab",
        "niche": "Премиальный детейлинг автомобилей и оклейка бронепленкой",
        "site": "apex-detailing-demo.ru",
        "contact_email": "stupapupa228777@gmail.com"  # Тестовая почта для проверки
    },
    {
        "name": "Nordic Renovation",
        "niche": "Дизайнерский ремонт квартир и загородных коттеджей",
        "site": "nordic-remont-sample.ru",
        "contact_email": "stupapupa228777@gmail.com"  # Тестовая почта для проверки
    },
    {
        "name": "Krono Watches",
        "niche": "Интернет-магазин оригинальных наручных часов",
        "site": "krono-store-demo.ru",
        "contact_email": "stupapupa228777@gmail.com"  # Тестовая почта для проверки
    }
]

# ==============================================================================
# ГЕНЕРАЦИЯ ОФФЕРА ЧЕРЕЗ GEMINI
# ==============================================================================
def generate_pitch(company_name: str, niche: str, current_site: str) -> str:
    """
    Генерирует короткое персонализированное письмо через Gemini API.
    При отсутствии API-ключа формирует адаптивный резервный шаблон.
    """
    prompt = f"""
Ты — технический архитектор и ведущий консультант студии цифровой разработки {STUDIO_NAME}.
Наше портфолио: {STUDIO_PORTFOLIO}
Наш Telegram: {STUDIO_TELEGRAM}

Составь короткое, строго персонализированное B2B-письмо руководителю компании.

Данные клиента:
- Компания: {company_name}
- Ниша: {niche}
- Сайт: {current_site}

Критерии качества:
1. Объем: строго 4-5 предложений. Максимальная плотность смысла, без клише и воды.
2. Никаких эмодзи (строго запрещено использовать эмодзи в тексте).
3. Проблема: укажи, что в нише "{niche}" типовые шаблонные сайты страдают долгой загрузкой, шаблонной баннерной слепотой и теряют мобильный трафик до оформления заявки.
4. Решение: предложи стек NEOCORE — 3D WebGL интерактив со скоростью 60 FPS, моментальный расчет сметы в калькуляторе и мгновенную доставку структурированных лидов в Telegram.
5. Призыв к действию: мягко предложить записать 30-секундное видео-демо с прототипом их нового экрана или показать концепт в живом эфире.
6. Подпись: {STUDIO_NAME} с ссылкой на портфолио ({STUDIO_PORTFOLIO}) и Telegram ({STUDIO_TELEGRAM}).
7. Верни ТОЛЬКО готовый текст письма.
"""

    # Попытка генерации через официальную библиотеку google-genai
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except ImportError:
            print("[INFO] Библиотека google-genai не найдена. Используется встроенный резервный генератор.")
        except Exception as e:
            print(f"[WARN] Ошибка обращения к Gemini API ({e}). Применен резервный шаблон.")

    # Высококонверсионный резервный шаблон (Fallback)
    fallback_pitch = (
        f"Здравствуйте, команда {company_name}.\n\n"
        f"Обратил внимание на ваш проект в сфере {niche}. Большинство сайтов в вашей отрасли "
        f"используют стандартные шаблонные блоки и долго грузятся на смартфонах, из-за чего теряется до 40% "
        f"входящего коммерческого трафика.\n\n"
        f"Мы в {STUDIO_NAME} проектируем решения нового поколения: интерактивный 3D WebGL (60 FPS без задержек), "
        f"динамический калькулятор сметы и прямую интеграцию приема заявок в Telegram.\n\n"
        f"Ознакомиться с нашими живыми кейсами можно в портфолио: {STUDIO_PORTFOLIO}\n\n"
        f"Готовы записать для вас короткий 30-секундный видеоразбор с идеями по усилению конверсии "
        f"вашего интерфейса. Подскажите, актуальна ли задача масштабирования заявок?\n\n"
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
    Отправляет сформированное письмо через SMTP.
    Если пароль не задан, отрабатывает режим симуляции (Dry Run).
    """
    if not SMTP_PASSWORD or SMTP_PASSWORD == "YOUR_APP_PASSWORD_HERE":
        print(f"[DRY-RUN] Пароль приложения SMTP не настроен. Письмо для <{to_email}> сформировано корректно, но реальная отправка пропущена.")
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
# ТОЧКА ВХОДА (ОСНОВНОЙ ЦИКЛ)
# ==============================================================================
def main():
    print("=" * 65)
    print(f"[{STUDIO_NAME}] Запуск модуля автоматического B2B-аутрича")
    print(f"Очередь обработки: {len(LEADS_DATABASE)} компаний")
    print(f"Задержка между отправками: {DISPATCH_DELAY_SECONDS} сек.")
    print("=" * 65)

    for index, lead in enumerate(LEADS_DATABASE, 1):
        company = lead["name"]
        niche = lead["niche"]
        site = lead["site"]
        email = lead["contact_email"]

        print(f"\n[{index}/{len(LEADS_DATABASE)}] Обработка: {company} | Ниша: {niche}")
        print("[INFO] Генерация персонализированного оффера через Gemini...")

        subject = f"{company} // Увеличение конверсии сайта и 3D-интерактив"
        pitch = generate_pitch(company, niche, site)

        print("\n--- СФОРМИРОВАННЫЙ ТЕКСТ ПИСЬМА ---")
        print(pitch)
        print("------------------------------------\n")

        print(f"[INFO] Передача письма в SMTP-шлюз ({email})...")
        send_email(email, subject, pitch)

        if index < len(LEADS_DATABASE):
            print(f"[PAUSE] Ожидание {DISPATCH_DELAY_SECONDS} сек. для предотвращения спам-фильтров...")
            time.sleep(DISPATCH_DELAY_SECONDS)

    print("\n" + "=" * 65)
    print("[COMPLETED] Вся очередь лидов успешно обработана.")
    print("=" * 65)

if __name__ == "__main__":
    main()
