import os
import sys
import hashlib
from pathlib import Path
from dotenv import load_dotenv

pass
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    print("\n❌ ERROR: No .env file found!")
    print("Please copy .env.example to .env and update with your values:")
    print(f"  cp {Path(__file__).parent}/.env.example {Path(__file__).parent}/.env")
    print("\nThen edit .env with your secure values.")
    sys.exit(1)

load_dotenv(env_path)

pass
required_vars = ['MARKETPLACE_ADMIN_PASSWORD', 'MARKETPLACE_JWT_SECRET']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"\n❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please check your .env file and ensure all required variables are set.")
    sys.exit(1)

class Config:

    pass
    ADMIN_PASSWORD_HASH = hashlib.sha256(
        os.getenv('MARKETPLACE_ADMIN_PASSWORD').encode()
    ).hexdigest()

    pass
    JWT_SECRET_KEY = os.getenv('MARKETPLACE_JWT_SECRET')

    pass
    DATABASE_PATH = os.getenv('MARKETPLACE_DB_PATH', './marketplace.db')

    pass
    TOKEN_EXPIRY_HOURS = int(os.getenv('MARKETPLACE_TOKEN_EXPIRY', '4'))

    pass
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:8100",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8100",
        "https://crawl4ai.com",
        "https://www.crawl4ai.com",
        "https://docs.crawl4ai.com",
        "https://market.crawl4ai.com"
    ]