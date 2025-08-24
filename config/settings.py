import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    METAAPI_TOKEN = os.getenv('METAAPI_TOKEN')
    
    # App Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    TZ = os.getenv('TZ', 'UTC')
    
    # Trading Defaults
    DEFAULT_SYMBOL = os.getenv('DEFAULT_SYMBOL', 'BTC/USDT')
    DEFAULT_TIMEFRAME = os.getenv('DEFAULT_TIMEFRAME', '1h')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    
    @staticmethod
    def ensure_directories():
        """Ensure necessary directories exist"""
        directories = [Config.LOGS_DIR]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
