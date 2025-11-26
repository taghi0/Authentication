import random
import string
from balecore import Bot, Message, OTP
from balecore.keyboards import ReplyKeyboardMarkup, ReplyKeyboardButton, ReplyKeyboardRemove
from database import db
from config import config

class AuthBot:
    def __init__(self, token: str):
        self.bot = Bot(token)
        self.user_states = {}
        self.user_data = {}
        self.setup_handlers()

    def setup_handlers(self):
        @self.bot.Message(commands=['start'])
        async def start_handler(message: Message):
            user_id = message.from_user.id

            if db.is_user_banned(user_id):
                await message.reply("❌ حساب شما به دلیل تلاش‌های ناموفق متعدد موقتاً مسدود شده است.")
                return

            user = db.get_user(user_id)
            if user and user['is_verified']:
                await message.reply(
                    "✅ شما قبلاً احراز هویت شده‌اید!\n"
                    "می‌توانید به ربات اصلی برگردید."
                )
                return

            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [ReplyKeyboardButton("📱 ارسال شماره موبایل", request_contact=True)]
                ],
                selective=True
            )

            await message.reply(
                "🔐 به سامانه احراز هویت خوش آمدید!\n\n"
                "لطفاً برای ادامه فرآیند احراز هویت، شماره موبایل خود را ارسال کنید:",
                reply_markup=keyboard
            )

            self.user_states[user_id] = "waiting_for_phone"

        @self.bot.Message(content_types=['contact'])
        async def contact_handler(message: Message):
            user_id = message.from_user.id

            if self.user_states.get(user_id) != "waiting_for_phone":
                return

            contact = message.contact
            if not contact or not contact.phone_number:
                await message.reply("❌ شماره موبایل دریافت نشد. لطفاً دوباره تلاش کنید.")
                return

            phone_number = self.normalize_phone_number(contact.phone_number)

            user_by_phone = db.get_user_by_phone(phone_number)
            if user_by_phone and db.is_user_banned(user_by_phone['user_id']):
                await message.reply("❌ این شماره موبایل مسدود شده است.")
                return

            db.add_user(
                user_id=user_id,
                phone_number=phone_number,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                username=message.from_user.username
            )

            otp_code = self.generate_otp(config.OTP_LENGTH)
            db.save_otp(user_id, phone_number, otp_code, config.OTP_EXPIRY_MINUTES)

            client = OTP(username=config.OTP_SERVICE_USERNAME, password=config.OTP_SERVICE_PASSWORD)

            await client.send_otp(phone_number=phone_number, code=otp_code)

            await message.reply(
                f"📲 کد تأیید برای شماره {phone_number} ارسال شد.\n\n"
                f"⏰ این کد تا {config.OTP_EXPIRY_MINUTES} دقیقه معتبر است.\n"
                f"لطفاً کد را وارد کنید:",
                reply_markup=ReplyKeyboardRemove()
            )

            self.user_states[user_id] = "waiting_for_otp"
            self.user_data[user_id] = {"phone": phone_number, "code": otp_code}

        @self.bot.Message(content_types=['text'])
        async def text_handler(message: Message):
            user_id = message.from_user.id
            current_state = self.user_states.get(user_id)

            if current_state == "waiting_for_otp":
                await self.handle_otp_verification(message)
            else:
                await message.reply(
                    "لطفاً از منوهای ارائه شده استفاده کنید یا دستور /start را ارسال کنید."
                )

    async def handle_otp_verification(self, message: Message):
        user_id = message.from_user.id
        entered_code = message.text.strip()

        if not self.is_valid_otp(entered_code, config.OTP_LENGTH):
            await message.reply(f"❌ کد باید {config.OTP_LENGTH} رقم باشد و فقط شامل اعداد باشد.")
            return

        if db.is_user_banned(user_id):
            await message.reply("❌ حساب شما مسدود شده است.")
            return

        if db.verify_otp(user_id, entered_code):
            db.update_user_verification(user_id, True)

            await message.reply(
                "✅ احراز هویت شما با موفقیت انجام شد!\n\n"
                "اکنون می‌توانید به ربات اصلی برگردید و از خدمات استفاده کنید."
            )

            self.cleanup_user_data(user_id)

        else:
            attempts = db.get_otp_attempts(user_id)
            remaining_attempts = config.MAX_VERIFICATION_ATTEMPTS - attempts

            db.add_failed_attempt(user_id, self.user_data[user_id]["phone"], "invalid_otp")

            if remaining_attempts > 0:
                await message.reply(
                    f"❌ کد وارد شده نامعتبر است.\n"
                    f"📋 تعداد تلاش‌های باقی‌مانده: {remaining_attempts}\n"
                    f"لطفاً دوباره کد را وارد کنید:"
                )
            else:
                db.ban_user(user_id, config.BAN_DURATION_HOURS)
                await message.reply(
                    f"❌ تعداد تلاش‌های شما بیش از حد مجاز بود.\n"
                    f"🔒 حساب شما به مدت {config.BAN_DURATION_HOURS} ساعت مسدود شد."
                )
                self.cleanup_user_data(user_id)

    def generate_otp(self, length: int = 6) -> str:
        return ''.join(random.choices(string.digits, k=length))

    def normalize_phone_number(self, phone: str) -> str:
        digits = ''.join(filter(str.isdigit, phone))

        if digits.startswith('0'):
            return '98' + digits[1:]

        return digits

    def is_valid_otp(self, code: str, expected_length: int) -> bool:
        return code.isdigit() and len(code) == expected_length

    def cleanup_user_data(self, user_id: int):
        self.user_states.pop(user_id, None)
        self.user_data.pop(user_id, None)

    async def run(self):
        await self.bot.start_polling

auth_bot = AuthBot(config.AUTH_BOT_TOKEN)