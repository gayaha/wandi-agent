import os
from dotenv import load_dotenv

load_dotenv()

# Airtable
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "app8393BIwz7tRlR9")

# Table IDs
TABLE_CLIENTS = "tblVUTKss5rnmH1P9"
TABLE_MAGNETS = "Magnets"
TABLE_VIRAL_HOOKS = "viral hooks"
TABLE_VIRAL_CONTENT_POOL = "Viral Content Pool"
TABLE_RTM_EVENTS = "RTM Events"
TABLE_REEL_TEMPLATES = "Reel Templates"
TABLE_CONTENT_QUEUE = "Content Queue"
TABLE_CLIENT_STYLE_BANK = "Client Style Bank"
TABLE_GLOBAL_INSIGHTS = "Global Insights"

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "glm4:latest")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "rendered-videos")
SUPABASE_SOURCE_BUCKET = os.getenv("SUPABASE_SOURCE_BUCKET", "source-videos")

# Remotion renderer service
REMOTION_SERVICE_URL = os.getenv("REMOTION_SERVICE_URL", "http://localhost:3000")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
