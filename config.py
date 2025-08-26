# config.py



# Источники для гороскопов
HOROSCOPE_SOURCES = [
    "https://horoscope-app-api.vercel.app/api/v1/get-horoscope",
    "https://theastrologer-api.herokuapp.com/api/horoscope"
]

# API для получения астрологической информации
ASTRO_API_BASE = "https://aztro.sameerkumar.website"
ASTROLOGY_API = "https:// astrology-api.p.rapidapi.com/api/astrology"

# API для получения информации о планетах
PLANETS_API = "https://planets-api.vercel.app/api/planets"

# Время ежедневной рассылки (час в 24-часовом формате)
DAILY_TIME_HOUR = 9
DAILY_TIME_MINUTE = 00

# Работающие русскоязычные сервисы для натальной карты
NATAL_CHART_SERVICES = [
    "http://astro.map.ru/",
    "https://astroclub.ru/calculators/natal-chart.html",
    "https://ru.astro-seek.com/natalni-astrologicka-karta"
]
