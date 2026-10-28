"""
Modern Bot Framework - Python 3.12+ Compatible
Updated: 2024
Enhanced error handling, logging, and async support
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pyrogram import filters
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import CallbackQuery, Message
from pyromod import Client

# Configure logging with proper formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)

# Suppress verbose logging from external libraries
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent / "assets" / ".env")

# Configuration with fallback values
class Config:
    """Bot configuration management"""

    API_ID: int = int(os.getenv("API_ID", "29402186"))
    API_HASH: str = os.getenv("API_HASH", "6741cbba99aa631d0591fbeddf02a06a")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "6649055118:AAE8UnvNlgnArVPX_QJNVYqEo1Yp6j1X0WA")
    CHANNEL_LOGS: int = int(os.getenv("CHANNEL_LOGS", "-1004297519745"))
    TARGET_CHAT_ID: int = -1002298111362

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not all([cls.API_ID, cls.API_HASH, cls.BOT_TOKEN]):
            logger.error("Missing required configuration variables")
            return False
        return True


# Import utilities after configuration
try:
    from utilsdf.functions import bot_on
    from utilsdf.db import Database
    from utilsdf.vars import PREFIXES
except ImportError as e:
    logger.error(f"Failed to import utilities: {e}")
    sys.exit(1)


class BotApp:
    """Encapsulated bot application class"""

    def __init__(self, config: Config):
        """Initialize bot with configuration"""
        self.config = config
        self.client: Optional[Client] = None
        self.db: Optional[Database] = None

    def setup_client(self) -> None:
        """Setup Pyrogram client"""
        try:
            self.client = Client(
                name="bot",
                api_id=self.config.API_ID,
                api_hash=self.config.API_HASH,
                bot_token=self.config.BOT_TOKEN,
                plugins=dict(root="plugins"),
                parse_mode=ParseMode.HTML,
                workers=8,  # Increased for better performance
            )
            logger.info("Bot client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot client: {e}")
            raise

    def setup_handlers(self) -> None:
        """Register message and callback handlers"""
        if not self.client:
            raise RuntimeError("Client not initialized")

        @self.client.on_callback_query()
        async def handle_callback_query(client: Client, callback_query: CallbackQuery) -> None:
            """Handle callback queries with safety checks"""
            try:
                # Safely check if this is a reply with proper null checks
                if callback_query.message and callback_query.message.reply_to_message:
                    reply_msg = callback_query.message.reply_to_message
                    if reply_msg.from_user and (
                        callback_query.from_user.id != reply_msg.from_user.id
                    ):
                        await callback_query.answer(
                            "Usa tu menu! ⚠️",
                            show_alert=True,
                            cache_time=60,
                        )
                        return

                await callback_query.continue_propagation()
            except Exception as e:
                logger.error(f"Error in callback query handler: {e}", exc_info=True)
                try:
                    await callback_query.answer("Error processing request", show_alert=True)
                except Exception as inner_e:
                    logger.error(f"Failed to send error alert: {inner_e}")

        @self.client.on_message(filters.text)
        async def handle_user_message(client: Client, message: Message) -> None:
            """Handle user messages with comprehensive checks"""
            try:
                # Validate message and sender
                if not message.from_user:
                    logger.debug("Ignoring message from unknown sender")
                    return

                if not message.text:
                    return

                # Check if message starts with command prefix
                try:
                    if message.text and message.text[0] not in PREFIXES:
                        return
                except (IndexError, AttributeError, UnicodeError) as e:
                    logger.debug(f"Skipping invalid message format: {e}")
                    return

                chat_id = message.chat.id

                # Initialize database connection
                try:
                    db = Database()
                except Exception as e:
                    logger.error(f"Database initialization error: {e}")
                    return

                # Handle auto-ban in specific chat
                if chat_id == self.config.TARGET_CHAT_ID:
                    await self._handle_auto_ban(client, message, db)

                # Register/update user
                await self._handle_user_registration(message, db)

                # Continue message propagation to other handlers
                await message.continue_propagation()

            except Exception as e:
                logger.error(f"Error in user message handler: {e}", exc_info=True)

        logger.info("Message handlers registered successfully")

    async def _handle_auto_ban(self, client: Client, message: Message, db: Database) -> None:
        """Handle automatic user banning logic"""
        try:
            async for member in message.chat.get_members():
                try:
                    # Skip if no user data
                    if not member.user:
                        continue

                    # Skip administrators
                    if member.status == ChatMemberStatus.ADMINISTRATOR:
                        continue

                    user_id = member.user.id

                    # Check user permissions
                    if db.is_seller_or_admin(user_id):
                        continue

                    if db.is_premium(user_id):
                        continue

                    if db.user_has_credits(user_id):
                        continue

                    # Ban the user
                    await message.chat.ban_member(user_id)

                    # Log the action
                    try:
                        user_info = db.get_info_user(user_id)
                        username = user_info.get("USERNAME", "Unknown") if user_info else "Unknown"
                        log_msg = f"<b>User eliminado:</b> @{username} (ID: {user_id})"
                        await client.send_message(
                            self.config.CHANNEL_LOGS,
                            log_msg,
                            disable_web_page_preview=True,
                        )
                    except Exception as e:
                        logger.error(f"Failed to log ban for user {user_id}: {e}")

                except Exception as e:
                    logger.error(f"Error processing member {member.user.id if member.user else 'unknown'}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in auto-ban handler: {e}", exc_info=True)

    async def _handle_user_registration(self, message: Message, db: Database) -> None:
        """Handle user registration and cleanup"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username

            # Remove expired users
            db.remove_expireds_users()

            # Check if user is banned
            if db.is_ban(user_id):
                logger.debug(f"Ignoring banned user {user_id}")
                return

            # Register or update user
            db.register_user(user_id, username)
            logger.debug(f"User {user_id} (@{username}) processed")

        except Exception as e:
            logger.error(f"Error in user registration: {e}", exc_info=True)

    def run(self) -> None:
        """Start the bot"""
        try:
            # Validate configuration
            if not self.config.validate():
                raise RuntimeError("Configuration validation failed")

            # Setup client
            self.setup_client()

            # Setup handlers
            self.setup_handlers()

            # Initialize database
            bot_on()
            logger.info("Database initialized")

            # Start the client
            logger.info("Starting bot...")
            if self.client:
                self.client.run()
            else:
                raise RuntimeError("Client not properly initialized")

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


def main() -> None:
    """Main entry point"""
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Starting Bot Framework...")

    config = Config()
    app = BotApp(config)
    app.run()


if __name__ == "__main__":
    main()
