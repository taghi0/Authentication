class Config:
    AUTH_BOT_TOKEN = ""
    MAIN_BOT_TOKEN = ""

    AUTH_BOT_USERNAME = "@"

    OTP_SERVICE_PASSWORD = ""
    OTP_SERVICE_USERNAME = ""

    DATABASE_URL = "sqlite:///auth_system.db"

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_OTP_ATTEMPTS = 2
    MAX_VERIFICATION_ATTEMPTS = 2

    BAN_DURATION_HOURS = 24

config = Config()