from services.azure_openai_service import azure_openai_service
from config.questions import PRESET_QUESTIONS, CATEGORIZED_QUESTIONS
from models.schemas import QuestionAnswer
from typing import List, Dict, Any, Optional
from utils.db_utils import DatabaseUtils
import json

class QuestionService:
    def __init__(self):
        self.preset_questions = PRESET_QUESTIONS

    def autofill_questions(self, template_name: str, transcript: str, meeting_id: str = None, conn=None) -> List[QuestionAnswer]:
        """
        Analyze transcript and extract answers for preset questions.
        Uses the aggregated transcript from meeting_details (Option A).
        
        Args:
            template_name: The name of the question template to use
            transcript: The conversation transcript (can be passed directly or retrieved from meeting)
            meeting_id: Optional meeting ID associated with the transcript
            conn: Database connection

        Returns:
            Tuple of (answered_questions, unanswered_questions)
        """
        # If meeting_id is provided and transcript is empty, try to fetch from meeting_details
        if meeting_id and not transcript:
            transcript = self._fetch_transcript_from_meeting(meeting_id, conn)
            if not transcript:
                raise ValueError(f"No transcript found for meeting_id: {meeting_id}. Please run aggregation first.")
        
        questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(self.preset_questions[template_name])])
        
        system_prompt = """You are an expert at analyzing conversation transcripts and extracting information.
        Your task is to read the transcript and identify answers to specific questions.

        For each question:
        - If the answer is clearly stated in the transcript, extract the relevant answer
        - If the answer is partially stated, extract what is available
        - If the question was not addressed at all, set the answer to null
        - Provide a confidence level: "high", "medium", or "low" based on how clearly the question was answered

        Return the results as a JSON object with the following structure:
        {
            "questions": [
                {
                    "question": "original question text",
                    "answer": "extracted answer or null",
                    "confidence": "high/medium/low or null"
                }
            ]
        }"""
        
        user_prompt = f"""Analyze the following transcript and extract answers to these questions:

        Questions:
        {questions_str}

        Transcript:
        {transcript}

        Provide the extracted answers in JSON format."""
        
        response = azure_openai_service.generate_json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )
        
        # Convert to QuestionAnswer objects
        question_answers = []
        question_unanswered = []
        for item in response.get("questions", []):
            if item.get("answer"):
                question_answers.append(QuestionAnswer(
                    question=item.get("question"),
                    answer=item.get("answer"),
                    confidence=item.get("confidence")
                ))
            else:
                question_unanswered.append(item.get("question"))

        # Save autofilled answers to database if meeting_id is provided
        # (This can be implemented later to store in meeting_details.questions field)
        
        return question_answers, question_unanswered
    
    def get_unanswered_questions(self, question_template_name: str, transcript: str, 
                                num_of_recommendations: int, meeting_id: str = None, conn=None) -> List[str]:
        """
        Identify which preset questions were not answered in the transcript.
        Uses the aggregated transcript from meeting_details (Option A).
        
        Args:
            question_template_name: The question template to analyze for recommending questions
            transcript: The conversation transcript (can be passed directly or retrieved from meeting)
            num_of_recommendations: Number of recommended questions to return
            meeting_id: Optional meeting ID to retrieve transcript from
            conn: Database connection
            
        Returns:
            List of questions that were not answered
        """
        # If meeting_id is provided and transcript is empty, try to fetch from meeting_details
        if meeting_id and not transcript:
            transcript = self._fetch_transcript_from_meeting(meeting_id, conn)
            if not transcript:
                raise ValueError(f"No transcript found for meeting_id: {meeting_id}. Please run aggregation first.")
        
        questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(self.preset_questions[question_template_name])])
        
        system_prompt = """You are an expert at analyzing conversation transcripts.
        Your task is to determine which questions from a preset list were NOT answered or discussed in the transcript.

        A question is considered "unanswered" if:
        - It was never asked in the conversation
        - It was asked but not answered
        - The answer provided was incomplete or unclear

        Return the results as a JSON object with the following structure:
        {
            "unanswered_questions": [
                "question text 1",
                "question text 2"
            ]
        }

        Only include the exact question text from the original list."""
        
        user_prompt = f"""Analyze the following transcript and identify which questions were NOT answered:

        Questions to check:
        {questions_str}

        Transcript:
        {transcript}

        Number of recommendations to return: {num_of_recommendations}

        Please make sure that the recommended questions are indeed unanswered and recommend the next {num_of_recommendations} unanswered questions sequentially.

        Provide the list of unanswered questions in JSON format."""
        
        response = azure_openai_service.generate_json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )
        
        return response.get("unanswered_questions", [])

    def track_questions(self, template_name: str, transcript: str, meeting_id: str = None, conn=None) -> Dict[str, Dict[str, bool]]:
        """
        Track which questions were answered in the transcript, organized by sections.
        
        Args:
            template_name: The question template name to use
            transcript: The conversation transcript (can be passed directly or retrieved from meeting)
            meeting_id: Optional meeting ID to retrieve transcript from
            conn: Database connection
        
        Returns:
            Dictionary with sections as keys, and question:boolean pairs as values
        """
        # If meeting_id is provided and transcript is empty, try to fetch from meeting_details
        if meeting_id and not transcript:
            transcript = self._fetch_transcript_from_meeting(meeting_id, conn)
            if not transcript:
                raise ValueError(f"No transcript found for meeting_id: {meeting_id}. Please run aggregation first.")
        
        # Get categorized questions for this template
        if template_name not in CATEGORIZED_QUESTIONS:
            raise ValueError(f"Template '{template_name}' not found in CATEGORIZED_QUESTIONS")
        
        categorized_questions = CATEGORIZED_QUESTIONS[template_name]
        
        # Build the prompt with all questions organized by section
        sections_str = ""
        for section, questions in categorized_questions.items():
            sections_str += f"\n{section}:\n"
            for i, q in enumerate(questions, 1):
                sections_str += f"  {i}. {q}\n"
        
        system_prompt = """You are an expert at analyzing conversation transcripts.
        Your task is to determine which questions from each section were answered or discussed in the transcript.

        A question is considered "answered" (true) if:
        - The sementics of the question was asked and answered
        - The topic was discussed in the conversation

        A question is considered "unanswered" (false) if:
        - It was never discussed
        - It was asked but not answered

        Return the results as a JSON object with sections as keys, and question:boolean pairs as values:
        {
            "section 1 - values": {
                "What is important to you about money?": true,
                "What is the role of money in your life?": false
            },
            "section 2 - goals": {
                ...
            }
        }

        Include ALL questions from ALL sections with their answered status (true/false)."""
        
        user_prompt = f"""Analyze the following transcript and determine which questions were answered in each section:

        Questions organized by sections:
        {sections_str}

        Transcript:
        {transcript}"""
        
        response = azure_openai_service.generate_json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )
        
        return response
    

    def _fetch_transcript_from_meeting(self, meeting_id: str, conn=None) -> Optional[str]:
        """
        Helper method to retrieve aggregated transcript from meeting_details.
        Uses Option A: retrieves from meeting_details.transcript field.
        
        Args:
            meeting_id: The meeting ID
            conn: Database connection
        
        Returns:
            Aggregated transcript string or None
        """
        if conn is None:
            return None
        
        try:
            db = DatabaseUtils(conn)
            
            # Get meeting details
            meeting_details = db.get_meeting_detail(meeting_id)
            
            if not meeting_details:
                return None
            
            transcript = meeting_details.get("transcript")
            
            # If no transcript in meeting_details, try to aggregate from segments
            if not transcript:
                transcript = db.aggregate_transcripts(meeting_id)
                
                # Save aggregated transcript to meeting_details for future use
                if transcript:
                    db.update_meeting_detail(meeting_id=meeting_id, transcript=transcript)
            
            return transcript
            
        except Exception as e:
            print(f"Error retrieving transcript for meeting {meeting_id}: {e}")
            return None