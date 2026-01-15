# Add this import at the top
from services.azure_openai_service import azure_openai_service
from utils.db_utils import DatabaseUtils

# Update the SummaryService class
class SummaryService:
    def generate_summary(self, transcript: str, meeting_id: str = None, 
                        created_by: str = "AI_PROCESSOR", conn=None) -> str:
        """
        Generate a structured 3-paragraph summary from meeting transcript
        AND create version 1 if this is first summary generation
        
        Args:
            transcript: The conversation transcript
            meeting_id: Optional meeting ID to fetch participant names and create version
            created_by: Who generated the summary (default: AI_PROCESSOR)
            conn: Database connection
        
        Returns:
            Formatted summary with 3 sections
        """
        # Fetch participant names if meeting_id is provided
        participant_context = ""
        if meeting_id and conn:
            try:
                db = DatabaseUtils(conn)
                meeting = db.get_meeting(meeting_id)
                
                if meeting:
                    advisor_name = "the advisor"
                    client_name = "the client"
                    
                    # Get advisor name
                    if meeting.get("advisor_id"):
                        advisor = db.get_advisor(meeting["advisor_id"])
                        if advisor:
                            advisor_name = advisor.get("name", "the advisor")
                    
                    # Get client name
                    if meeting.get("client_id"):
                        client = db.get_client(meeting["client_id"])
                        if client:
                            client_name = client.get("name", "the client")
                    
                    participant_context = f"""
                    IMPORTANT: The participants in this meeting are:
                    - Advisor: {advisor_name}
                    - Client: {client_name}

                    When writing the summary, you need to analyze the transcript of a meeting that will be given to you to understand who is the advisor and who is the client. 
                    If there is a 3rd or 4th guest, identify their role as well and name them accordingly based on transcript if possible, else use Client 2, client 3.
                    Use these actual names instead of generic labels like "Guest-1", "Guest-2", "the advisor", or "the client". For example:
                    - Instead of "The advisor explained...", write "{advisor_name} explained..."
                    - Instead of "The client mentioned...", write "{client_name} mentioned..."
                    """
                    
            except Exception as e:
                print(f"Warning: Could not fetch participant names: {e}")
                participant_context = ""

        
        system_prompt = f"""You are a professional meeting summarization assistant for Providend, a financial advisory firm. Your role is to generate comprehensive, well-structured meeting summaries from transcript data.

        {participant_context}

        OUTPUT FORMAT

        Your summary must follow this exact two-part structure:

        Part 1: Meeting Notes
        - Organize content into hierarchical topics with descriptive titles
        - Use this format: "Main Topic Title: [Brief context sentence introducing the discussion]"
        - Include 2-4 subtopics under each main topic
        - Subtopic format: "Subtopic Title: [Detailed explanation of what was discussed]"

        Part 2: Follow-up Tasks
        - List all action items identified during the meeting
        - Format: "Task Title: [Detailed description of the task.] (Assignee Name)"
        - Always include the assignee in parentheses

        CONTENT REQUIREMENTS

        Comprehensiveness:
        - Capture ALL significant discussion points, not just highlights
        - Include specific numbers, dates, amounts, percentages, and named entities (people, companies, products)
        - Document both the "what" (facts discussed) and the "why" (reasoning, implications, considerations)
        - Preserve the relationship and flow between related topics

        Level of Detail:
        - Each subtopic should be 2-4 sentences minimum
        - Include specific examples, scenarios, or options that were discussed
        - Document preferences, concerns, and decision-making rationale
        - Capture explanations of concepts or processes that were covered

        Participant Attribution:
        - Use the actual participant names provided above throughout the summary
        - Maintain clarity about who provided advice vs. who asked questions
        - Document which advisor is responsible for specific follow-up actions
        - NEVER use generic labels like "Guest-1", "Guest-2", "the advisor", or "the client"

        Contextual Information:
        - Include relevant background information that explains current decisions
        - Note any existing arrangements or previous engagements mentioned
        - Document family structure, asset locations, or other context that informs planning

        WRITING STYLE

        - Tone: Professional, objective, third-person perspective
        - Tense: Past tense for completed discussions
        - Sentence Structure: Complete, well-formed sentences (no bullet points in the body)
        - Precision: Use exact figures and specific terminology mentioned in the meeting
        - Clarity: Ensure someone who wasn't in the meeting can understand the full context

        TOPIC ORGANIZATION

        Group related discussions under logical main topics such as:
        - Planning goals and timelines (retirement, estate, etc.)
        - Financial analysis (income, expenses, assets)
        - Product recommendations (insurance, investments, accounts)
        - Legal and administrative matters
        - Family and beneficiary considerations
        - Professional coordination (lawyers, trust companies, other advisors)
        - Next steps and process

        Within each main topic:
        - Start with overview/context
        - Progress through specific details and considerations
        - End with conclusions or recommendations

        FOLLOW-UP TASKS

        - Extract every action item mentioned during the meeting
        - Be specific about what needs to be done, not just the category
        - Include enough context so the assignee knows exactly what's expected
        - Always specify the assignee (using their actual name)
        - Order tasks logically (by urgency, by topic, or by assignee)

        EXAMPLE STRUCTURE

        Meeting notes:

        Main Topic Title: Context sentence introducing this area of discussion, including who initiated it and basic parameters.

        Subtopic Title: Detailed explanation of what was discussed, including specific details like amounts, dates, names, and reasoning. Continues to provide context about implications, options considered, or decisions made.

        Another Subtopic Title: More detailed discussion points with attribution to participants (using their actual names), specific numbers or examples, and any explanations provided during the meeting.

        Another Main Topic: Introduction to this discussion area with context.

        [Continue pattern...]

        Follow-up tasks:

        Task Description Title: Detailed explanation of what needs to be done, including relevant context and any specific parameters mentioned. (Assignee Name)

        [Continue for all action items...]"""

        
        user_prompt = f"""Here is my Transcript, please generate the meeting notes: {transcript}"""
        
        summary = azure_openai_service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=800
        )
        
        summary_text = summary.strip()
        
        # If meeting_id provided, save to meeting_details and create version 1
        if meeting_id and conn:
            try:
                from utils.db_utils import DatabaseUtils
                db = DatabaseUtils(conn)
                
                # Check if summary already exists
                details = db.get_meeting_detail(meeting_id)
                
                if not details or not details.get("summary"):
                    # First time - save and create v1
                    db.update_meeting_detail(meeting_id=meeting_id, summary=summary_text)
                    db.create_content_version(
                        meeting_id=meeting_id,
                        content_type='summary',
                        content=summary_text,
                        created_by=created_by
                    )
            except Exception as e:
                print(f"Warning: Could not save summary version: {e}")
        
        return summary_text