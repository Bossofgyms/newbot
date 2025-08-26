import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, задан ли токен
if not BOT_TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не задана! Проверь файл .env")

# Импортируем модули проекта
from database import init_db, save_user, update_user_data, subscribe_user, unsubscribe_user, get_user_data
from zodiac import get_zodiac_sign
from horoscope_api import get_daily_horoscope, get_natal_chart_info
from scheduler import scheduler

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Создаём экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Определяем состояния для FSM
class UserData(StatesGroup):
    waiting_for_birth_date = State()
    waiting_for_birth_time = State()
    waiting_for_birth_place = State()

# Функция для создания основной клавиатуры с кнопками
def get_main_keyboard():
    """Создание основной клавиатуры с кнопками"""
    keyboard = [
        [types.KeyboardButton(text="🔮 Гороскоп")],
        [types.KeyboardButton(text="📊 Натальная карта")],
        [types.KeyboardButton(text="🔢 Число жизни")],
        [types.KeyboardButton(text="📨 Подписаться на гороскоп"), types.KeyboardButton(text="❌ Отписаться")],
        [types.KeyboardButton(text="👤 Мой профиль")],
        [types.KeyboardButton(text="❓ Помощь")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Функция для вычисления числа жизни (формулы души)
def calculate_soul_formula(birth_date_str: str) -> str:
    """
    Вычисляет Число жизни по дате рождения.
    Args:
        birth_date_str (str): Дата рождения в формате ДД.ММ.ГГГГ.
    Returns:
        str: Число жизни (однозначное число или мастер-число).
    """
    if not birth_date_str:
        return "Дата рождения не указана."

    try:
        # Разделяем дату и проверяем формат
        parts = birth_date_str.split('.')
        if len(parts) != 3:
            return "Неверный формат даты."

        day, month, year = map(int, parts)

        # Проверка диапазонов (упрощённая)
        if not (1 <= day <= 31) or not (1 <= month <= 12) or not (1900 <= year <= 2030):
            return "Некорректная дата."

        # Суммируем все цифры
        total = day + month + year
        # Приводим к однозначному числу
        while total > 9:
            # Проверка на мастер-числа
            if total in [11, 22, 33]:
                break
            total = sum(int(digit) for digit in str(total))

        return str(total)
    except Exception as e:
        logging.error(f"Ошибка при вычислении числа жизни для {birth_date_str}: {e}")
        return "Ошибка при расчёте."

# Функция для создания стартовой клавиатуры
def get_start_keyboard():
    """Клавиатура для начального экрана"""
    keyboard = [
        [types.KeyboardButton(text="❓ Помощь")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Функция для установки команд бота
async def set_bot_commands(bot: Bot):
    """Устанавливает список команд бота, видимый в интерфейсе Telegram."""
    commands = [
        types.BotCommand(command="start", description="Начать работу с ботом"),
        types.BotCommand(command="help", description="Получить справку о командах и функциях бота"),
    ]
    await bot.set_my_commands(commands)

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start - удаляет команду и показывает приветствие"""
    # Пытаемся удалить сообщение с командой
    try:
        await message.delete()
        command_deleted = True
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение /start: {e}")
        command_deleted = False

    # Сохраняем пользователя в базе данных
    await save_user(message.from_user.id)
    # Очищаем состояние
    await state.clear()
    
    # Текст приветствия
    welcome_text = """
🔮 Привет! Я астрологический бот!

Я могу:
• Определить ваш знак зодиака
• Сгенерировать натальную карту
• Присылать ежедневный гороскоп
• Дать детальный астрологический анализ

Введите вашу дату рождения в формате ДД.ММ.ГГГГ
Например: 31.07.1990
"""
    # Отправляем новое сообщение с приветствием
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=welcome_text,
        reply_markup=get_start_keyboard()
    )

# Функция для проверки формата даты
def validate_date_format(date_str: str) -> tuple[bool, str]:
    """Проверка формата даты"""
    if not date_str or not isinstance(date_str, str):
        return False, "Дата не может быть пустой"
    
    # Проверка формата ДД.ММ.ГГГГ
    if not re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', date_str):
        return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 31.07.1990)"
    
    try:
        parts = date_str.split('.')
        day, month, year = map(int, parts)
        
        # Проверка диапазонов
        if not (1 <= day <= 31):
            return False, f"День должен быть от 1 до 31 (вы ввели: {day})"
        if not (1 <= month <= 12):
            return False, f"Месяц должен быть от 1 до 12 (вы ввели: {month})"
        if not (1900 <= year <= 2030):
            return False, f"Год должен быть от 1900 до 2030 (вы ввели: {year})"
        
        # Проверка корректности даты
        if month in [4, 6, 9, 11] and day > 30:
            return False, f"В этом месяце только 30 дней"
        if month == 2:
            # Проверка високосного года
            is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
            max_feb_days = 29 if is_leap else 28
            if day > max_feb_days:
                return False, f"В феврале {year} года только {max_feb_days} дней"
        
        return True, ""
    except ValueError:
        return False, "Неверный формат чисел в дате"

# Функция для проверки формата времени
def validate_time_format(time_str: str) -> tuple[bool, str]:
    """Проверка формата времени"""
    if not time_str or not isinstance(time_str, str):
        return False, "Время не может быть пустым"
    
    if time_str == '-':
        return True, ""
    
    # Проверка формата ЧЧ:ММ
    if not re.match(r'^\d{1,2}:\d{2}$', time_str):
        return False, "Неверный формат времени. Используйте ЧЧ:ММ (например: 14:30) или '-' если не знаете"
    
    try:
        parts = time_str.split(':')
        hour, minute = map(int, parts)
        
        if not (0 <= hour <= 23):
            return False, f"Час должен быть от 0 до 23 (вы ввели: {hour})"
        if not (0 <= minute <= 59):
            return False, f"Минуты должны быть от 0 до 59 (вы ввели: {minute})"
        
        return True, ""
    except ValueError:
        return False, "Неверный формат чисел во времени"

# Обработчик ввода даты рождения
@dp.message(lambda message: message.text and '.' in message.text and len(message.text.split('.')) == 3)
async def get_birth_date(message: types.Message, state: FSMContext):
    """Обработка ввода даты рождения - удаляет сообщение и обрабатывает данные"""
    # Пытаемся удалить сообщение пользователя
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с датой: {e}")

    # Проверяем, ожидаем ли мы дату рождения
    current_state = await state.get_state()
    if current_state is not None and current_state != UserData.waiting_for_birth_date.state:
        # Если мы в другом состоянии, не обрабатываем это сообщение
        # (например, если пользователь случайно отправил дату позже)
        # В этом случае сообщение уже удалено, ничего не делаем
        return
    
    date_str = message.text.strip()
    
    # Валидация даты
    is_valid, error_message = validate_date_format(date_str)
    if not is_valid:
        # Отправляем сообщение об ошибке в чат
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"❌ Ошибка: {error_message}\n\nПожалуйста, введите дату в формате ДД.ММ.ГГГГ\nПример: 31.07.1990"
        )
        return
    
    try:
        parts = date_str.split('.')
        day, month, year = map(int, parts)
        
        # Дополнительная проверка корректности даты
        import datetime
        try:
            datetime.date(year, month, day)
        except ValueError as e:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=f"❌ Ошибка: Некорректная дата ({str(e)})\n\nПожалуйста, введите существующую дату"
            )
            return
        
        zodiac = get_zodiac_sign(day, month)
        
        # Сохраняем дату рождения и знак зодиака в состоянии
        await state.update_data(birth_date=date_str, zodiac_sign=zodiac)
        
        # Устанавливаем состояние ожидания времени рождения
        await state.set_state(UserData.waiting_for_birth_time)
        
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"✅ Дата принята!\nВаш знак зодиака: {zodiac} ♢\n\n"
                 f"Введите время рождения (формат ЧЧ:ММ) или отправьте '-' если не знаете:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
    except Exception as e:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"❌ Произошла ошибка при обработке даты: {str(e)}\n\n"
                 f"Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\nПример: 31.07.1990"
        )

# Обработчик ввода времени рождения
@dp.message(UserData.waiting_for_birth_time)
async def get_birth_time(message: types.Message, state: FSMContext):
    """Обработка ввода времени рождения - удаляет сообщение и обрабатывает данные"""
    # Пытаемся удалить сообщение пользователя
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с временем: {e}")

    time_str = message.text.strip()
    
    # Валидация времени
    is_valid, error_message = validate_time_format(time_str)
    if not is_valid:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"❌ Ошибка: {error_message}\n\nВведите время в формате ЧЧ:ММ или '-' если не знаете"
        )
        return
    
    birth_time = None
    if time_str != '-':
        birth_time = time_str
    
    # Сохраняем время рождения в состоянии
    await state.update_data(birth_time=birth_time)
    
    # Устанавливаем состояние ожидания места рождения
    await state.set_state(UserData.waiting_for_birth_place)
    
    await message.bot.send_message(
        chat_id=message.chat.id,
        text="Введите место рождения (город) или отправьте '-':",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработчик ввода места рождения
@dp.message(UserData.waiting_for_birth_place)
async def get_birth_place(message: types.Message, state: FSMContext):
    """Обработка ввода места рождения - удаляет сообщение и обрабатывает данные"""
    # Пытаемся удалить сообщение пользователя
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с местом: {e}")

    birth_place = None
    place_text = message.text.strip()
    
    # Проверка на пустой ввод
    if not place_text:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Место рождения не может быть пустым. Введите название города или отправьте '-'"
        )
        return
    
    if place_text != '-':
        # Проверка на допустимые символы
        if not re.match(r'^[а-яА-Яa-zA-Z\s\-,\.\d]+$', place_text):
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="❌ Недопустимые символы в названии города. Используйте буквы, пробелы и дефисы"
            )
            return
        birth_place = place_text
    
    # Получаем все данные из состояния
    user_data = await state.get_data()
    birth_date = user_data['birth_date']
    zodiac_sign = user_data['zodiac_sign']
    birth_time = user_data.get('birth_time')
    
    # Сохраняем данные в базе данных
    await update_user_data(
        message.from_user.id, 
        birth_date, 
        zodiac_sign, 
        birth_time, 
        birth_place
    )
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем подтверждение и показываем главное меню
    await message.bot.send_message(
        chat_id=message.chat.id,
        text="✅ Данные успешно сохранены!",
        reply_markup=get_main_keyboard()
    )
    
    # Показываем приветственное сообщение с кнопками
    welcome_msg = f"""
🔮 Добро пожаловать в меню астролога!

Ваш профиль:
🎂 Дата рождения: {birth_date}
⭐ Знак зодиака: {zodiac_sign}
"""
    if birth_time:
        welcome_msg += f"⏰ Время рождения: {birth_time}\n"
    if birth_place:
        welcome_msg += f"📍 Место рождения: {birth_place}\n"
    
    welcome_msg += "\nИспользуйте кнопки ниже для навигации:"
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=welcome_msg
    )

# --- ХЭНДЛЕРЫ ДЛЯ КНОПОК И КОМАНД ---
# Они должны быть зарегистрированы до универсального хэндлера, чтобы сработать первыми

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help - удаляет команду и показывает помощь"""
    # Пытаемся удалить сообщение с командой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение /help: {e}")

    help_text = """
🔮 Помощь по боту:

Для начала работы введите дату рождения в формате ДД.ММ.ГГГГ
Пример: 31.07.1990

Кнопки меню:
🔮 Гороскоп - Получить гороскоп на сегодня
📊 Натальная карта - Ссылка на вашу натальную карту
👤 Мой профиль - Просмотр ваших данных
📨 Подписаться - Ежедневная рассылка гороскопа
❌ Отписаться - Отменить подписку
❓ Помощь - Показать эту справку

Для вопросов, связанных с некорректной работой бота, прошу сообщать @Bossofgyms

Также доступны команды:
/start - Начать работу с ботом
/help - Помощь
"""
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=help_text,
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки '🔮 Гороскоп'
@dp.message(lambda message: message.text == "🔮 Гороскоп")
async def btn_horoscope(message: types.Message):
    """Обработчик кнопки '🔮 Гороскоп' - удаляет сообщение и показывает гороскоп"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Гороскоп: {e}")

    # 1. Получаем данные пользователя из БД
    user_data_from_db = await get_user_data(message.from_user.id)
    if not user_data_from_db or not user_data_from_db[1]: # Проверяем наличие знака зодиака
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сначала введите дату рождения через /start"
        )
        return

    # 2. Извлекаем необходимые данные
    birth_date_str = user_data_from_db[0]  # Дата рождения (строка)
    zodiac_sign = user_data_from_db[1]     # Знак зодиака (строка)

    # 3. Подготавливаем параметры дня и месяца рождения
    birth_day_int = None
    birth_month_int = None
    if birth_date_str:
        try:
            day, month, year = map(int, birth_date_str.split('.'))
            birth_day_int = day
            birth_month_int = month
        except (ValueError, IndexError):
            logging.warning(f"Предупреждение: Не удалось распарсить дату рождения '{birth_date_str}' для пользователя {message.from_user.id}")
            # birth_day_int и birth_month_int останутся None

    # 4. Отправляем сообщение о загрузке и вызываем функцию гороскопа
    # loading_msg = await message.answer("🔮 Получаю астрологический гороскоп...")
    loading_msg = await message.bot.send_message(
        chat_id=message.chat.id,
        text="🔮 Получаю астрологический гороскоп..."
    )
    
    # 5. Передаем день и месяц рождения в функцию
    horoscope_data = await get_daily_horoscope(zodiac_sign, birth_day_int, birth_month_int)
    
    await loading_msg.delete()
    
    message_text = format_real_horoscope_message(horoscope_data)
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=message_text,
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки '📊 Натальная карта'
@dp.message(lambda message: message.text == "📊 Натальная карта")
async def btn_natal_chart(message: types.Message):
    """Обработчик кнопки '📊 Натальная карта' - удаляет сообщение и показывает карту"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Натальная карта: {e}")

    # 1. Получаем данные пользователя из БД
    user_data = await get_user_data(message.from_user.id)
    if not user_data or not user_data[0]:  # Проверяем наличие даты рождения
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сначала введите дату рождения через /start"
        )
        return
    
    # 2. Извлекаем данные
    birth_date, zodiac_sign, birth_time, birth_place = user_data
    
    # 3. Получаем информацию о натальной карте 
    # Теперь get_natal_chart_info возвращает dict с ключами 'info_text' и 'url'
    natal_data = await get_natal_chart_info(birth_date, birth_time, birth_place)
    
    # 4. Проверяем, не возникла ли ошибка внутри get_natal_chart_info
    if isinstance(natal_data, dict) and "error" in natal_data:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=natal_data["error"]
        )
        return

    # 5. Извлекаем текст и URL из результата
    if isinstance(natal_data, dict) and "info_text" in natal_data and "url" in natal_data:
        info_text = natal_data["info_text"]
        chart_url = natal_data["url"]
    else:
        # На случай, если функция по какой-то причине всё ещё возвращает строку
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="⚠️ Ошибка получения данных натальной карты."
        )
        return

    # 6. Формируем основной текст ответа
    response = f"📊 Натальная карта для {zodiac_sign}\n\n"
    response += info_text # Добавляем информационный текст

    # 7. Создаем кнопку с ссылкой на натальную карту
    button = InlineKeyboardButton(text="🔮 Рассчитать натальную карту", url=chart_url)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

    # 8. Отправляем сообщение с текстом и кнопкой
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=response, 
        reply_markup=keyboard, # Прикрепляем клавиатуру с кнопкой
        disable_web_page_preview=True # Отключаем предпросмотр ссылки в основном тексте
    )

# Обработчик кнопки '👤 Мой профиль'
@dp.message(lambda message: message.text == "👤 Мой профиль")
async def btn_profile(message: types.Message):
    """Обработчик кнопки '👤 Мой профиль' - удаляет сообщение и показывает профиль"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Мой профиль: {e}")

    user_data = await get_user_data(message.from_user.id)
    if not user_data or not user_data[0]:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сначала введите дату рождения через /start"
        )
        return
    
    birth_date, zodiac_sign, birth_time, birth_place = user_data
    
    if not birth_date:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сначала введите дату рождения через /start"
        )
        return
    
    response = f"👤 Ваш профиль:\n\n"
    response += f"🎂 Дата рождения: {birth_date}\n"
    response += f"⭐ Знак зодиака: {zodiac_sign or 'Не определен'}\n"
    if birth_time:
        response += f"⏰ Время рождения: {birth_time}\n"
    if birth_place:
        response += f"📍 Место рождения: {birth_place}\n"
    
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=response,
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки '📨 Подписаться на гороскоп'
@dp.message(lambda message: message.text == "📨 Подписаться на гороскоп")
async def btn_subscribe(message: types.Message):
    """Обработчик кнопки '📨 Подписаться' - удаляет сообщение и подписывает"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Подписаться: {e}")

    user_data = await get_user_data(message.from_user.id)
    if not user_data or not user_data[1]:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сначала введите дату рождения через /start"
        )
        return
    
    await subscribe_user(message.from_user.id)
    await message.bot.send_message(
        chat_id=message.chat.id,
        text="✅ Вы успешно подписались на ежедневную рассылку гороскопа!\nГороскоп будет приходить каждый день в 9:00 утра.",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки '❌ Отписаться'
@dp.message(lambda message: message.text == "❌ Отписаться")
async def btn_unsubscribe(message: types.Message):
    """Обработчик кнопки '❌ Отписаться' - удаляет сообщение и отписывает"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Отписаться: {e}")

    await unsubscribe_user(message.from_user.id)
    await message.bot.send_message(
        chat_id=message.chat.id,
        text="❌ Вы отписались от ежедневной рассылки гороскопа.",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки '❓ Помощь'
@dp.message(lambda message: message.text == "❓ Помощь")
async def btn_help(message: types.Message):
    """Обработчик кнопки '❓ Помощь' - удаляет сообщение и показывает помощь"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Помощь: {e}")

    help_text = """
🔮 Помощь по боту:

Для начала работы введите дату рождения в формате ДД.ММ.ГГГГ
Пример: 31.07.1990

Кнопки меню:
🔮 Гороскоп - Получить гороскоп на сегодня
📊 Натальная карта - Ссылка на вашу натальную карту
👤 Мой профиль - Просмотр ваших данных
📨 Подписаться - Ежедневная рассылка гороскопа
❌ Отписаться - Отменить подписку
❓ Помощь - Показать эту справку

Для вопросов, связанных с некорректной работой бота, прошу сообщать @Bossofgyms

Также доступны команды:
/start - Начать работу с ботом
/help - Помощь
"""
    await message.bot.send_message(
        chat_id=message.chat.id,
        text=help_text,
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки "🔢 Число жизни"
@dp.message(lambda message: message.text == "🔢 Число жизни")
async def btn_soul_formula(message: types.Message):
    """Обработчик кнопки '🔢 Число жизни' - удаляет сообщение и показывает результат"""
    # Пытаемся удалить сообщение с кнопкой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопкой Число жизни: {e}")

    # 1. Получаем данные пользователя из БД
    user_data = await get_user_data(message.from_user.id)
    if not user_data or not user_data[0]:  # Проверяем наличие даты рождения
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Сначала введите дату рождения через /start",
            reply_markup=get_main_keyboard() # Добавляем клавиатуру для удобства
        )
        return

    # 2. Извлекаем дату рождения
    birth_date = user_data[0]

    # 3. Вычисляем формулу души
    soul_number = calculate_soul_formula(birth_date)

    # 4. Формируем и отправляем ответ
    # --- Обновляем описания с более подробной информацией ---
    descriptions = {
        "1": (
            "Единица символизирует новое начало, лидерство, независимость и стремление быть первым. "
            "Вы обладаете сильной волей, инициативой и амбициями. Люди с этим числом часто становятся вдохновителями и новаторами. "
            "Ваши сильные стороны: решительность, уверенность, творческий подход, способность принимать решения. "
            "Возможные слабые стороны: импульсивность, нетерпение, стремление контролировать, индивидуализм."
        ),
        "2": (
            "Двойка олицетворяет сотрудничество, дипломатию, чувствительность и стремление к гармонии. "
            "Вы цените партнёрские отношения, умеете слушать и чувствуете настроение окружающих. "
            "Ваши сильные стороны: эмпатия, дипломатичность, умение работать в команде, гибкость. "
            "Возможные слабые стороны: излишняя зависимость от мнения других, неуверенность, избегание конфликтов, чрезмерная чувствительность."
        ),
        "3": (
            "Тройка символизирует творчество, самовыражение, общительность и оптимизм. "
            "Вы легко находите общий язык с людьми, любите общение и умеете вдохновлять. "
            "Ваши сильные стороны: коммуникабельность, творческий талант, жизнерадостность, воображение. "
            "Возможные слабые стороны: поверхностность, рассеянность, излишняя болтливость, трудности с концентрацией."
        ),
        "4": (
            "Четверка означает стабильность, практичность, организованность и трудолюбие. "
            "Вы цените порядок, надежность и способны доводить начатое до конца. "
            "Ваши сильные стороны: дисциплина, надежность, логическое мышление, терпение. "
            "Возможные слабые стороны: упрямство, склонность к рутине, излишний пессимизм, сопротивление переменам."
        ),
        "5": (
            "Пятерка символизирует свободу, приключения, адаптивность и любопытство. "
            "Вы любите перемены, новые впечатления и не боитесь риска. "
            "Ваши сильные стороны: адаптивность, любознательность, энергичность, гибкость мышления. "
            "Возможные слабые стороны: неугомонность, непостоянство, трудности с обязательствами, импульсивность."
        ),
        "6": (
            "Шестерка олицетворяет заботу, ответственность, гармонию и чувство долга. "
            "Вы стремитесь к стабильным отношениям, заботитесь о близких и цените красоту и порядок. "
            "Ваши сильные стороны: заботливость, надежность, чувство справедливости, любовь к красоте. "
            "Возможные слабые стороны: чрезмерная тревожность, стремление контролировать других, самопожертвование, обида при недостатке благодарности."
        ),
        "7": (
            "Семерка символизирует анализ, интроспекцию, стремление к знаниям и поиск истины. "
            "Вы любите размышлять, углубляться в суть вещей и цените уединение. "
            "Ваши сильные стороны: аналитический ум, интуиция, мудрость, стремление к самопознанию. "
            "Возможные слабые стороны: склонность к изоляции, чрезмерный перфекционизм, скептицизм, трудности с выражением эмоций."
        ),
        "8": (
            "Восьмерка означает власть, материальный успех, амбиции и управленческие способности. "
            "Вы стремитесь к достижению целей, обладаете сильной волей и чувством справедливости. "
            "Ваши сильные стороны: решимость, организаторские способности, умение зарабатывать, практическая польза. "
            "Возможные слабые стороны: чрезмерный фокус на материальном, жесткость, склонность к манипуляциям, трудности в личной жизни из-за работы."
        ),
        "9": (
            "Девятка символизирует гуманизм, идеализм, сострадание и стремление служить другим. "
            "Вы чувствительны к страданиям мира и стремитесь внести вклад в общее благо. "
            "Ваши сильные стороны: сострадание, альтруизм, толерантность, творческий потенциал. "
            "Возможные слабые стороны: чрезмерная эмоциональность, склонность к жертвенности, разочарование из-за несовершенства мира, трудности с постановкой личных границ."
        ),
        "11": (
            "Одиннадцать - мастер-число, символизирующее интуицию, вдохновение, идеализм и потенциал для духовного пробуждения. "
            "Вы обладаете острым умом, чувствительны к энергетике окружающих и часто испытываете вдохновение. "
            "Ваши сильные стороны: высокая интуиция, вдохновляющее лидерство, идеализм, чувствительность. "
            "Возможные слабые стороны: чрезмерная чувствительность, склонность к иллюзиям, внутренние конфликты из-за высоких идеалов, трудности с заземлением."
        ),
        "22": (
            "Двадцать два - мастер-число, символизирующее мастерство в воплощении великих идей, практичный идеализм и сильное влияние на мир. "
            "Вы обладаете потенциалом для реализации масштабных проектов и можете вдохновлять других на большие свершения. "
            "Ваши сильные стороны: практические мечтатели, сильная воля, лидерские качества, способность вдохновлять. "
            "Возможные слабые стороны: давление высоких ожиданий, трудности с балансом между идеалами и реальностью, склонность к перегрузке."
        ),
        "33": (
            "Тридцать три - редкое мастер-число, символизирующее высшую степень сострадания, мудрости и способности быть учителем и целителем. "
            "Вы обладаете великодушием и стремлением помогать другим на глубоком уровне. "
            "Ваши сильные стороны: высокое сострадание, мудрость, вдохновляющее наставничество, целительная энергия. "
            "Возможные слабые стороны: чрезмерная жертвенность, трудности с установлением личных границ, эмоциональное выгорание из-за заботы о других."
        ),
        # Обработка ошибок
        "Дата рождения не указана.": "❌ Дата рождения не указана.",
        "Неверный формат даты.": "❌ Неверный формат даты.",
        "Некорректная дата.": "❌ Некорректная дата.",
        "Ошибка при расчёте.": "❌ Ошибка при расчёте формулы души."
    }
    # --- Конец обновленных описаний ---

    base_description = descriptions.get(soul_number, f"Неизвестное число: {soul_number}")

    # Добавляем научно-обоснованное предупреждение
    disclaimer = "\n\nℹ️ *Важно:* Нумерология не является научной дисциплиной. Это интерпретация чисел, основанная на традициях и верованиях."

    response = f"🔢 Ваше Число Жизни: *{soul_number}*\n\n{base_description}{disclaimer}"

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=response,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown' # Используем Markdown для форматирования
    )

# УНИВЕРСАЛЬНЫЙ ХЭНДЛЕР ДЛЯ ОСТАЛЬНЫХ СООБЩЕНИЙ
# Этот хэндлер должен быть последним, чтобы не перехватывать команды и кнопки
@dp.message(~F.text.startswith("/")) # Ловим сообщения, которые НЕ начинаются с "/"
async def handle_any_other_message(message: types.Message, state: FSMContext):
    """
    Универсальный обработчик для любых других текстовых сообщений.
    Пытается удалить сообщение пользователя.
    Обрабатывает FSM-состояния.
    """
    # Пытаемся удалить любое входящее текстовое сообщение (кроме команд)
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение '{message.text}': {e}")

    current_state = await state.get_state()
    
    # Если пользователь в процессе ввода данных, но отправил что-то не то
    if current_state == UserData.waiting_for_birth_date.state:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Пожалуйста, введите дату рождения в формате ДД.ММ.ГГГГ\n"
                 "Пример: 31.07.1990"
        )
    elif current_state == UserData.waiting_for_birth_time.state:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Пожалуйста, введите время рождения в формате ЧЧ:ММ или '-' если не знаете\n"
                 "Пример: 14:30 или -"
        )
    elif current_state == UserData.waiting_for_birth_place.state:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="❌ Пожалуйста, введите место рождения (город) или '-' если не знаете"
        )
    # Для всех других случаев (например, случайный текст) просто игнорируем
    # или можно отправить общее сообщение, если нужно:
    # else:
    #     await message.bot.send_message(
    #         chat_id=message.chat.id,
    #         text="🔮 Пожалуйста, используйте кнопки меню или команды.\n/help - Помощь",
    #         reply_markup=get_main_keyboard()
    #     )

# Функция для форматирования реального гороскопа
def format_real_horoscope_message(data: dict) -> str:
    """Форматирование реального гороскопа с астрологическими данными"""
    message = data.get('description', 'Гороскоп недоступен.')
    return message

# Основная функция запуска бота
async def main():
    await init_db()
    
    # Инициализируем бота для установки команд
    bot_instance = Bot(token=BOT_TOKEN)
    
    # Устанавливаем команды
    await set_bot_commands(bot_instance)
    
    # Запускаем планировщик
    asyncio.create_task(scheduler(bot_instance))
    
    # Запускаем polling
    await dp.start_polling(bot_instance)

# Точка входа в программу
if __name__ == "__main__":
    asyncio.run(main())
