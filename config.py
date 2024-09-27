import os
from pathlib import Path

# Server configuration
DEFAULT_PORT = 8000
DEFAULT_CACHE_DURATION = 3600  # 1 hour

# Cache configuration
CACHE_DIR = Path('cache')
CACHE_DIR.mkdir(exist_ok=True)

# CORS configuration
ALLOWED_ORIGINS = ['*']  # Consider making this more restrictive
ALLOWED_METHODS = ['GET', 'POST', 'OPTIONS']
ALLOWED_HEADERS = ['X-Requested-With', 'Content-Type', 'Authorization']

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()