import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Azure Speech Configuration
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# Azure Entra ID (AAD) Configuration
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", "http://localhost:8001/api/v1/auth/callback")

# Frontend URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Validate required environment variables
def validate_config():
    required_vars = {
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
        "AZURE_OPENAI_API_VERSION": AZURE_OPENAI_API_VERSION,
        "AZURE_OPENAI_DEPLOYMENT": AZURE_OPENAI_DEPLOYMENT,
        "AZURE_SPEECH_KEY": AZURE_SPEECH_KEY,
        "AZURE_SPEECH_REGION": AZURE_SPEECH_REGION,
        "AZURE_TENANT_ID": AZURE_TENANT_ID,
        "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
        "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
    }
    
    missing_vars = [key for key, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Run validation on import
validate_config()