from balecore import Bot, Message
from database import db
from config import config

class MainBot:
    def __init__(self, token: str, auth_bot_username: str):
        self.bot = Bot(token)
        self.auth_bot_username = auth_bot_username
        self.setup_handlers()

    def setup_handlers(self):
        @self.bot.Message(commands=['start'])
        async def start_handler(message: Message):
            user_id = message.from_user.id

            user = db.get_user(user_id)

            if user and user['is_verified']:
                await message.reply(
                    "🎉 به ربات اصلی خوش آمدید!\n\n"
                    "✅ شما قبلاً احراز هویت شده‌اید و می‌توانید از خدمات ما استفاده کنید.\n\n"
                    "📊 اطلاعات حساب شما:\n"
                    f"👤 نام: {user['first_name'] or 'تعیین نشده'}\n"
                    f"📱 شماره: {user['phone_number']}\n"
                    f"🆔 نام کاربری: @{user['username'] or 'ندارد'}"
                )
            else:
                auth_link = f"https://ble.ir/{self.auth_bot_username}?start=auth"

                await message.reply(
                    "🔐 به ربات اصلی خوش آمدید!\n\n"
                    "برای استفاده از خدمات، ابتدا باید احراز هویت شوید.\n\n"
                    f"لطفاً به ربات احراز هویت مراجعه کنید:\n"
                    f"👉 [ربات احراز هویت]({auth_link})\n\n"
                    "پس از تکمیل احراز هویت، به این ربات برگردید.",
                )

        @self.bot.Message(commands=['profile'])
        async def profile_handler(message: Message):
            user_id = message.from_user.id
            user = db.get_user(user_id)

            if not user:
                await message.reply("❌ شما هنوز ثبت‌نام نکرده‌اید. لطفاً از /start استفاده کنید.")
                return

            if not user['is_verified']:
                auth_link = f"https://ble.ir/{self.auth_bot_username}?start=auth"
                await message.reply(
                    "❌ شما هنوز احراز هویت نشده‌اید.\n\n"
                    f"لطفاً به ربات احراز هویت مراجعه کنید:\n"
                    f"👉 [ربات احراز هویت]({auth_link})",
                )
                return

            status = "✅ احراز هویت شده" if user['is_verified'] else "❌ احراز هویت نشده"
            verified_date = user['verified_at'] or "تعیین نشده"

            await message.reply(
                "👤 پروفایل شما:\n\n"
                f"🆔 شناسه: {user['user_id']}\n"
                f"👤 نام: {user['first_name'] or 'تعیین نشده'}\n"
                f"📱 شماره: {user['phone_number']}\n"
                f"🆔 نام کاربری: @{user['username'] or 'ندارد'}\n"
                f"🔐 وضعیت: {status}\n"
                f"📅 تاریخ احراز: {verified_date}"
            )

        @self.bot.Message(commands=['help'])
        async def help_handler(message: Message):
            await message.reply(
                "📖 راهنمای ربات اصلی:\n\n"
                "/start - شروع کار با ربات\n"
                "/profile - مشاهده پروفایل\n"
                "/help - نمایش این راهنما\n\n"
                "🔐 برای احراز هویت به ربات زیر مراجعه کنید:\n"
                f"@{self.auth_bot_username}"
            )

    async def run(self):
        await self.bot.start_polling

main_bot = MainBot(config.MAIN_BOT_TOKEN, config.AUTH_BOT_USERNAME)