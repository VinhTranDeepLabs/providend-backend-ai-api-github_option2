# Providend Backend AI API

A FastAPI-based backend service powering **Bearies AI** — an intelligent meeting assistant platform for financial advisors. The system provides automated meeting transcription, AI-powered summarization, question analysis, and product recommendations.

## Features

### Core Capabilities

- **Meeting Management** — Create, track, and manage client-advisor meetings with full lifecycle support
- **Audio Transcription** — Batch transcription with speaker diarization via Azure Speech Services
- **AI Summarization** — Structured meeting summaries with thematic grouping and follow-up tasks
- **Question Analysis** — Automated question tracking and answer extraction from transcripts
- **Product Recommendations** — AI-driven financial product suggestions based on client conversations
- **Chat Assistant** — Context-aware chat interface for querying meeting content
- **Version Control** — Track changes to transcripts and summaries with rollback support

### Technical Features

- RESTful API with automatic OpenAPI documentation
- Microsoft Entra ID (Azure AD) authentication
- Background processing for async transcription and meeting analysis
- PostgreSQL database with comprehensive schema
- Azure Blob Storage integration for audio files

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | FastAPI 0.109.0 |
| Runtime | Python 3.10+ |
| Database | PostgreSQL (Azure) |
| AI Services | Azure OpenAI (GPT-4) |
| Speech | Azure Speech Services |
| Storage | Azure Blob Storage |
| Auth | Microsoft Entra ID |
| Server | Uvicorn / Gunicorn |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Routers                                                         │
│  ├── /api/v1/auth      → Authentication (SSO)                   │
│  ├── /api/v1/meeting   → Meeting CRUD & transcript management   │
│  ├── /api/v1/advisor   → Advisor profiles & statistics          │
│  ├── /api/v1/client    → Client profiles & portfolios           │
│  ├── /api/v1/transcript→ Audio upload & transcription           │
│  ├── /api/v1/question  → Question analysis & tracking           │
│  ├── /api/v1/process   → Summary generation                     │
│  ├── /api/v1/chat      → Meeting chat assistant                 │
│  ├── /api/v1/feedback  → User feedback collection               │
│  └── /api/v1/template  → Question templates                     │
├─────────────────────────────────────────────────────────────────┤
│  Services Layer                                                  │
│  ├── azure_openai_service  → GPT completions & JSON responses   │
│  ├── transcription_service → Batch transcription & diarization  │
│  ├── meeting_service       → Meeting operations & versioning    │
│  ├── question_service      → Autofill & tracking                │
│  ├── summary_service       → AI summarization                   │
│  ├── product_service       → Recommendation engine              │
│  └── chat_service          → Conversational AI                  │
├─────────────────────────────────────────────────────────────────┤
│  Background Processors                                           │
│  ├── background_batch_transcribe.py  → Audio file monitoring    │
│  └── background_meeting_processor.py → Post-meeting analysis    │
└─────────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database
- Azure account with:
  - Azure OpenAI Service
  - Azure Speech Services
  - Azure Blob Storage
  - Azure Entra ID (for authentication)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/deeeplabs/providend-backend-ai-api.git
   cd providend-backend-ai-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   # Development
   uvicorn main:app --reload --port 8001

   # Production
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
   ```

### Environment Variables

```env
# Database
DB_HOST=your-postgres-host.postgres.database.azure.com
DB_NAME=providend_db
DB_USER=admin_user
DB_PASSWORD=your_secure_password
DB_PORT=5432

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Azure Speech Services
AZURE_SPEECH_KEY=your_speech_key
AZURE_SPEECH_REGION=southeastasia

# Azure Blob Storage
BLOB_ACCOUNT_NAME=your_storage_account
BLOB_CONTAINER_NAME=audio-files
BLOB_ACCOUNT_KEY=your_storage_key

# Azure Entra ID
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_REDIRECT_URI=http://localhost:8001/api/v1/auth/callback

# Application
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=["http://localhost:3000"]
ENVIRONMENT=development
```

## API Documentation

Once running, access the interactive API docs at:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/meeting/create` | Create a new meeting |
| `POST` | `/api/v1/meeting/{id}/end` | End meeting & aggregate transcripts |
| `POST` | `/api/v1/transcript/upload-audio/{id}` | Upload audio for transcription |
| `GET` | `/api/v1/transcript/batch-transcribe/status/{id}` | Check transcription status |
| `POST` | `/api/v1/process/{id}/summary` | Generate AI summary |
| `POST` | `/api/v1/question/autofill` | Extract answers from transcript |
| `POST` | `/api/v1/chat/meeting/{id}/message` | Send chat message |
| `GET` | `/api/v1/advisor/{id}/meetings` | Get advisor's meetings (paginated) |

## Background Services

### Audio Monitor (`background_batch_transcribe.py`)

Monitors Azure Blob Storage for new audio files and automatically transcribes them.

```bash
python background_batch_transcribe.py
```

**Features:**
- Polls blob storage every 5 seconds (configurable)
- Automatic language detection (English/Chinese)
- Speaker diarization (up to 10 speakers)
- Retry failed transcriptions
- Saves transcripts to `transcript_aggregator` table

### Meeting Processor (`background_meeting_processor.py`)

Processes completed meetings with AI analysis.

```bash
python background_meeting_processor.py
```

**Features:**
- Auto-identifies speakers from meeting context
- Generates question autofill from transcripts
- Creates product recommendations
- Exponential backoff for retries (30s, 60s, 120s)
- Concurrent task execution with asyncio

## Project Structure

```
providend-backend-ai-api/
├── main.py                          # FastAPI application entry point
├── requirements.txt                 # Python dependencies
├── background_batch_transcribe.py   # Audio transcription service
├── background_meeting_processor.py  # Meeting analysis service
├── config/
│   ├── settings.py                  # Environment configuration
│   ├── questions.py                 # Question templates (TCP)
│   └── product.py                   # Product decision tree
├── models/
│   └── schemas.py                   # Pydantic models
├── routers/
│   ├── meeting.py                   # Meeting endpoints
│   ├── transcript.py                # Transcription endpoints
│   ├── question_analysis.py         # Question analysis endpoints
│   ├── advisor.py                   # Advisor management
│   ├── client.py                    # Client management
│   ├── chat.py                      # Chat endpoints
│   ├── process.py                   # Processing endpoints
│   ├── feedback.py                  # Feedback endpoints
│   ├── login.py                     # Authentication
│   └── question_template.py         # Template endpoints
├── services/
│   ├── azure_openai_service.py      # OpenAI integration
│   ├── transcription_service.py     # Speech-to-text
│   ├── meeting_service.py           # Meeting business logic
│   ├── question_service.py          # Question analysis
│   ├── summay_service.py            # Summary generation
│   ├── product_service.py           # Recommendations
│   ├── chat_service.py              # Chat functionality
│   ├── advisor_service.py           # Advisor operations
│   ├── client_service.py            # Client operations
│   └── auth_service.py              # Authentication
├── utils/
│   ├── db_utils.py                  # Database operations
│   ├── blob_utils.py                # Blob storage utilities
│   ├── audio_utils.py               # Audio processing
│   └── token.py                     # JWT validation
├── tests/
│   └── evaluate/
│       └── summary_eval.py          # DeepEval test suite
└── .github/
    └── workflows/
        └── main_backend-providend-ai-dev-qadujv.yml  # CI/CD
```

## Database Schema

The application uses PostgreSQL with the following core tables:

| Table | Purpose |
|-------|---------|
| `advisors` | Financial advisor profiles |
| `clients` | Client profiles with advisor relationships |
| `meetings` | Meeting records with status tracking |
| `meeting_details` | Transcripts, summaries, recommendations |
| `transcript_aggregator` | Individual transcript segments |
| `content_versions` | Version history for transcripts/summaries |
| `processed_audio_files` | Audio processing status tracking |
| `chats` / `messages` | Chat conversation history |
| `feedback` | User feedback entries |

## Development

### Running Tests

```bash
# Run evaluation tests
python -m pytest tests/

# Run specific evaluation
python tests/evaluate/summary_eval.py
```

### Code Style

The project follows PEP 8 guidelines. Key conventions:
- Type hints for function parameters and returns
- Docstrings for all public functions
- Service layer pattern for business logic
- Dependency injection via FastAPI's `Depends()`

### Git Workflow

The repository uses a multi-environment branch strategy:
- `main` — Production deployments
- `uat` — User acceptance testing
- `dev` — Development and feature integration

## Deployment

### Azure App Service

The application is configured for Azure App Service deployment via GitHub Actions. The workflow automatically deploys on push to the `dev` branch.

### Environment Configuration

Ensure all environment variables are configured in Azure App Service Configuration settings.

### Health Check

```bash
curl http://your-app-url/
# Response: {"message": "Bearies AI Gateway is running", "status": "online", "version": "1.0.0"}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary — Deeeplabs Pte. Ltd. All rights reserved.

## Support

For issues and questions, contact the development team at Deeeplabs.

## Quick setup up guide:
1. Clone this repo
2. Ask for .env file
3. Login to frontend so that a Advisor ID will be generated for you
4. If not able to find Advisor ID let me know
5. Run main.py and access swagger page (localhost:8001/docs):
 - Create clinets for your adcisor ID (POST /api/v1/client/create)
6. Go back to UI and you should see clients assigned under your Advisor ID.
7. You can now start a meeting and access the other functionalities.
