from fastapi import APIRouter, HTTPException
from models.schemas import TranscriptRequest, SummaryResponse, ErrorResponse
from services.azure_openai_service import azure_openai_service
import json

router = APIRouter()

SUMMARY_TEMPLATE = """
Please provide a comprehensive summary of the transcript in the following format:

**Executive Summary**
[2-3 sentence overview of the main discussion]

**Key Discussion Points**
- [Main point 1]
- [Main point 2]
- [Main point 3]
[Add more points as needed]

**Important Details**
- [Notable detail 1]
- [Notable detail 2]
[Add more details as needed]

**Action Items / Next Steps**
- [Action item 1]
- [Action item 2]
[If any were mentioned]

**Overall Tone/Sentiment**
[Brief description of the conversation tone]
"""

@router.post("/summarize", response_model=SummaryResponse, responses={500: {"model": ErrorResponse}})
async def summarize_transcript(request: TranscriptRequest):
    """
    Summarize a transcript using Azure OpenAI with a structured template
    
    - **transcript**: The text transcript to summarize
    """
    try:
        system_prompt = f"""You are an expert at analyzing and summarizing conversation transcripts.
Your task is to create a comprehensive, well-structured summary following the template provided.

Use the following template structure:
{SUMMARY_TEMPLATE}

Guidelines:
- Be concise but comprehensive
- Extract all key information accurately
- Highlight actionable items if present
- Return the response as a JSON object with fields: "summary" (full formatted summary) and "key_points" (array of main points)
"""
        
        user_prompt = f"""Please summarize the following transcript:

{request.transcript}

Provide a structured summary following the template format."""
        
        response = azure_openai_service.generate_json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5
        )
        
        return SummaryResponse(
            summary=response.get("summary", ""),
            key_points=response.get("key_points", []),
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )