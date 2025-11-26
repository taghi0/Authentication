import asyncio
import logging
from auth_bot import auth_bot
from main_bot import main_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def run_bots():
    try:
        logger.info("Starting authentication system...")

        await asyncio.gather(
            auth_bot.run(),
            main_bot.run()
        )

    except Exception as e:
        logger.error(f"Error running bots: {e}")
    finally:
        logger.info("Authentication system stopped.")

if __name__ == "__main__":
    asyncio.run(run_bots())