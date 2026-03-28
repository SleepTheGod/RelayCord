import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBERS = os.getenv("TWILIO_NUMBERS", "").split(",")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
DATABASE_ENCRYPTION_KEY = os.getenv("DATABASE_ENCRYPTION_KEY").encode()
ALLOWED_ROLES = os.getenv("ALLOWED_ROLES", "").split(",")
MAX_CONCURRENT_CALLS = int(os.getenv("MAX_CONCURRENT_CALLS", 5))
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", 8765))
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "wss://your-domain.com/media-stream")
