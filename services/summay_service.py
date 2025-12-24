# Add this import at the top
from services.azure_openai_service import azure_openai_service

# Add this method to the MeetingService class
class SummaryService:
    def generate_summary(self, transcript: str) -> str:
        """
        Generate a structured 3-paragraph summary from meeting transcript
        
        Args:
            transcript: The conversation transcript
        
        Returns:
            Formatted summary with 3 sections
        """
        system_prompt = """You are an expert financial advisor assistant who summarizes client meetings.

    Your task is to generate a concise, professional summary with exactly 3 paragraphs following these headers:
    1. Meeting Objective
    2. Client Situation
    3. Goals

    Format requirements:
    - Each section should be exactly ONE paragraph (3-5 sentences)
    - Use clear, professional language
    - Focus on key points only
    - Do NOT use markdown formatting (no **, ##, etc.)
    - Separate sections with a blank line

    Return as plain text in this exact format:

    Meeting Objective
    [One paragraph describing the purpose and context of the meeting]

    Client Situation
    [One paragraph describing the client's current circumstances, financial status, and life situation]

    Goals
    [One paragraph describing what the client wants to achieve]"""
        
        user_prompt = f"""Generate a 3-paragraph summary for the following meeting transcript:

    {transcript}

    Remember: Plain text format, no markdown, exactly 3 paragraphs with the headers shown."""
        
        summary = azure_openai_service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=800
        )
        
        return summary.strip()