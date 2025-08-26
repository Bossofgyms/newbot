# scheduler.py

import asyncio
import datetime
from aiogram import Bot
from database import get_subscribed_users
from horoscope_api import get_daily_horoscope
from config import DAILY_TIME_HOUR, DAILY_TIME_MINUTE

async def send_daily_horoscopes(bot: Bot):
    """Отправка ежедневных гороскопов подписчикам"""
    try:
        users = await get_subscribed_users()
        print(f"Отправка гороскопов {len(users)} пользователям")
        
        for user_id, zodiac_sign in users:
            try:
                horoscope_data = await get_daily_horoscope(zodiac_sign)
                
                message = f"🌅 Доброе утро! Ежедневный гороскоп для {zodiac_sign}\n\n"
                if horoscope_data.get('date'):
                    message += f"📅 {horoscope_data['date']}\n\n"
                message += f"{horoscope_data['description']}\n\n"
                
                details = []
                if horoscope_data.get('mood'):
                    details.append(f"Настроение: {horoscope_data['mood']}")
                if horoscope_data.get('color'):
                    details.append(f"Цвет дня: {horoscope_data['color']}")
                if horoscope_data.get('lucky_number'):
                    details.append(f"Счастливое число: {horoscope_data['lucky_number']}")
                if horoscope_data.get('lucky_time'):
                    details.append(f"Счастливое время: {horoscope_data['lucky_time']}")
                
                if details:
                    message += "\n".join(details) + "\n"
                
                message += "\n💫 Хорошего дня!"
                
                await bot.send_message(user_id, message)
                print(f"Гороскоп отправлен пользователю {user_id}")
                await asyncio.sleep(0.1)  # Небольшая задержка чтобы не спамить
            except Exception as e:
                print(f"Ошибка отправки гороскопа пользователю {user_id}: {e}")
                continue
    except Exception as e:
        print(f"Ошибка в send_daily_horoscopes: {e}")

async def scheduler(bot: Bot):
    """Основной планировщик"""
    while True:
        try:
            now = datetime.datetime.now()
            target_time = now.replace(hour=DAILY_TIME_HOUR, minute=DAILY_TIME_MINUTE, second=0, microsecond=0)
            
            # Если время уже прошло сегодня, установить на завтра
            if now >= target_time:
                target_time += datetime.timedelta(days=1)
            
            # Ждем до целевого времени
            wait_seconds = (target_time - now).total_seconds()
            hours = int(wait_seconds // 3600)
            minutes = int((wait_seconds % 3600) // 60)
            print(f"Следующая отправка гороскопов через {hours} часов {minutes} минут ({target_time.strftime('%d.%m.%Y %H:%M')})")
            
            await asyncio.sleep(wait_seconds)
            
            # Отправляем гороскопы
            await send_daily_horoscopes(bot)
            
            # Ждем немного, чтобы избежать повторной отправки в ту же секунду
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(60)  # Ждем минуту и пробуем снова