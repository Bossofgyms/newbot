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
PLANET_INFLUENCES_DETAILED = {
    "Овен": {
        "sun": "☀️ Солнце в вашем знаке придаёт вам мощный заряд энергии, уверенности и харизмы. Это отличное время для начала новых проектов и проявления лидерских качеств.",
        "moon": "🌙 Луна усиливает вашу эмоциональную интуицию и импульсивность. Прислушайтесь к своим чувствам, они будут особенно ясны.",
        "mercury": "☿️ Меркурий делает ваш ум острым и коммуникацию прямолинейной. Отличный день для важных разговоров, но следите за тоном.",
        "venus": "♀️ Венера добавляет страсти в любовь и эстетическое восприятие. Вы чувствуете себя особенно привлекательно.",
        "mars": "♂️ Марс усиливает вашу боевую энергию и решимость. Идеальное время для решительных действий, но избегайте конфликтов ради конфликтов."
    },
    "Телец": {
        "sun": "☀️ Солнце в вашем знаке укрепляет вашу внутреннюю стабильность и уверенность в себе. Вы чувствуете связь с собственной ценностью.",
        "moon": "🌙 Луна делает ваши эмоции глубокими и стойкими. Вам нужно больше времени, чтобы обработать чувства, но они искренни.",
        "mercury": "☿️ Меркурий благоприятствует практическому мышлению и точной оценке. Хороший день для финансовых обсуждений.",
        "venus": "♀️ Венера в вашем знаке - это пик чувственности и любви к красоте. Наслаждайтесь удовольствиями жизни.",
        "mars": "♂️ Марс придаёт вам упорство и настойчивость. Когда вы что-то затеете, доведёте до конца, пусть даже медленно."
    },
    "Близнецы": {
        "sun": "☀️ Солнце активизирует ваш ум и коммуникабельность. Вы чувствуете себя вдохновлённым для обмена идеями и социальных взаимодействий.",
        "moon": "🌙 Луна делает ваше эмоциональное состояние переменчивым, но также делает интуицию острой. Обратите внимание на всплывающие мысли.",
        "mercury": "☿️ Меркурий в своём знаке - ваш дом! Интеллект на максимуме, идеальное время для учёбы, письма и разговоров.",
        "venus": "♀️ Венера делает вас обаятельным и любознательным в отношениях. Вам нужны разнообразные и увлекательные связи.",
        "mars": "♂️ Марс придаёт вам гибкость в действии. Вы быстро переключаетесь между задачами, но иногда нужна фокусировка."
    },
    "Рак": {
        "sun": "☀️ Солнце в вашем знаке делает вашу личность глубокой и эмоционально насыщенной. Вы чувствуете сильную связь с домом и семьёй.",
        "moon": "🌙 Луна в своём знаке усиливает вашу эмпатию и интуицию до предела. Вы чувствуете настроение окружающих почти физически.",
        "mercury": "☿️ Меркурий делает ваше мышление более интуитивным и чувствительным. Слова могут задеть глубже обычного.",
        "venus": "♀️ Венера усиливает потребность в уюте и романтике. Вы стремитесь к глубокой эмоциональной связи.",
        "mars": "♂️ Марс делает вашу защиту сильной. Вы будете отстаивать своих близких с большой решимостью."
    },
    "Лев": {
         "sun": "☀️ Солнце в вашем знаке - это как лучи света на вашем сердце! Вы чувствуете себя уверенно, творчески и готовы сиять. Это ваше время быть в центре внимания.",
         "moon": "🌙 Луна усиливает вашу эмоциональную щедрость и потребность в признании. Ваши чувства ярки и открыты.",
         "mercury": "☿️ Меркурий подчёркивает вашу харизматичную речь и любовь к драматизму. Отличный день для самовыражения и убеждения.",
         "venus": "♀️ Венера делает вас особенно привлекательным и романтичным. Ищите признания и красоты во всём.",
         "mars": "♂️ Марс придаёт вам горделивую решимость. Вы готовы защищать свою честь и добиваться победы."
    },
    "Дева": {
         "sun": "☀️ Солнце в вашем знаке делает ваш ум особенно аналитическим и стремление к совершенству - вашим двигателем. Это хороший день для организации и детального планирования.",
         "moon": "🌙 Луна делает ваши эмоции более сдержанными, но внимательными к деталям. Вы можете беспокоиться, но это стимул к действию.",
         "mercury": "☿️ Меркурий в вашем знаке - это суперсила! Мозг работает на полную мощность, идеальное время для учёбы, анализа и решения сложных задач.",
         "venus": "♀️ Венера придаёт чувство эстетики и любви к порядку. Вы цените простые, но качественные удовольствия.",
         "mars": "♂️ Марс делает вас эффективным и трудолюбивым. Вы способны много работать и доводить дела до совершенства."
    },
    "Весы": {
         "sun": "☀️ Солнце в вашем знаке делает вашу личность обаятельной и стремящейся к гармонии. Вы чувствуете себя уверенно в социальных ситуациях и стремитесь к балансу.",
         "moon": "🌙 Луна усиливает вашу эмпатию и потребность в эмоциональной гармонии. Вы чувствительны к настроению окружающих.",
         "mercury": "☿️ Меркурий делает вас отличным дипломатом и коммуникатором. Вы умеете находить компромиссы и красиво выражать мысли.",
         "venus": "♀️ Венера в своём знаке правит! Вы чувствуете себя особенно привлекательно, любите красоту и гармонию во всём.",
         "mars": "♂️ Марс может вызывать колебания, но также придаёт вам решимость в защите справедливости и эстетических ценностей."
    },
    "Скорпион": {
         "sun": "☀️ Солнце в вашем знаке делает вашу личность магнетической и интенсивной. Вы чувствуете глубокую связь со своими эмоциями и интуицией.",
         "moon": "🌙 Луна усиливает вашу эмоциональную глубину и способность к трансформации. Ваши чувства сильны и подлинны.",
         "mercury": "☿️ Меркурий делает ваш ум проницательным и склонным к анализу. Вы видите скрытые мотивы и смыслы.",
         "venus": "♀️ Венера придаёт страсть и глубину в любви и чувственности. Ваши привязанности сильны и преданы.",
         "mars": "♂️ Марс усиливает вашу волю и решимость. Вы способны на многое ради достижения цели, проявляя огромную внутреннюю силу."
    },
    "Стрелец": {
         "sun": "☀️ Солнце в вашем знаке наполняет вас оптимизмом и жаждой приключений. Вы чувствуете себя свободно и вдохновлённо.",
         "moon": "🌙 Луна делает ваши эмоции свободными и прямыми. Вы быстро переживаете чувства и смотрите вперёд.",
         "mercury": "☿️ Меркурий делает ваш ум любознательным и философским. Отличный день для обучения и обмена идеями.",
         "venus": "♀️ Венера придаёт чувство романтики и любви к красоте, связанной с путешествиями и культурой.",
         "mars": "♂️ Марс делает вас предприимчивым и решительным. Вы готовы к новым начинаниям и преодолению препятствий."
    },
    "Козерог": {
         "sun": "☀️ Солнце в вашем знаке делает вашу личность амбициозной и целеустремлённой. Вы чувствуете силу и ответственность.",
         "moon": "🌙 Луна делает ваши эмоции сдержанными, но глубокими. Ваши чувства связаны с чувством долга и заботой о будущем.",
         "mercury": "☿️ Меркурий делает ваше мышление практичным и дисциплинированным. Вы цените точность и долгосрочную перспективу.",
         "venus": "♀️ Венера придаёт чувство ценности в традициях, стабильности и долгосрочных отношениях.",
         "mars": "♂️ Марс усиливает вашу настойчивость и терпение. Вы способны долго и упорно работать ради достижения долгосрочных целей."
    },
    "Водолей": {
         "sun": "☀️ Солнце в вашем знаке делает вашу личность оригинальной и независимой. Вы чувствуете вдохновение от нестандартных идей.",
         "moon": "🌙 Луна делает ваши эмоции неожиданными и ориентированными на коллектив. Вы чувствуете связь с будущим и гуманитарными идеалами.",
         "mercury": "☿️ Меркурий делает ваш ум инновационным и склонным к абстрактному мышлению. Отличный день для изучения новых технологий и идей.",
         "venus": "♀️ Венера придаёт чувство любви к свободе и нестандартной красоте. Вы цените уникальность в отношениях.",
         "mars": "♂️ Марс делает вас решительным в отстаивании своих убеждений и реформ. Вы боретесь за прогресс и перемены."
    },
    "Рыбы": {
         "sun": "☀️ Солнце в вашем знаке делает вашу личность чувствительной и интуитивной. Вы чувствуете глубокую связь с эмоциями и искусством.",
         "moon": "🌙 Луна усиливает вашу эмпатию до предела. Вы чувствуете эмоции окружающих, как свои собственные.",
         "mercury": "☿️ Меркурий делает ваш ум интуитивным и воображаемым. Вы воспринимаете информацию через образы и чувства.",
         "venus": "♀️ Венера усиливает вашу чувственность, сострадание и любовь к искусству. Вы ищете духовную и эмоциональную красоту.",
         "mars": "♂️ Марс делает вашу энергию текучей и подчинённой вашим идеалам. Вы действуете интуитивно и с состраданием."
    },
}
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
    # 2. Получаем астрологический прогноз из API
    astro_forecast = await get_astrological_forecast(sign)
    # 3. Получаем влияние планет на знак (более детальное)
    planetary_influences = PLANET_INFLUENCES_DETAILED.get(sign, {})
    # 4. Генерируем подробный текст гороскопа
    enhanced_description = await generate_enhanced_forecast_text(sign, astro_forecast, planetary_info, planetary_influences)
    # 5. Комбинируем все данные, помещая улучшенный текст в description
    result = {
        "sign": sign,
        "date": datetime.now().strftime("%d.%m.%Y"),
        "planetary_positions": planetary_info,
        "forecast": astro_forecast, # Оригинальные данные API
        "planetary_influences": planetary_influences,
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
async def generate_enhanced_forecast_text(sign: str, forecast_data: dict, planetary_info: dict, influences: dict) -> str:
    """Генерация подробного и информативного текста гороскопа с проверками качества и автоматическим переводом"""
    # --- Формирование подробного текста ---
    forecast_text = f"🔮 Гороскоп для {sign} на {datetime.now().strftime('%d.%m.%Y')}\n"
    
    # 1. Основной прогноз из API (оригинальный с привязкой к сервису)
    api_description = forecast_data.get('description', '').strip()
    
    # Всегда используем оригинальный прогноз, если он есть, с переводом при необходимости
    if api_description and len(api_description) > 10:
        # Проверяем, нужен ли перевод (проверяем первые 100 символов на наличие кириллицы)
        if not re.search(r'[а-яА-Я]', api_description[:100]):
            # Английский текст, переводим
            translated_description = await translate_text(api_description)
            # Проверяем качество перевода
            if translated_description and len(translated_description.strip()) > 10:
                # Дополнительная проверка: убедимся, что перевод содержит русские буквы
                if re.search(r'[а-яА-Я]', translated_description[:100]):
                    api_description = translated_description.strip()
                else:
                    print(f"Предупреждение: Перевод для {sign} не содержит кириллицы, используем оригинальный текст")
            else:
                print(f"Предупреждение: Не удалось перевести текст для {sign}, используем оригинальный текст")
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
    sun_sign = planetary_info.get('sun_sign', 'Неизвестно')
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
        # Примерные периоды ретрограда Меркурия в 2024 году
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

async def get_astrological_forecast(sign: str) -> dict:
    """Получение астрологического прогноза в реальном времени с уникальной привязкой к дате"""
    try:
        sign_api = ZODIAC_API_MAP.get(sign, "aries")
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        # Создаем уникальные параметры для предотвращения кэширования
        unique_param = hashlib.md5(f"{sign_api}_{current_date}_{current_time}".encode()).hexdigest()[:12]
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{ASTRO_API_BASE}" # Предполагается, что это "https://aztro.sameerkumar.website"
            params = {
                "sign": sign_api, 
                "day": "today",
                "_": unique_param,  # Уникальный параметр для предотвращения кэширования
                "t": current_time   # Дополнительный параметр времени
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
                        # Принимаем любой прогноз как есть, с переводом при необходимости
                        if description and not re.search(r'[а-яА-Я]', description[:100]):
                            translated_description = await translate_text(description)
                            # Проверяем качество перевода
                            if translated_description and len(translated_description.strip()) > 10:
                                # Дополнительная проверка: убедимся, что перевод содержит русские буквы
                                if re.search(r'[а-яА-Я]', translated_description[:100]):
                                    description = translated_description.strip()
                                else:
                                    print(f"Предупреждение: Перевод для {sign} не содержит кириллицы")
                            else:
                                print(f"Предупреждение: Не удалось перевести текст для {sign}")
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
                        print(f"Ошибка парсинга JSON для {sign}: {json_error}")
                        # Пробуем получить текст
                        text = await response.text()
                        if text:
                            try:
                                # Попытка парсинга текста как JSON
                                import json as json_lib
                                data = json_lib.loads(text)
                                description = data.get("description", "")
                                # Переводим при необходимости
                                if description and not re.search(r'[а-яА-Я]', description[:100]):
                                    translated_description = await translate_text(description)
                                    if translated_description and len(translated_description.strip()) > 10:
                                        # Дополнительная проверка: убедимся, что перевод содержит русские буквы
                                        if re.search(r'[а-яА-Я]', translated_description[:100]):
                                            description = translated_description.strip()
                                        else:
                                            print(f"Предупреждение: Перевод для {sign} не содержит кириллицы")
                                    else:
                                        print(f"Предупреждение: Не удалось перевести текст для {sign}")
                                return {
                                    "description": description,
                                    "compatibility": data.get("compatibility", ""),
                                    "mood": data.get("mood", ""),
                                    "color": data.get("color", ""),
                                    "lucky_number": data.get("lucky_number", ""),
                                    "lucky_time": data.get("lucky_time", ""),
                                    "date_range": data.get("date_range", "")
                                }
                            except:
                                # Возвращаем текст как есть, с переводом при необходимости
                                clean_text = text.strip()
                                if len(clean_text) > 10:
                                    if not re.search(r'[а-яА-Я]', clean_text[:100]):
                                        clean_text = await translate_text(clean_text)
                                        # Проверяем качество перевода
                                        if clean_text and len(clean_text.strip()) > 10:
                                            # Дополнительная проверка: убедимся, что перевод содержит русские буквы
                                            if re.search(r'[а-яА-Я]', clean_text[:100]):
                                                clean_text = clean_text.strip()
                                            else:
                                                print(f"Предупреждение: Перевод для {sign} не содержит кириллицы, используем оригинальный текст")
                                        else:
                                            print(f"Предупреждение: Не удалось перевести текст для {sign}, используем оригинальный текст")
                                    return {
                                        "description": clean_text,
                                        "compatibility": "Все знаки",
                                        "mood": "позитивный",
                                        "color": "разноцветный",
                                        "lucky_number": "7",
                                        "lucky_time": f"{random.randint(9, 20)}:{random.choice(['00', '15', '30', '45'])}",
                                        "date_range": "Сегодня"
                                    }
                                else:
                                    return get_default_forecast(sign)
                        return get_default_forecast(sign)
                else:
                    print(f"API вернул статус {response.status} для знака {sign}")
                    # Пробуем альтернативный источник
                    alt_forecast = await get_alternative_forecast(sign)
                    if alt_forecast and alt_forecast.get("description") and len(alt_forecast["description"]) > 10:
                        return alt_forecast
                    return get_default_forecast(sign)
    except Exception as e:
        print(f"Ошибка при получении астрологического прогноза для {sign}: {e}")
        # Пробуем альтернативный источник
        alt_forecast = await get_alternative_forecast(sign)
        if alt_forecast and alt_forecast.get("description") and len(alt_forecast["description"]) > 10:
            return alt_forecast
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

# --- ФУНКЦИИ ДЛЯ АЛЬТЕРНАТИВНЫХ ИСТОЧНИКОВ ---
async def get_alternative_forecast(sign: str) -> dict:
    """Получение прогноза из альтернативного источника"""
    try:
        sign_api = ZODIAC_API_MAP.get(sign, "aries").lower()
        timestamp = int(datetime.now().timestamp())
        # Пробуем разные источники
        urls = [
            f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={sign_api}&day=TODAY&_={timestamp}",
            f"https://horoscope-api-v2.vercel.app/api/horoscope/{sign_api}",
        ]
        for url in urls:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {
                        "User-Agent": "AstroBot/1.0",
                        "Accept": "application/json",
                        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
                    }
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                # Ищем текст прогноза в разных полях
                                horoscope_text = (
                                    data.get('data', {}).get('horoscope_data') or
                                    data.get('horoscope') or
                                    data.get('description') or
                                    data.get('prediction') or
                                    ""
                                )
                                if horoscope_text and len(horoscope_text) > 10:
                                    # Переводим при необходимости
                                    if not re.search(r'[а-яА-Я]', horoscope_text[:100]):
                                        translated_text = await translate_text(horoscope_text)
                                        if translated_text and len(translated_text.strip()) > 10:
                                            # Дополнительная проверка: убедимся, что перевод содержит русские буквы
                                            if re.search(r'[а-яА-Я]', translated_text[:100]):
                                                horoscope_text = translated_text.strip()
                                            else:
                                                print(f"Предупреждение: Перевод для {sign} не содержит кириллицы")
                                        else:
                                            print(f"Предупреждение: Не удалось перевести текст для {sign}")
                                    return {
                                        "description": horoscope_text,
                                        "compatibility": data.get("compatibility", "") or "Все знаки",
                                        "mood": data.get("mood", "") or "позитивный",
                                        "color": data.get("color", "") or "разноцветный",
                                        "lucky_number": data.get("lucky_number", "") or "7",
                                        "lucky_time": data.get("lucky_time", "") or f"{random.randint(9, 20)}:{random.choice(['00', '15', '30', '45'])}",
                                        "date_range": data.get("date_range", "") or "Сегодня"
                                    }
                            except Exception as e:
                                print(f"Ошибка парсинга JSON из альтернативного источника для {sign}: {e}")
                                continue
            except Exception as e:
                print(f"Ошибка запроса к альтернативному источнику {url} для {sign}: {e}")
                continue
        return get_default_forecast(sign)
    except Exception as e:
        print(f"Ошибка при получении альтернативного прогноза для {sign}: {e}")
        return get_default_forecast(sign)

# --- КОНЕЦ ФУНКЦИЙ ДЛЯ АЛЬТЕРНАТИВНЫХ ИСТОЧНИКОВ ---

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