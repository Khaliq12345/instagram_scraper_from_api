from dotenv import load_dotenv
import os

load_dotenv()

RAPID_API_KEY = os.getenv("RAPID_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
APP_KEY = os.getenv("APP_KEY")

SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
