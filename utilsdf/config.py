"""
Configuration Management - Python 3.12+ Compatible
Centralized configuration with validation and environment variable support
"""

import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class LogConfig:
    """Logging configuration"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "bot.log"
    max_size_mb: int = 100
    backup_count: int = 5


@dataclass
class TelegramConfig:
    """Telegram Bot configuration"""

    api_id: int
    api_hash: str
    bot_token: str
    workers: int = 8
    session_name: str = "bot"
    parse_mode: str = "HTML"

    def validate(self) -> bool:
        """Validate Telegram configuration"""
        if not all([self.api_id, self.api_hash, self.bot_token]):
            logger.error("Missing Telegram credentials")
            return False
        if self.workers < 1 or self.workers > 32:
            logger.warning(f"Invalid worker count {self.workers}, setting to 8")
            self.workers = 8
        return True


@dataclass
class ChatConfig:
    """Chat-specific configuration"""

    logs_channel_id: int
    target_chat_id: int
    admin_chat_id: Optional[int] = None
    welcome_enabled: bool = True


@dataclass
class DatabaseConfig:
    """Database configuration"""

    path: str = "assets/db_bot.db"
    timeout: int = 30
    check_same_thread: bool = False
    enable_foreign_keys: bool = True
    journal_mode: str = "WAL"  # Write-Ahead Logging for better concurrency


@dataclass
class FeatureConfig:
    """Feature toggles and configuration"""

    auto_ban_enabled: bool = True
    captcha_enabled: bool = True
    antispam_enabled: bool = True
    rate_limiting_enabled: bool = True
    default_ratelimit: int = 60  # seconds

    # Feature thresholds
    captcha_threshold: int = 2  # Require captcha after N messages
    ban_threshold: int = 10  # Ban after N infractions


@dataclass
class BotConfig:
    """Main bot configuration"""

    telegram: TelegramConfig
    chat: ChatConfig
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LogConfig = field(default_factory=LogConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)

    # Metadata
    version: str = "1.4.0"
    debug: bool = False
    owner_id: int = 5579729798

    def validate(self) -> bool:
        """Validate all configurations"""
        validations = [
            (self.telegram.validate(), "Telegram config"),
            (self._validate_paths(), "Paths"),
            (self._validate_timeouts(), "Timeouts"),
        ]

        for is_valid, config_name in validations:
            if not is_valid:
                logger.error(f"Validation failed for {config_name}")
                return False

        return True

    def _validate_paths(self) -> bool:
        """Validate file paths"""
        db_dir = Path(self.database.path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir.exists()

    def _validate_timeouts(self) -> bool:
        """Validate timeout values"""
        if self.database.timeout < 5:
            logger.warning("Database timeout too low, setting to 30")
            self.database.timeout = 30
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)


class ConfigLoader:
    """Load and manage bot configuration"""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize config loader"""
        self.env_file = env_file or "assets/.env"
        self.config: Optional[BotConfig] = None

    def load(self) -> BotConfig:
        """Load configuration from environment and .env file"""
        # Load environment variables
        env_path = Path(self.env_file)
        if env_path.exists():
            load_dotenv(env_path)
        else:
            logger.warning(f"Environment file not found at {env_path}")

        try:
            # Telegram configuration
            telegram_config = TelegramConfig(
                api_id=int(self._get_env("API_ID", "29890751")),
                api_hash=self._get_env("API_HASH", "7fbdb8f35aea92c9726f3f2667fbd548"),
                bot_token=self._get_env("BOT_TOKEN", ""),
                workers=int(self._get_env("WORKERS", "8")),
            )

            # Chat configuration
            chat_config = ChatConfig(
                logs_channel_id=int(self._get_env("CHANNEL_LOGS", "-4047350871")),
                target_chat_id=int(self._get_env("TARGET_CHAT_ID", "-1001494650944")),
            )

            # Database configuration
            database_config = DatabaseConfig(
                path=self._get_env("DATABASE_PATH", "assets/db_bot.db"),
                timeout=int(self._get_env("DATABASE_TIMEOUT", "30")),
            )

            # Feature configuration
            features_config = FeatureConfig(
                auto_ban_enabled=self._get_bool("AUTO_BAN_ENABLED", True),
                captcha_enabled=self._get_bool("CAPTCHA_ENABLED", True),
                antispam_enabled=self._get_bool("ANTISPAM_ENABLED", True),
            )

            # Logging configuration
            logging_config = LogConfig(
                level=self._get_env("LOG_LEVEL", "INFO"),
                file_path=self._get_env("LOG_FILE", "bot.log"),
            )

            # Create main config
            self.config = BotConfig(
                telegram=telegram_config,
                chat=chat_config,
                database=database_config,
                features=features_config,
                logging=logging_config,
                debug=self._get_bool("DEBUG", False),
                owner_id=int(self._get_env("OWNER_ID", "5579729798")),
            )

            # Validate
            if not self.config.validate():
                raise ValueError("Configuration validation failed")

            logger.info(f"Configuration loaded (version {self.config.version})")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        """Get environment variable with default"""
        value = os.getenv(key, default)
        if not value and not default:
            logger.warning(f"Missing environment variable: {key}")
        return value

    @staticmethod
    def _get_bool(key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def get_config(self) -> BotConfig:
        """Get loaded configuration"""
        if not self.config:
            return self.load()
        return self.config


# Global config instance
_config_instance: Optional[BotConfig] = None


def get_config(reload: bool = False) -> BotConfig:
    """Get or load global configuration"""
    global _config_instance

    if reload or not _config_instance:
        loader = ConfigLoader()
        _config_instance = loader.load()

    return _config_instance
