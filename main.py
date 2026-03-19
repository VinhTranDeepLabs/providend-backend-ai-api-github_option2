import os
import psycopg2
from backup import network
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import login, question_analysis, meeting, question_template, advisor, client, summarization, transcript, process, feedback, chat
import uvicorn

# Load environment variables
load_dotenv()

def create_connection():
    """Create a database connection to Azure PostgreSQL"""
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT", "5432"),
            sslmode="prefer"
        )
        print("✓ Successfully connected to PostgreSQL database")
        return connection
    except Exception as e:
        print(f"✗ Error connecting to PostgreSQL: {e}")
        return None


app = FastAPI(
    title="Azure AI Gateway API",
    description="API Gateway for Azure OpenAI and Speech Services",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(",") if "," in os.getenv("CORS_ORIGINS", "") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(login.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(question_analysis.router, prefix="/api/v1/question", tags=["Question Analysis"])
app.include_router(meeting.router, prefix="/api/v1/meeting", tags=["Meetings"])
app.include_router(question_template.router, prefix="/api/v1/template", tags=["Question Templates"])
app.include_router(advisor.router, prefix="/api/v1/advisor", tags=["Advisors"])
app.include_router(client.router, prefix="/api/v1/client", tags=["Clients"])
app.include_router(transcript.router, prefix="/api/v1/transcript", tags=["Transcripts"])
app.include_router(process.router, prefix="/api/v1/process", tags=["Process"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])

app.include_router(summarization.router, prefix="/api/v1", tags=["Summarization"])

@app.get("/")
async def root():
    return {
        "message": "Bearies AI Gateway is running",
        "status": "online",
        "version": "1.0.0"
    }


@app.on_event("startup")
def _startup_db():
    """Create a shared DB connection and attach it to app.state.db_conn.

    Uses `create_connection()` defined above. If connection fails we keep
    running but log a warning; routes depending on `app.state.db_conn` will
    raise the RuntimeError you saw until the environment is configured.
    """
    conn = create_connection()
    if conn is None:
        print("Warning: DB connection unavailable on startup (app.state.db_conn not set)")
    app.state.db_conn = conn


@app.on_event("shutdown")
def _shutdown_db():
    conn = getattr(app.state, "db_conn", None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)