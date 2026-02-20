# Providend Backend AI API

A FastAPI-based backend service powering **Bearies AI** — an intelligent meeting assistant platform for financial advisors. The system provides automated meeting transcription, AI-powered summarization, question analysis, product recommendations, and a conversational chat assistant.

## Features

### Core Capabilities

- **Meeting Management** — Full lifecycle support: create, track, end, and delete meetings. Supports both standard and quick-create (no client assigned) flows.
- **Audio Transcription** — Batch transcription with speaker diarization via Azure Speech Services. Background audio monitor auto-detects new uploads and transcribes them.
- **Speaker Identification** — AI-powered speaker identification that maps generic labels (Guest-1, Speaker 1) to real participant names using meeting context.
- **AI Summarization** — Structured meeting summaries with thematic grouping, follow-up tasks, and speaker attribution. Summaries are generated with detailed context from the product decision tree.
- **Question Analysis** — Automated question tracking and answer extraction from transcripts. Supports autofill, unanswered question detection, and section-based tracking across configurable templates.
- **Product Recommendations** — AI-driven financial product suggestions based on a decision tree covering protection needs and wealth accumulation strategies.
- **Chat Assistant** — Context-aware chat interface for querying meeting content. Each meeting maintains its own chat session with full history.
- **Version Control** — Track changes to transcripts and summaries with full version history, side-by-side comparison, and rollback support.
- **Question Templates** — CRUD management for question templates with section-based organization, pagination, and runtime refresh into the application config.
- **Feedback System** — Collect and manage user feedback per meeting with categorization support.

### Technical Features

- RESTful API with automatic OpenAPI/Swagger documentation
- Microsoft Entra ID (Azure AD) SSO authentication with JWKS token validation
- Background processing services for async transcription and post-meeting analysis
- PostgreSQL database with comprehensive relational schema
- Azure Blob Storage integration for audio file uploads
- Exponential backoff retry logic for failed processing tasks
- Optimistic locking to prevent duplicate meeting processing
- Paginated endpoints with search, filtering, and sorting
- Content versioning with unified edit timeline

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | FastAPI 0.109.0 |
| Runtime | Python 3.10+ |
| Database | PostgreSQL (Azure) |
| AI Services | Azure OpenAI (GPT-4) |
| Speech | Azure Speech Services |
| Storage | Azure Blob Storage |
| Auth | Microsoft Entra ID (SSO + JWKS) |
| Server | Uvicorn / Gunicorn |
| ORM/DB | psycopg2 (raw SQL) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Routers                                                         │
│  ├── /api/v1/auth        → SSO login, token verification        │
│  ├── /api/v1/meeting     → Meeting CRUD, transcript management  │
│  │                         version control, question tracker     │
│  ├── /api/v1/advisor     → Advisor profiles, statistics,        │
│  │                         paginated meetings                    │
│  ├── /api/v1/client      → Client profiles, portfolios,        │
│  │                         product management                    │
│  ├── /api/v1/transcript  → Audio upload, batch transcription,   │
│  │                         speaker identification                │
│  ├── /api/v1/question    → Autofill, tracking, recommendations  │
│  ├── /api/v1/process     → Summary generation                   │
│  ├── /api/v1/chat        → Meeting chat assistant               │
│  ├── /api/v1/feedback    → User feedback collection             │
│  └── /api/v1/template    → Question template CRUD               │
├─────────────────────────────────────────────────────────────────┤
│  Services Layer                                                  │
│  ├── azure_openai_service  → GPT completions & JSON responses   │
│  ├── transcription_service → Batch transcription, diarization,  │
│  │                           speaker identification              │
│  ├── meeting_service       → Meeting ops, versioning, diffing   │
│  ├── question_service      → Autofill, tracking, sync           │
│  ├── summary_service       → AI summarization with templates    │
│  ├── product_service       → Decision tree recommendations      │
│  ├── chat_service          → Conversational AI with context     │
│  ├── advisor_service       → Advisor CRUD, SSO user management  │
│  ├── client_service        → Client CRUD, portfolio management  │
│  ├── feedback_service      → Feedback CRUD                      │
│  ├── auth_service          → OAuth2 flows, token handling       │
│  └── question_template_service → Template CRUD, config refresh  │
├─────────────────────────────────────────────────────────────────┤
│  Background Processors                                           │
│  ├── background_batch_transcribe.py  → Blob storage monitor     │
│  │   Polls for new audio files, transcribes via Azure Speech,   │
│  │   saves to transcript_aggregator. Retries failed files.      │
│  └── background_meeting_processor.py → Post-meeting analysis    │
│      Auto-identifies speakers, runs question autofill,          │
│      generates product recommendations. Exponential backoff.    │
├─────────────────────────────────────────────────────────────────┤
│  Utilities                                                       │
│  ├── db_utils       → All database operations (CRUD, versions)  │
│  ├── blob_utils     → Azure Blob Storage helpers                │
│  ├── audio_utils    → Audio file processing                     │
│  └── token          → JWT/JWKS token validation                 │
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
   # Edit .env with your configuration (see Environment Variables below)
   ```

5. **Run the application**
   ```bash
   # Development
   uvicorn main:app --reload --port 8001

   # Production
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
   ```

### Quick Setup Guide

1. Clone this repo
2. Ask for `.env` file
3. Login to the frontend so that an Advisor ID will be generated for you
4. If not able to find Advisor ID, let the team know
5. Run `main.py` and access the Swagger page (`localhost:8001/docs`):
   - Create clients for your Advisor ID (`POST /api/v1/client/create`)
6. Go back to the UI and you should see clients assigned under your Advisor ID
7. You can now start a meeting and access the other functionalities

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

# Background Processors (optional)
AUDIO_MONITOR_INTERVAL=5
PROCESSOR_POLL_INTERVAL=15
PROCESSOR_MAX_RETRIES=3
PROCESSOR_BATCH_SIZE=10
PROCESSOR_BACKOFF_BASE=30
```

## API Documentation

Once running, access the interactive API docs at:
- **Swagger UI**: `http://localhost:8001/docs`

### Key Endpoints

#### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/sso` | SSO login with Microsoft Entra ID token |
| `GET` | `/api/v1/auth/verify` | Verify access token validity |
| `POST` | `/api/v1/auth/dev-login` | Dev-only bypass for testing |

#### Meetings
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/meeting/create` | Create a new meeting |
| `POST` | `/api/v1/meeting/quick-create` | Create meeting without client |
| `POST` | `/api/v1/meeting/{id}/end` | End meeting & aggregate transcripts |
| `GET` | `/api/v1/meeting/{id}` | Get full meeting details |
| `PATCH` | `/api/v1/meeting/{id}/summary` | Update summary (auto-versions) |
| `PATCH` | `/api/v1/meeting/{id}/transcript` | Update transcript (auto-versions) |
| `PATCH` | `/api/v1/meeting/{id}/client` | Assign client to meeting |
| `GET` | `/api/v1/meeting/{id}/versions/timeline` | Unified edit timeline |

#### Transcription
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/transcript/upload-audio/{id}` | Upload audio for transcription |
| `GET` | `/api/v1/transcript/batch-transcribe/status/{id}` | Check transcription status |
| `POST` | `/api/v1/transcript/{id}/identify-speakers` | AI speaker identification |
| `POST` | `/api/v1/transcript/{id}/apply-speaker-mapping` | Apply speaker name mapping |

#### Question Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/question/autofill` | Extract answers from transcript |
| `POST` | `/api/v1/question/recommend` | Get unanswered question recommendations |
| `POST` | `/api/v1/question/tracker` | Track answered questions by section |
| `POST` | `/api/v1/question/sync-tracker/{id}` | Sync questions to tracker format |

#### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat/meeting/{id}/message` | Send message & get AI response |
| `POST` | `/api/v1/chat/meeting/{id}/new` | Start new chat session |
| `GET` | `/api/v1/chat/meeting/{id}/messages` | Get chat history |

#### Advisors & Clients
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/advisor/{id}/meetings` | Paginated meetings with search/filter |
| `GET` | `/api/v1/advisor/{id}/statistics` | Advisor dashboard statistics |
| `GET` | `/api/v1/client/{id}/recommendations` | Client recommendation history |
| `GET` | `/api/v1/client/{id}/products` | Client product portfolio |

#### Question Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/template/all` | List templates (paginated) |
| `POST` | `/api/v1/template/` | Create new template |
| `PUT` | `/api/v1/template/{id}` | Full replace template |
| `DELETE` | `/api/v1/template/{id}` | Delete template |

## Background Services

### Audio Monitor (`background_batch_transcribe.py`)

Monitors Azure Blob Storage for new audio files and automatically transcribes them.

```bash
python background_batch_transcribe.py
```

**How it works:**
- Polls blob storage every 5 seconds (configurable via `AUDIO_MONITOR_INTERVAL`)
- Parses filenames in format: `<meeting_id>_<YYYY-MM-DD HH-MM-SS+00>.extension`
- Supports `.wav` and `.webm` audio formats
- Transcribes using Azure Speech Services batch API with speaker diarization (up to 5 speakers)
- Saves transcripts to `transcript_aggregator` table
- Tracks processed files in `processed_audio_files` table
- Automatically retries failed transcriptions (failed status files are re-queued)
- Graceful shutdown on SIGINT/SIGTERM

### Meeting Processor (`background_meeting_processor.py`)

Processes completed meetings with AI analysis.

```bash
python background_meeting_processor.py
```

**How it works:**
- Polls for meetings with `status='Completed'` and `processing_status='pending'`
- Uses optimistic locking to prevent duplicate processing across instances
- Processing pipeline per meeting:
  1. Auto-identifies speakers (replaces generic labels with real names)
  2. Runs question autofill from transcript
  3. Generates product recommendations
- Exponential backoff for retries: 30s → 60s → 120s (configurable)
- Max 3 retry attempts before marking as permanently failed
- Concurrent task execution with asyncio
- Graceful shutdown on SIGINT/SIGTERM

## Project Structure

```
providend-backend-ai-api/
├── main.py                          # FastAPI app entry point, DB startup, router registration
├── requirements.txt                 # Python dependencies
├── background_batch_transcribe.py   # Audio transcription background service
├── background_meeting_processor.py  # Meeting analysis background service
├── config/
│   ├── settings.py                  # Environment config & validation
│   ├── questions.py                 # Question templates (TCP), CATEGORIZED_QUESTIONS
│   └── product.py                   # Product recommendation decision tree
├── models/
│   └── schemas.py                   # Pydantic request/response models
├── routers/
│   ├── login.py                     # SSO authentication endpoints
│   ├── meeting.py                   # Meeting CRUD, transcript segments, versioning
│   ├── transcript.py                # Audio upload, batch transcribe, speaker ID
│   ├── question_analysis.py         # Autofill, recommend, tracker endpoints
│   ├── question_template.py         # Template CRUD with pagination
│   ├── process.py                   # Summary generation endpoint
│   ├── advisor.py                   # Advisor CRUD, paginated meetings, stats
│   ├── client.py                    # Client CRUD, products, portfolio
│   ├── chat.py                      # Chat session management
│   └── feedback.py                  # Feedback CRUD
├── services/
│   ├── azure_openai_service.py      # Azure OpenAI client (completions, JSON mode)
│   ├── transcription_service.py     # Speech-to-text, speaker identification
│   ├── meeting_service.py           # Meeting logic, diff tracking, versioning
│   ├── question_service.py          # Question autofill, tracking, sync
│   ├── summay_service.py            # AI summary generation
│   ├── product_service.py           # Decision tree recommendations
│   ├── chat_service.py              # Chat with meeting context
│   ├── advisor_service.py           # Advisor ops, SSO user management
│   ├── client_service.py            # Client ops, portfolio management
│   ├── feedback_service.py          # Feedback operations
│   ├── auth_service.py              # OAuth2 flows, token handling
│   ├── login_service.py             # (Reserved)
│   └── question_template_service.py # Template CRUD, config refresh
├── utils/
│   ├── db_utils.py                  # All database operations
│   ├── blob_utils.py                # Azure Blob Storage utilities
│   ├── audio_utils.py               # Audio file processing
│   └── token.py                     # JWT/JWKS token validation
├── backup/
│   ├── network.py                   # Network connectivity check endpoint
│   └── network_service.py           # Internet connection checker
├── tests/
│   ├── test_chat_service.py         # Chat service tests
│   ├── test_client.py               # Client tests
│   ├── test_db.py                   # Database tests
│   ├── test_sql.py                  # SQL tests
│   └── evaluate/
│       ├── test_chatbot_eval.py     # Chatbot evaluation
│       └── test_summary_eval.py     # Summary evaluation (DeepEval)
└── .github/
    └── workflows/
        └── main_backend-providend-ai-dev-qadujv.yml  # CI/CD pipeline
```

## Database Schema

The application uses PostgreSQL with the following core tables:

| Table | Purpose |
|-------|---------|
| `advisors` | Financial advisor profiles (SSO-linked via OID) |
| `clients` | Client profiles with advisor FK relationships |
| `meetings` | Meeting records with status, type, and processing tracking |
| `meeting_details` | Transcripts, summaries, recommendations, questions, notes, tracker |
| `transcript_aggregator` | Individual transcript segments (pre-aggregation) |
| `content_versions` | Version history for transcripts and summaries |
| `processed_audio_files` | Audio file processing status tracking |
| `chats` | Chat sessions per meeting (soft-deletable) |
| `messages` | Chat message history (user + bot) |
| `feedback` | User feedback entries per meeting |
| `question_templates` | Configurable question template definitions |
| `template_sections` | Sections within question templates |
| `template_questions` | Individual questions within sections |
| `client_products` | Client-product portfolio relationships |

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run evaluation tests
python tests/evaluate/test_summary_eval.py
python tests/evaluate/test_chatbot_eval.py
```

### Code Conventions

- Type hints for function parameters and returns
- Docstrings for all public functions
- Service layer pattern for business logic separation
- Dependency injection via FastAPI's `Depends()` for DB connections
- Raw SQL via psycopg2 (no ORM)
- JSON serialization for complex fields stored in PostgreSQL

### Git Workflow

| Branch | Purpose |
|--------|---------|
| `prod` | Production deployments (Not Created Yet)|
| `uat` | User acceptance testing |
| `main` | Development and feature integration |

## Deployment

### Azure App Service

The application is configured for Azure App Service deployment via GitHub Actions. The workflow automatically deploys on push to the `dev` branch.

Ensure all environment variables are configured in Azure App Service Configuration settings.

### Health Check

```bash
curl http://your-app-url/
# Response: {"message": "Bearies AI Gateway is running", "status": "online", "version": "1.0.0"}
```

## License

Proprietary — Deeeplabs Pte. Ltd. All rights reserved.

## Support

For issues and questions, contact the development team at Deeeplabs.