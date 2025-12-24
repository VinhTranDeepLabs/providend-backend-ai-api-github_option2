# Azure AI Gateway API

A FastAPI-based API gateway for Azure OpenAI and Azure Speech Services with modular, reusable architecture.

## Features

- **Transcript Summarization**: Generate structured summaries with Azure OpenAI
- **Question Analysis**: Autofill preset questions and identify unanswered questions from transcripts
- **Batch Speech-to-Text**: Convert audio files to text with speaker diarization

## Project Structure

```
project/
├── main.py                          # FastAPI app initialization
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables (create this)
├── .env.example                    # Example environment file
├── README.md                       # This file
│
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Configuration & environment variables
│   └── questions.py                # Hardcoded preset questions
│
├── models/
│   ├── __init__.py
│   └── schemas.py                  # Pydantic models for requests/responses
│
├── services/
│   ├── __init__.py
│   ├── azure_openai_service.py    # Reusable Azure OpenAI logic
│   ├── question_service.py        # Question matching/analysis logic
│   └── speech_service.py          # Azure Speech Service logic
│
└── routers/
    ├── __init__.py
    ├── summarization.py           # Summarization endpoint
    ├── question_analysis.py       # Question analysis endpoints
    └── speech_to_text.py          # Speech-to-text endpoint
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory with your Azure credentials (use `.env.example` as template):

```env
AZURE_OPENAI_ENDPOINT="your-endpoint"
AZURE_OPENAI_API_KEY="your-key"
AZURE_OPENAI_API_VERSION="2025-01-01-preview"
AZURE_OPENAI_DEPLOYMENT="gpt-4.1"

AZURE_SPEECH_KEY="your-speech-key"
AZURE_SPEECH_REGION="eastus"
```

### 3. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Summarize Transcript
**POST** `/api/v1/summarize`

```json
{
  "transcript": "Your transcript text here..."
}
```

**Response:**
```json
{
  "summary": "Formatted summary with sections",
  "key_points": ["Point 1", "Point 2"],
  "success": true
}
```

### 2. Autofill Questions
**POST** `/api/v1/autofill-questions`

```json
{
  "transcript": "Your transcript text here..."
}
```

**Response:**
```json
{
  "answered_questions": [
    {
      "question": "What is your current occupation?",
      "answer": "Software Engineer",
      "confidence": "high"
    }
  ],
  "success": true
}
```

### 3. Get Unanswered Questions
**POST** `/api/v1/unanswered-questions`

```json
{
  "transcript": "Your transcript text here..."
}
```

**Response:**
```json
{
  "unanswered_questions": [
    "Do you have any existing insurance coverage?",
    "What is your annual income?"
  ],
  "total_unanswered": 2,
  "success": true
}
```

### 4. Batch Transcribe
**POST** `/api/v1/batch-transcribe`

```json
{
  "audio_urls": [
    "https://your-storage.blob.core.windows.net/audio/file1.wav",
    "https://your-storage.blob.core.windows.net/audio/file2.wav"
  ],
  "language": "en-US"
}
```

**Response:**
```json
{
  "results": [
    {
      "audio_url": "https://...",
      "transcript": "Full transcript text",
      "speaker_segments": [
        {
          "speaker": "Speaker 1",
          "text": "Hello, how are you?",
          "start_time": 0.5,
          "end_time": 2.3
        }
      ],
      "language": "en-US",
      "duration": 120.5
    }
  ],
  "total_files": 1,
  "success": true
}
```

## Interactive API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Customization

### Modify Preset Questions

Edit `config/questions.py` to update the hardcoded questions list:

```python
PRESET_QUESTIONS = [
    "Your custom question 1?",
    "Your custom question 2?",
    # Add more questions...
]
```

### Adjust Summary Template

Edit the `SUMMARY_TEMPLATE` in `routers/summarization.py` to customize the output format.

## Architecture Highlights

- **Separation of Concerns**: Routers handle HTTP, services contain business logic
- **Reusability**: Services can be called from multiple endpoints
- **Type Safety**: Pydantic models for request/response validation
- **Configuration**: Centralized settings with environment variable validation
- **Error Handling**: Comprehensive exception handling with meaningful error messages

## Requirements

- Python 3.9+
- Azure OpenAI account with GPT-4 deployment
- Azure Speech Services subscription
- Audio files must be publicly accessible URLs for batch transcription

## Notes

- The batch transcription endpoint uses Azure's Batch Transcription API v3.1
- Audio files must be accessible via HTTPS URLs (e.g., Azure Blob Storage with SAS tokens)
- Supported audio formats: WAV, MP3, OGG, FLAC
- The API automatically enables speaker diarization for speech-to-text