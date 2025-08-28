# horoscope_api.py
import aiohttp
import random
from datetime import datetime
import urllib.parse
import hashlib
import re
import json

# Импортируем необходимые функции из других модулей
# Убедитесь, что эти файлы существуют и доступны
try:
    from config import HOROSCOPE_SOURCES, ASTRO_API_BASE
    from zodiac import get_zodiac_sign, ZODIAC_API_MAP # <-- ВАЖНО: Импортируем get_zodiac_sign
except ImportError as e:
    print(f"Предупреждение: Не удалось импортировать модули: {e}")
    HOROSCOPE_SOURCES = {}
    ASTRO_API_BASE = "https://aztro.sameerkumar.website"
    get_zodiac_sign = lambda d, m: "Неизвестно"
    ZODIAC_API_MAP = {"Овен": "aries"}

# --- Словари для улучшенного гороскопа ---
# PLANET_INFLUENCES_DETAILED удален по запросу

MOON_PHASE_DESCRIPTIONS = {
    "Новолуние": "🌑 Новолуние - время новых начинаний, внутренней работы и постановки целей. Энергия внутренняя, заряжайтесь идеями.",
    "Молодая луна": "🌒 Молодая луна - фаза роста и первых шагов. Начинайте воплощать идеи в жизнь, энергия набирает силу.",
    "Первая четверть": "🌓 Первая четверть - время действий и преодоления первых препятствий. Требуется настойчивость.",
    "Прибывающая луна": "🌔 Прибывающая луна - продолжайте работу, энергия сильна. Подходит для развития и доработки проектов.",
    "Полнолуние": "🌕 Полнолуние - пик энергии и эмоций. Видны результаты, но возможны перегрузы. Хорошее время для завершения.",
    "Убывающая луна": "🌖 Убывающая луна - фаза спада. Начинайте отпускать, завершать дела, уменьшайте активность.",
    "Последняя четверть": "🌗 Последняя четверть - время очищения и подготовки. Может быть напряжённой, но необходимой для обновления.",
    "Старая луна": "🌘 Старая луна - глубокий отдых и внутренний анализ перед новым циклом. Подходит для медитации и планирования."
}

# Словарь природных камней для знаков зодиака
ZODIAC_STONES = {
    "Овен": "Яшма",
    "Телец": "Сердолик",
    "Близнецы": "Агат",
    "Рак": "Изумруд",
    "Лев": "Оникс",
    "Дева": "Сапфир",
    "Весы": "Опал",
    "Скорпион": "Топаз",
    "Стрелец": "Аметист",
    "Козерог": "Гранат",
    "Водолей": "Гелиодор (золотистый берилл)",
    "Рыбы": "Аквамарин"
}

# URL для гороскопов на сегодня на rambler.ru
ZODIAC_RAMBLER_URLS = {
    "Овен": "https://horoscopes.rambler.ru/aries/today/",
    "Телец": "https://horoscopes.rambler.ru/taurus/today/",
    "Близнецы": "https://horoscopes.rambler.ru/gemini/today/",
    "Рак": "https://horoscopes.rambler.ru/cancer/today/",
    "Лев": "https://horoscopes.rambler.ru/leo/today/",
    "Дева": "https://horoscopes.rambler.ru/virgo/today/",
    "Весы": "https://horoscopes.rambler.ru/libra/today/",
    "Скорпион": "https://horoscopes.rambler.ru/scorpio/today/",
    "Стрелец": "https://horoscopes.rambler.ru/sagittarius/today/",
    "Козерог": "https://horoscopes.rambler.ru/capricorn/today/",
    "Водолей": "https://horoscopes.rambler.ru/aquarius/today/",
    "Рыбы": "https://horoscopes.rambler.ru/pisces/today/",
}

# Кэш для хранения прогнозов на день
horoscope_cache = {}
# --- Конец словарей для улучшенного гороскопа ---

# --- ОСНОВНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ГОРОСКОПА ---
async def get_daily_horoscope(sign: str, birth_day: int = None, birth_month: int = None) -> dict:
    """
    Получение детального ежедневного гороскопа с реальными астрологическими данными.
    Args:
        sign (str): Знак зодиака пользователя.
        birth_day (int, optional): День рождения пользователя. Defaults to None.
        birth_month (int, optional): Месяц рождения пользователя. Defaults to None.
    """
    # Создаем уникальный ключ для кэширования с учетом времени
    cache_key = f"{sign}_{datetime.now().strftime('%Y-%m-%d_%H')}"
    # Проверяем кэш
    if cache_key in horoscope_cache:
        return horoscope_cache[cache_key]

    # 1. Получаем информацию о планетах и их положении (на основе даты рождения!)
    planetary_info = await get_planetary_positions(birth_day, birth_month)

    # 2. Получаем астрологический прогноз из API (новый сервис Rambler)
    astro_forecast = await get_astrological_forecast(sign)

    # 3. Генерируем подробный текст гороскопа (PLANET_INFLUENCES_DLAILED больше нет)
    enhanced_description = await generate_enhanced_forecast_text(sign, astro_forecast, planetary_info)

    # 4. Комбинируем все данные, помещая улучшенный текст в description
    result = {
        "sign": sign,
        "date": datetime.now().strftime("%d.%m.%Y"),
        "planetary_positions": planetary_info,
        "forecast": astro_forecast, # Оригинальные данные API
        # "planetary_influences": {}, # Удалено
        "description": enhanced_description, # Улучшенный текст
        "compatibility": astro_forecast.get('compatibility', ''),
        "mood": astro_forecast.get('mood', ''),
        "color": astro_forecast.get('color', ''),
        "lucky_number": astro_forecast.get('lucky_number', ''),
        "lucky_time": astro_forecast.get('lucky_time', '')
    }

    # Сохраняем в кэш
    horoscope_cache[cache_key] = result
    return result
# --- КОНЕЦ ОСНОВНОЙ ФУНКЦИИ ---

# --- ФУНКЦИИ ДЛЯ УЛУЧШЕННОГО ГОРОСКОПА ---
async def generate_enhanced_forecast_text(sign: str, forecast_data: dict, planetary_info: dict) -> str:
    """Генерация подробного и информативного текста гороскопа с проверками качества"""
    # --- Формирование подробного текста ---
    forecast_text = f"🔮 Гороскоп для {sign} на {datetime.now().strftime('%d.%m.%Y')}\n"

    # 1. Основной прогноз из API (оригинальный с привязкой к сервису)
    api_description = forecast_data.get('description', '').strip()
    # Всегда используем оригинальный прогноз, если он есть
    # API теперь должен возвращать текст на русском
    if api_description and len(api_description) > 10:
        # Проверяем, что текст на русском (на всякий случай)
        if re.search(r'[а-яА-Я]', api_description[:100]):
             forecast_text += f"✨ Астрологический прогноз для {sign}:\n{api_description}\n"
        else:
             # Если вдруг пришел не русский текст, пытаемся перевести
             print(f"Предупреждение: Получен не русский текст для {sign}, пробуем перевести.")
             translated_description = await translate_text(api_description)
             if translated_description and len(translated_description.strip()) > 10 and re.search(r'[а-яА-Я]', translated_description[:100]):
                 forecast_text += f"✨ Астрологический прогноз для {sign}:\n{translated_description.strip()}\n"
             else:
                 # Если перевод не удался, используем фолбэк
                 forecast_text += f"✨ Астрологический прогноз для {sign}:\n{api_description}\n"
    else:
        # Только если совсем нет данных, используем фолбэк
        fallback_forecasts = {
            "Овен": "Сегодня ваша энергия на пике! Используйте это для начала важных проектов. Будьте осторожны в личных отношениях - избегайте импульсивных решений.",
            "Телец": "Финансовые возможности представятся вам сегодня. Доверяйте своей интуиции в денежных вопросах. Обратите внимание на здоровье.",
            "Близнецы": "Отличный день для общения и обучения. Ваши идеи будут особенно востребованы. Избегайте многозадачности - сосредоточьтесь на главном.",
            "Рак": "Эмоциональная чувствительность усиливается сегодня. Прислушайтесь к своим внутренним голосам. Дом и семья требуют вашего внимания.",
            "Лев": "Ваша харизма на высоте! Используйте её для достижения целей. Не бойтесь проявлять лидерские качества, но учитывайте других.",
            "Дева": "Сегодня идеальный день для организации и планирования. Ваши аналитические способности помогут решить сложные задачи. Обратите внимание на детали.",
            "Весы": "Баланс и гармония - ваши ключевые слова сегодня. Ищите компромиссы в сложных ситуациях. Красота и искусство вдохновят вас.",
            "Скорпион": "Глубокие эмоции и интуиция будут вашими союзниками. Сегодня вы способны увидеть скрытые мотивы. Будьте осторожны с ревностью.",
            "Стрелец": "Приключения и новые знания ждут вас сегодня. Расширьте свои горизонты. Избегайте импульсивных финансовых решений.",
            "Козерог": "Ваша целеустремлённость и дисциплина принесут успехи. Сосредоточьтесь на долгосрочных целях. Не забывайте о личной жизни.",
            "Водолей": "Оригинальные идеи и нестандартное мышление - ваши сильные стороны сегодня. Работайте над групповыми проектами. Будьте открыты новому.",
            "Рыбы": "Ваша интуиция особенно остра сегодня. Доверяйте внутреннему голосу. Творческие проекты будут успешны. Избегайте чрезмерной эмоциональности."
        }
        forecast_text += f"✨ Астрологический прогноз для {sign}:\n{fallback_forecasts.get(sign, 'Сегодня звезды указывают на важные перемены в вашей жизни. Обратите внимание на интуитивные сигналы и не упускайте возможности, которые представятся вам сегодня.')}\n"

    # 2. Астрологические позиции
    # sun_sign = planetary_info.get('sun_sign', 'Неизвестно') # Убрано, так как теперь используем real_sun_sign
    moon_phase = planetary_info.get('moon_phase', 'Неизвестно')
    mercury_retrograde = planetary_info.get('mercury_retrograde', False)

    # Получаем реальные астрологические условия на сегодня
    real_sun_sign = await get_real_sun_sign()
    real_moon_phase = await get_real_moon_phase()
    real_mercury_retrograde = await check_real_mercury_retrograde()

    forecast_text += "🌌 Астрологические условия сегодня:\n"
    forecast_text += f"• ☀️ Солнце находится в знаке {real_sun_sign} (сегодня)\n"
    forecast_text += f"• {MOON_PHASE_DESCRIPTIONS.get(real_moon_phase, f'• 🌕 Луна в фазе {real_moon_phase}')}\n"
    if real_mercury_retrograde:
        forecast_text += "• ☿️ Меркурий находится в ретроградном движении! Будьте внимательны в коммуникациях, перепроверяйте важные документы и отложите запуск новых IT-проектов.\n"
    forecast_text += "\n"

    # 3. Влияние планет на знак - УБРАНО по запросу
    # (Удален блок кода, отвечающий за это)
    # if influences:  # influences - это словарь с влияниями планет, например, PLANET_INFLUENCES_DETAILED[sign]
    #     forecast_text += f"\n🪐 Влияние планет на {sign}:\n"
    #     # Предполагаем, что influences - это словарь с ключами планет
    #     # Обычно отображаются влияния Солнца, Луны, Меркурия, Венеры, Марса
    #     planet_symbols = {'sun': '☀️', 'moon': '🌙', 'mercury': '☿️', 'venus': '♀️', 'mars': '♂️'}
    #     
    #     for planet_key in ['sun', 'moon', 'mercury', 'venus', 'mars']: # Порядок важен
    #         desc = influences.get(planet_key)
    #         if desc:
    #             symbol = planet_symbols.get(planet_key, '')
    #             # Добавляем отступ перед каждой строкой влияния планеты
    #             forecast_text += f"{symbol} {desc}\n" 
    # forecast_text += "\n" # Пустая строка после влияния планет

    # 4. Практические рекомендации (только на основе реальных условий)
    recommendations = []
    if real_mercury_retrograde:
        recommendations.append("• Перепроверяйте всю важную информацию и договорённости.")
        recommendations.append("• Не подписывайте важные документы, если это не срочно.")
        recommendations.append("• Отложите крупные покупки электроники.")
    if "Полнолуние" in real_moon_phase:
        recommendations.append("• Эмоции могут быть напряжёнными, найдите способ расслабиться.")
        recommendations.append("• Хорошее время для завершения проектов.")
    elif "Новолуние" in real_moon_phase:
        recommendations.append("• Отличный день для планирования и постановки целей.")
        recommendations.append("• Сосредоточьтесь на внутренней работе.")

    # Получаем природный камень
    zodiac_stone = ZODIAC_STONES.get(sign, "Неизвестен")

    if recommendations:
        forecast_text += "💡 Рекомендации на день:\n"
        forecast_text += "\n".join(recommendations) + "\n"
        # Вместо счастливых чисел и времени, показываем камень
        forecast_text += f"\n🪨 Ваш природный камень: {zodiac_stone}\n"
    else:
        # Если нет специфических рекомендаций, выводим только камень
        forecast_text += f"🪨 Природный камень {sign}: {zodiac_stone}\n"

    return forecast_text.strip()
# --- КОНЕЦ ФУНКЦИЙ ДЛЯ УЛУЧШЕННОГО ГОРОСКОПА ---

# --- ФУНКЦИИ ДЛЯ ПОЛУЧЕНИЯ АСТРОЛОГИЧЕСКОЙ ИНФОРМАЦИИ ---
async def get_planetary_positions(birth_day: int = None, birth_month: int = None) -> dict:
    """
    Получение астрологических условий.
    Если переданы birth_day и birth_month, определяет знак Солнца для даты рождения.
    """
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        # ИСПРАВЛЕНО: Определяем знак Солнца для даты рождения, а не для сегодняшнего дня
        sun_sign = "Неизвестно"
        if birth_day is not None and birth_month is not None:
            sun_sign = get_zodiac_sign(birth_day, birth_month) # <-- Используем правильную функцию
        planetary_data = {
            "date": current_date,
            "sun_sign": sun_sign, # <-- Теперь корректный знак
            "moon_phase": await get_moon_phase(),
            "mercury_retrograde": await check_mercury_retrograde(),
        }
        return planetary_data
    except Exception as e:
        print(f"Ошибка при получении положений планет: {e}")
        return get_default_planetary_info()

async def get_real_sun_sign() -> str:
    """Получение реального знака Солнца на сегодня в режиме реального времени"""
    try:
        current_date = datetime.now()
        current_day = current_date.day
        current_month = current_date.month
        # Определяем реальный знак Солнца на сегодня
        real_sun_sign = get_zodiac_sign(current_day, current_month)
        return real_sun_sign
    except Exception as e:
        print(f"Ошибка при получении реального знака Солнца: {e}")
        return "Неизвестно"

async def get_real_moon_phase() -> str:
    """Получение реальной фазы Луны в режиме реального времени"""
    try:
        # Реальная фаза Луны зависит от дня месяца
        day_of_month = datetime.now().day
        phases = ["Новолуние", "Молодая луна", "Первая четверть", "Прибывающая луна",
                 "Полнолуние", "Убывающая луна", "Последняя четверть", "Старая луна"]
        # Более точное определение фазы (примерное)
        if day_of_month <= 3:
            return "Новолуние"
        elif day_of_month <= 7:
            return "Молодая луна"
        elif day_of_month <= 10:
            return "Первая четверть"
        elif day_of_month <= 14:
            return "Прибывающая луна"
        elif day_of_month <= 17:
            return "Полнолуние"
        elif day_of_month <= 21:
            return "Убывающая луна"
        elif day_of_month <= 24:
            return "Последняя четверть"
        elif day_of_month <= 28:
            return "Старая луна"
        else:
            return "Новолуние"
    except Exception as e:
        print(f"Ошибка при получении реальной фазы Луны: {e}")
        return "Неизвестно"

async def check_real_mercury_retrograde() -> bool:
    """Проверка реального состояния Меркурия в ретроградном движении в режиме реального времени"""
    try:
        # Реальные периоды ретроградного движения Меркурия (приблизительные)
        current_date = datetime.now()
        current_month = current_date.month
        current_day = current_date.day
        # Примерные периоды ретрограда Меркурия в 2024 году (обновите при необходимости)
        mercury_retrograde_periods = [
            (1, 1, 1, 25),    # 1-25 января
            (5, 14, 6, 4),    # 14 мая - 4 июня
            (9, 6, 9, 26),    # 6-26 сентября
            (12, 30, 12, 31)  # 30-31 декабря (переходит в следующий год)
        ]
        # Проверяем текущую дату
        for start_month, start_day, end_month, end_day in mercury_retrograde_periods:
            if current_month == start_month and start_day <= current_day <= end_day:
                return True
            if current_month == end_month and current_day <= end_day:
                return True
        # Если это декабрь и после 30 числа, проверяем январь следующего года
        if current_month == 12 and current_day >= 30:
            return True
        return False
    except Exception as e:
        print(f"Ошибка при проверке реального состояния Меркурия: {e}")
        return False

async def get_moon_phase() -> str:
    """Получение фазы Луны"""
    try:
        day_of_month = datetime.now().day
        phases = ["Новолуние", "Молодая луна", "Первая четверть", "Прибывающая луна",
                 "Полнолуние", "Убывающая луна", "Последняя четверть", "Старая луна"]
        phase_index = (day_of_month - 1) // 4
        return phases[min(phase_index, len(phases) - 1)]
    except:
        return "Неизвестно"

async def check_mercury_retrograde() -> bool:
    """Проверка, находится ли Меркурий в ретроградном движении"""
    try:
        # Упрощенная проверка - Меркурий бывает в ретрограде примерно 3 раза в год
        today = datetime.now()
        retrograde_periods = [
            (1, 10, 2, 3),   # Январь-Февраль
            (5, 10, 6, 3),   # Май-Июнь
            (9, 10, 10, 3),  # Сентябрь-Октябрь
        ]
        for start_month, start_day, end_month, duration_weeks in retrograde_periods:
            if today.month == start_month and start_day <= today.day <= start_day + duration_weeks * 7:
                return True
            if today.month == end_month and today.day <= duration_weeks * 7:
                return True
        return False
    except:
        return False

def get_default_planetary_info() -> dict:
    """Получение информации по умолчанию"""
    return {
        "date": datetime.now().strftime("%d.%m.%Y"),
        "sun_sign": "Неизвестно",
        "moon_phase": "Неизвестно",
        "mercury_retrograde": False,
    }


# --- НОВАЯ/ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ГОРОСКОПА С RAMBLER ---
# horoscope_api.py (фрагмент обновленной функции)
# ... (все импорты и предыдущий код остаются без изменений) ...

# --- ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ГОРОСКОПА С RAMBLER ---
async def get_astrological_forecast(sign: str) -> dict:
    """
    Получение астрологического прогноза с rambler.ru.
    """
    try:
        # Получаем URL для конкретного знака
        horoscope_url = ZODIAC_RAMBLER_URLS.get(sign)

        if not horoscope_url:
            print(f"Не найден URL для знака зодиака: {sign}")
            return await get_alternative_forecast(sign) # Пробуем альтернативный источник сразу

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Добавляем заголовки, имитирующие браузер, чтобы избежать блокировок
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0"
            }

            async with session.get(horoscope_url, headers=headers) as response:
                if response.status == 200:
                    try:
                        html_content = await response.text()

                        # --- ОБНОВЛЕННОЕ ИЗВЛЕЧЕНИЕ ТЕКСТА ГОРОСКОПА ---
                        # Ищем контейнер с текстом гороскопа
                        # Пример обновленной структуры: <div class="article__text"><p>...</p><p>...</p></div>
                        # Или <div class="jLSeW"><p>...</p><p>...</p></div> (как в примере сниппета)
                        
                        # Пробуем сначала найти div с классом, содержащим "article__text"
                        pattern_main = r'<div[^>]*class="[^"]*article__text[^"]*"[^>]*>(.*?)</div>'
                        match_main = re.search(pattern_main, html_content, re.DOTALL | re.IGNORECASE)
                        
                        description_parts = []
                        inner_html_to_parse = ""

                        if match_main:
                            inner_html_to_parse = match_main.group(1)
                        else:
                            # Если не найден основной класс, пробуем альтернативный подход
                            # Ищем div, который содержит абзацы с гороскопом (менее точно, но может помочь)
                            # Пример: найти первый div, содержащий несколько <p> с содержимым
                            print("Основной паттерн 'article__text' не найден, пробуем альтернативный поиск...")
                            # Поиск всех div и проверка содержимого
                            divs = re.findall(r'<div[^>]*>(.*?)</div>', html_content, re.DOTALL | re.IGNORECASE)
                            for div_content in divs:
                                # Проверяем, содержит ли div несколько <p> с текстом
                                p_tags = re.findall(r'<p[^>]*>(.*?)</p>', div_content, re.DOTALL | re.IGNORECASE)
                                # Фильтруем непустые абзацы
                                non_empty_ps = [p for p in p_tags if p.strip() and not re.match(r'^\s*<[^>]+>\s*$', p)]
                                if len(non_empty_ps) >= 1: # Если найден хотя бы один непустой абзац
                                    # Более точная проверка: ищем div, который выглядит как текст гороскопа
                                    # (например, не содержит вложенных сложных структур в большом количестве)
                                    if div_content.count('<div') < 5 and div_content.count('<script') == 0:
                                         inner_html_to_parse = div_content
                                         print("Найден потенциальный контейнер для текста гороскопа (альтернативный метод).")
                                         break # Берем первый подходящий

                        # Если нашли HTML для парсинга
                        if inner_html_to_parse:
                            # Извлекаем все <p> теги
                            p_texts = re.findall(r'<p[^>]*>(.*?)</p>', inner_html_to_parse, re.DOTALL | re.IGNORECASE)
                            
                            for p_text in p_texts:
                                # Очищаем HTML теги из текста абзаца
                                clean_text = re.sub(r'<[^>]+>', '', p_text).strip()
                                # Декодируем HTML сущности (например, &mdash;, &nbsp;, &laquo;, &raquo;)
                                clean_text = re.sub(r'&mdash;', '—', clean_text)
                                clean_text = re.sub(r'&nbsp;', ' ', clean_text)
                                clean_text = re.sub(r'&laquo;', '"', clean_text)
                                clean_text = re.sub(r'&raquo;', '"', clean_text)
                                clean_text = re.sub(r'&quot;', '"', clean_text)
                                clean_text = re.sub(r'&amp;', '&', clean_text) # Важно делать последним
                                # Добавляем непустой текст
                                if clean_text:
                                    description_parts.append(clean_text)

                        description = ' '.join(description_parts).strip()

                        if description and len(description) > 20: # Проверка на минимальную длину
                            print(f"Гороскоп для {sign} успешно получен и обработан с rambler.ru")
                            # Rambler предоставляет гороскоп на русском, перевод не нужен
                            return {
                                "description": description,
                                "compatibility": "См. общий прогноз",
                                "mood": "См. общий прогноз",
                                "color": "См. общий прогноз",
                                "lucky_number": "См. общий прогноз",
                                "lucky_time": "См. общий прогноз",
                                "date_range": "Сегодня"
                            }
                        else:
                            print(f"Не удалось извлечь подходящий текст гороскопа из HTML для {sign}. Извлечено: '{description[:50]}...'")
                        
                        # --- КОНЕЦ ОБНОВЛЕННОГО ИЗВЛЕЧЕНИЯ ---

                        # Если извлечение не удалось
                        print(f"Не удалось найти или корректно извлечь текст гороскопа для {sign} с rambler.ru.")
                        # Пробуем альтернативный источник
                        return await get_alternative_forecast(sign)

                    except Exception as parse_error:
                        print(f"Ошибка парсинга HTML для {sign}: {parse_error}")
                        import traceback
                        traceback.print_exc() # Для отладки
                        # Пробуем альтернативный источник
                        return await get_alternative_forecast(sign)
                else:
                    error_text = await response.text()
                    print(f"Rambler вернул статус {response.status} для знака {sign}. Заголовки: {response.headers}")
                    # Пробуем альтернативный источник
                    return await get_alternative_forecast(sign)

    except aiohttp.ClientError as client_error:
        print(f"Сетевая ошибка при запросе к Rambler для {sign}: {client_error}")
        # Пробуем альтернативный источник
        return await get_alternative_forecast(sign)
    except Exception as e:
        print(f"Неожиданная ошибка при получении астрологического прогноза для {sign} с Rambler: {e}")
        import traceback
        traceback.print_exc() # Для отладки
        # Пробуем альтернативный источник
        return await get_alternative_forecast(sign)

# ... (остальной код файла остается без изменений) ...


# --- ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ АЛЬТЕРНАТИВНОГО ИСТОЧНИКА (фолбэк на aztro) ---
async def get_alternative_forecast(sign: str) -> dict:
    """Получение прогноза из альтернативного источника (оригинальный aztro API с переводом)."""
    print(f"Попытка получить прогноз для {sign} из альтернативного источника (aztro)...")
    try:
        sign_api = ZODIAC_API_MAP.get(sign, "aries")
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        # Создаем уникальные параметры для предотвращения кэширования
        unique_param = hashlib.md5(f"{sign_api}_{current_date}_{current_time}".encode()).hexdigest()[:12]

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Предполагается, что ASTRO_API_BASE = "https://aztro.sameerkumar.website"
            url = f"{ASTRO_API_BASE}"
            params = {
                "sign": sign_api,
                "day": "today",
                "_": unique_param,
                "t": current_time
            }
            # Добавляем заголовки для лучшей идентификации
            headers = {
                "User-Agent": "AstroBot/1.0",
                "Cache-Control": "no-cache",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            async with session.post(url, params=params, headers=headers) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        description = data.get("description", "")
                        # Переводим при необходимости (оригинальная логика)
                        if description and not re.search(r'[а-яА-Я]', description[:100]):
                            translated_description = await translate_text(description)
                            if translated_description and len(translated_description.strip()) > 10:
                                if re.search(r'[а-яА-Я]', translated_description[:100]):
                                    description = translated_description.strip()
                                else:
                                    print(f"Предупреждение: Перевод для {sign} не содержит кириллицы")
                            else:
                                print(f"Предупреждение: Не удалось перевести текст для {sign}")
                        print(f"Прогноз для {sign} получен из альтернативного источника (aztro).")
                        return {
                            "description": description,
                            "compatibility": data.get("compatibility", ""),
                            "mood": data.get("mood", ""),
                            "color": data.get("color", ""),
                            "lucky_number": data.get("lucky_number", ""),
                            "lucky_time": data.get("lucky_time", ""),
                            "date_range": data.get("date_range", "")
                        }
                    except Exception as json_error:
                        print(f"Ошибка парсинга JSON из альтернативного источника (aztro) для {sign}: {json_error}")
                        return get_default_forecast(sign)
                else:
                    print(f"Альтернативный источник (aztro) вернул статус {response.status} для знака {sign}")
                    return get_default_forecast(sign)
    except Exception as e:
        print(f"Ошибка при получении астрологического прогноза для {sign} из альтернативного источника (aztro): {e}")
        return get_default_forecast(sign)

def get_default_forecast(sign: str) -> dict:
    """Получение прогноза по умолчанию"""
    moods = ["позитивный", "энергичный", "спокойный", "вдохновляющий"]
    colors = ["красный", "синий", "зеленый", "фиолетовый", "золотой"]
    return {
        "description": f"{sign}, сегодня планеты создают благоприятные условия для развития. Следуйте своей интуиции и не бойтесь принимать новые решения.",
        "compatibility": "Все знаки",
        "mood": random.choice(moods),
        "color": random.choice(colors),
        "lucky_number": str(random.randint(1, 100)),
        "lucky_time": f"{random.randint(9, 20)}:{random.choice(['00', '15', '30', '45'])}",
        "date_range": "Сегодня"
    }
# --- КОНЕЦ ФУНКЦИЙ ДЛЯ ПОЛУЧЕНИЯ АСТРОЛОГИЧЕСКОЙ ИНФОРМАЦИИ ---


# --- ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ССЫЛКИ НА НАТАЛЬНУЮ КАРТУ ---
async def get_natal_chart_info(birth_date: str, birth_time: str = None, birth_place: str = None) -> dict:
    """Получение информации о натальной карте и URL для кнопки"""
    parts = birth_date.split('.')
    if len(parts) != 3:
        return {"error": "Неверный формат даты"}
    day, month, year = parts
    natal_chart_url = generate_astro_seek_url(day, month, year, birth_time, birth_place)
    info_lines = []
    info_lines.append("📊 Натальная карта")
    info_lines.append(f"🎂 Дата рождения: {birth_date}")
    if birth_time and birth_time != '-':
        info_lines.append(f"⏰ Время рождения: {birth_time}")
    else:
        info_lines.append("⏰ Время рождения: 00:00 (по умолчанию)")
    if birth_place and birth_place != '-':
        info_lines.append(f"📍 Место рождения: {birth_place}")
    else:
        info_lines.append("📍 Место рождения: Краснодар (по умолчанию)")
    info_lines.append("") # Пустая строка перед советами
    info_lines.append("💡 Советы:")
    info_lines.append("• Для точного расчета укажите точное время рождения")
    info_lines.append("• Если не знаете время, используйте 12:00")
    info_lines.append("• Место рождения влияет на точность расчетов")
    info_lines.append("• ДЛЯ БОЛЕЕ ТОЧНОГО ПОНИМАНИЯ СВОЕГО ДАЛЬНЕЙШЕГО ПУТИ ОБРАТИТЕСЬ К НАШИМ СПЕЦИАЛИСТАМ @Eva_evgenivna99")
    return {
        "info_text": "\n".join(info_lines),
        "url": natal_chart_url
    }

def generate_astro_seek_url(day: str, month: str, year: str, birth_time: str = None, birth_place: str = None) -> str:
    """Генерация URL для astro-seek.com по образцу из запроса пользователя"""
    hour = "00"
    minute = "00"
    city_display_name = "Краснодар"
    city_url_name = "Краснодар"
    country_code = "RU"
    latitude_degrees = "45"
    latitude_minutes = "3"
    latitude_direction = "0"
    longitude_degrees = "38"
    longitude_minutes = "59"
    longitude_direction = "0"
    if birth_time and birth_time != '-':
        time_parts = birth_time.split(':')
        if len(time_parts) >= 2:
            try:
                hour = f"{int(time_parts[0]):02d}"
                minute = f"{int(time_parts[1]):02d}"
            except ValueError:
                print(f"Предупреждение: Неверный формат времени '{birth_time}'. Используются значения по умолчанию.")
    if birth_place and birth_place != '-':
        city_display_name = birth_place
        city_url_name = birth_place
    # --- ИСПРАВЛЕНИЕ: Убедитесь, что city_url_name и city_display_name не None ---
    if not city_url_name:
        city_url_name = "Krasnodar" # Английское название для URL
    if not city_display_name:
        city_display_name = "Краснодар"
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    encoded_city_url = urllib.parse.quote(city_url_name)
    encoded_city_hidden = urllib.parse.quote(city_display_name)
    # Исправлен base_url (убраны лишние пробелы в конце)
    base_url = "https://ru.astro-seek.com/vychislit-natalnaya-karta/"
    params = [
        "edit_input_data=1",
        "natal_input=1",
        "send_calculation=1",
        f"narozeni_den={int(day)}",
        f"narozeni_mesic={int(month)}",
        f"narozeni_rok={year}",
        f"narozeni_hodina={hour}",
        f"narozeni_minuta={minute}",
        f"narozeni_city={encoded_city_url}%2C+{country_code}",
        f"narozeni_mesto_hidden={encoded_city_hidden}",
        f"narozeni_stat_hidden={country_code}",
        "narozeni_podstat_kratky_hidden=",
        f"narozeni_sirka_stupne={latitude_degrees}",
        f"narozeni_sirka_minuty={latitude_minutes}",
        f"narozeni_sirka_smer={latitude_direction}",
        f"narozeni_delka_stupne={longitude_degrees}",
        f"narozeni_delka_minuty={longitude_minutes}",
        f"narozeni_delka_smer={longitude_direction}",
        "narozeni_timezone_form=auto",
        "narozeni_timezone_dst_form=auto",
        "house_system=placidus",
        "hid_fortune=1",
        "hid_fortune_check=on",
        "hid_chiron=1",
        "hid_chiron_check=on",
        "hid_lilith=1",
        "hid_lilith_check=on",
        "hid_uzel=1",
        "hid_uzel_check=on",
        "tolerance=1",
        "tolerance_paral=1.2"
    ]
    full_url = f"{base_url}?{'&'.join(params)}"
    return full_url
# --- КОНЕЦ ФУНКЦИЙ ДЛЯ ГЕНЕРАЦИИ ССЫЛКИ НА НАТАЛЬНУЮ КАРТУ ---

# Функция для очистки кэша (вызывать при необходимости)
def clear_horoscope_cache():
    """Очистка кэша гороскопов"""
    global horoscope_cache
    horoscope_cache.clear()
    print("Кэш гороскопов очищен")

# Функция для получения прогноза с принудительным обновлением (без кэша)
async def get_fresh_horoscope(sign: str, birth_day: int = None, birth_month: int = None) -> dict:
    """Получение свежего гороскопа без использования кэша"""
    # Временно очищаем кэш для этого знака
    cache_key = f"{sign}_{datetime.now().strftime('%Y-%m-%d_%H')}"
    if cache_key in horoscope_cache:
        del horoscope_cache[cache_key]
    # Получаем новый прогноз
    return await get_daily_horoscope(sign, birth_day, birth_month)

# --- ФУНКЦИИ ПЕРЕВОДА ТЕКСТА ---
# (Функции перевода оставлены без изменений, так как могут потребоваться как фолбэк)
async def translate_text(text: str) -> str:
    """Перевод текста с помощью различных онлайн-переводчиков"""
    if not text or len(text.strip()) < 2:
        return text
    # Проверяем, если текст уже на целевом языке (проверяем первые 100 символов)
    if re.search(r'[а-яА-Я]', text[:100]):
        return text
    # Пробуем различные методы перевода
    methods = [
        translate_with_google_api,
        translate_with_yandex_api,
        translate_with_mymemory_api,
        translate_with_libretranslate_api
    ]
    for method in methods:
        try:
            translated = await method(text)
            if translated and len(translated.strip()) > 5:
                # Проверяем, содержит ли перевод русские буквы
                if re.search(r'[а-яА-Я]', translated[:100]):
                    return translated.strip()
                else:
                    print(f"Предупреждение: {method.__name__} вернул текст без кириллицы")
        except Exception as e:
            print(f"Ошибка перевода через {method.__name__}: {e}")
            continue
    # Если все методы не сработали, возвращаем оригинальный текст
    print(f"Предупреждение: Не удалось перевести текст, возвращаем оригинальный")
    return text

async def translate_with_google_api(text: str) -> str:
    """Перевод через Google Translate API"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Используем бесплатный Google Translate API
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en",
                "tl": "ru",
                "dt": "t",
                "q": text
            }
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0 and data[0]:
                        translated_text = ""
                        for item in data[0]:
                            if item and len(item) > 0 and item[0]:
                                translated_text += item[0]
                        if translated_text and len(translated_text.strip()) > 5:
                            return translated_text.strip()
    except Exception as e:
        print(f"Ошибка Google Translate: {e}")
    return ""

async def translate_with_yandex_api(text: str) -> str:
    """Перевод через Yandex Translate API"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Используем Yandex Translate через прокси
            url = "https://translate.yandex.net/api/v1/tr.json/translate"
            params = {
                "lang": "en-ru",
                "text": text,
                "srv": "tr-text",
                "id": f"{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12]}-0-0"
            }
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "text" in data and data["text"]:
                        translated_text = data["text"][0]
                        if len(translated_text.strip()) > 5:
                            return translated_text.strip()
    except Exception as e:
        print(f"Ошибка Yandex Translate: {e}")
    return ""

async def translate_with_mymemory_api(text: str) -> str:
    """Перевод через MyMemory API"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q": text,
                "langpair": "en|ru"
            }
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "responseData" in data and "translatedText" in data["responseData"]:
                        translated_text = data["responseData"]["translatedText"]
                        if len(translated_text.strip()) > 5:
                            return translated_text.strip()
    except Exception as e:
        print(f"Ошибка MyMemory Translate: {e}")
    return ""

async def translate_with_libretranslate_api(text: str) -> str:
    """Перевод через LibreTranslate API"""
    try:
        # Пробуем различные публичные LibreTranslate серверы
        servers = [
            "https://libretranslate.de/translate",
            "https://translate.argosopentech.com/translate",
            "https://libretranslate.pussthecat.org/translate"
        ]
        for server in servers:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    payload = {
                        "q": text,
                        "source": "en",
                        "target": "ru",
                        "format": "text"
                    }
                    async with session.post(server, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "translatedText" in data:
                                translated_text = data["translatedText"]
                                if len(translated_text.strip()) > 5:
                                    return translated_text.strip()
            except Exception as e:
                print(f"Ошибка LibreTranslate ({server}): {e}")
                continue
    except Exception as e:
        print(f"Ошибка LibreTranslate: {e}")
    return ""

def detect_language(text: str) -> str:
    """
    Определение языка текста
    Args:
        text (str): Текст для определения языка
    Returns:
        str: Код языка ("ru", "en" или "unknown")
    """
    if not text or len(text.strip()) < 2:
        return "unknown"
    # Подсчитываем количество русских и английских букв
    russian_chars = len(re.findall(r'[а-яА-Я]', text[:100]))
    english_chars = len(re.findall(r'[a-zA-Z]', text[:100]))
    if russian_chars > english_chars and russian_chars > 5:
        return "ru"
    elif english_chars > russian_chars and english_chars > 5:
        return "en"
    else:
        return "unknown"
# --- КОНЕЦ ФУНКЦИЙ ПЕРЕВОДА ТЕКСТА ---

# --- ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ---
async def translate_horoscope_text(english_text: str) -> str:
    """
    Специализированная функция для перевода астрологических текстов
    Args:
        english_text (str): Астрологический текст на английском языке
    Returns:
        str: Переведенный текст на русский язык
    """
    if not english_text or len(english_text.strip()) < 5:
        return english_text
    # Проверяем, если текст уже на русском
    if re.search(r'[а-яА-Я]', english_text[:100]):
        return english_text
    # Используем универсальную функцию перевода
    translated = await translate_text(english_text)
    return translated if translated else english_text

# Функция для тестирования перевода
async def test_translation(text: str) -> str:
    """
    Тестовая функция для проверки работы перевода
    Args:
        text (str): Текст для перевода
    Returns:
        str: Переведенный текст
    """
    print(f"Оригинал: {text}")
    translated = await translate_text(text)
    print(f"Перевод: {translated}")
    return translated
# --- КОНЕЦ ДОПОЛНИТЕЛЬНЫХ ФУНКЦИЙ ---

# --- ФУНКЦИИ ПРОВЕРКИ КАЧЕСТВА ПЕРЕВОДА ---
async def is_good_translation(text: str) -> bool:
    """Проверка качества перевода"""
    if not text or len(text.strip()) < 10:
        return False
    # Проверяем наличие русских букв
    if not re.search(r'[а-яА-Я]', text[:100]):
        return False
    # Проверяем на бессмысленные строки
    meaningless_patterns = [
        r'^[^\w\s]+$',  # Только знаки препинания
        r'^\s*$',       # Только пробелы
        r'^[0-9\s]+$',  # Только цифры и пробелы
    ]
    for pattern in meaningless_patterns:
        if re.match(pattern, text):
            return False
    # Проверяем длину осмысленного текста
    if len(text.strip()) < 20:
        return False
    # Проверяем на повторяющиеся символы
    if re.search(r'(.)\1{10,}', text):  # Повтор одного символа более 10 раз
        return False
    return True
# --- КОНЕЦ ФУНКЦИЙ ПРОВЕРКИ КАЧЕСТВА ПЕРЕВОДА ---
