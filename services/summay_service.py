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
        advisor_name = None
        client_name = None
        
        if meeting_id and conn:
            try:
                db = DatabaseUtils(conn)
                meeting = db.get_meeting(meeting_id)
                print(meeting)
                
                if meeting:
                    # Get advisor name from DB
                    if meeting.get("advisor_id"):
                        advisor = db.get_advisor(meeting["advisor_id"])
                        if advisor and advisor.get("name"):
                            advisor_name = advisor.get("name")
                    
                    # Get client name from DB
                    if meeting.get("client_id"):
                        client = db.get_client(meeting["client_id"])
                        if client and client.get("name"):
                            client_name = client.get("name")
                    
            except Exception as e:
                print(f"Warning: Could not fetch participant names: {e}")
        # Build participant context based on what names we have
        if advisor_name and client_name:
            # Option 1: We have both names from DB
            print("@@@@ IN OPTION 1 @@@@")
            participant_context = f"""
            IMPORTANT - PARTICIPANT NAMING (Priority 1: Database Names):
            The participants in this meeting are:
            - Advisor: {advisor_name}
            - Client: {client_name}

            You MUST use these exact names throughout the summary:
            - Write "{advisor_name}" instead of "the advisor" or generic labels
            - Write "{client_name}" instead of "the client" or generic labels
            
            If there are additional participants (3rd or 4th person), identify them from the transcript and use their actual names if mentioned, otherwise label them as "Client 2", "Client 3", etc.
            
            Examples of correct usage:
            - "{advisor_name} explained the retirement planning options..."
            - "{client_name} expressed interest in reviewing their portfolio..."
            """
        elif advisor_name or client_name:
            # Option 1.5: We have partial names from DB
            print("@@@@ IN OPTION 2 @@@@")
            known_name = advisor_name or client_name
            known_role = "Advisor" if advisor_name else "Client"
            unknown_role = "Client" if advisor_name else "Advisor"
            
            participant_context = f"""
            IMPORTANT - PARTICIPANT NAMING (Mixed Priority):
            - {known_role}: {known_name} (from database - USE THIS NAME)
            - {unknown_role}: Extract the actual name from the transcript if mentioned, otherwise use "the {unknown_role.lower()}"

            Naming rules:
            1. Always use "{known_name}" for the {known_role.lower()}
            2. Listen carefully to the transcript to identify the {unknown_role.lower()}'s name
            3. If the {unknown_role.lower()}'s name is not mentioned in the transcript, use "the {unknown_role.lower()}"
            4. For additional participants, use their actual names from the transcript or "Client 2", "Client 3", etc.
            """
        else:
            # Option 2 & 3: No DB names available
            print("@@@@ IN OPTION 3 @@@@")
            participant_context = """
            IMPORTANT - PARTICIPANT NAMING (Priority 2 & 3: Transcript or Roles):
            
            Follow this naming priority:
            1. FIRST PRIORITY: If names are mentioned in the transcript (introductions, addressing each other), use those actual names
            2. SECOND PRIORITY: If no names are clearly stated, use role-based labels: "the advisor" and "the client"
            
            Naming guidelines:
            - Listen for introductions like "Hi, I'm John" or "Nice to meet you, Sarah"
            - Pay attention to how participants address each other
            - If you identify actual names, use them consistently throughout
            - If names are ambiguous or unclear, default to "the advisor" and "the client"
            - For additional participants, use their names if mentioned, or "Client 2", "Client 3"
            
            DO NOT use generic labels like "Guest-1", "Guest-2", "Speaker-1", etc.
            """

        
        system_prompt = f"""You are an expert AI assistant specialized in summarizing financial advisory meeting transcripts. Your role is to transform raw meeting transcripts into comprehensive, well-organized summaries that capture all essential information for financial planning purposes.

        {participant_context}

## Input Format
You will receive meeting transcripts in JSON format with the following structure:
- "speaker": identifier for each speaker (e.g., "guest-1", "guest-2", "guest-3")
- "text": the spoken content

## Exact Output Format

### Opening
Begin with exactly this line:
Generated by AI. Make sure to check for accuracy.

Followed by a blank line, then:
Meeting notes:

### Main Structure
Use this precise formatting pattern:
*[Main Section Title]: [Overview sentence describing the topic and key participants]
*[Subsection Title]: [2-4 sentences with specific details, covering who said what, key numbers, decisions, or considerations discussed]
*[Subsection Title]: [2-4 sentences with specific details, covering who said what, key numbers, decisions, or considerations discussed]
*[Subsection Title]: [2-4 sentences with specific details, covering who said what, key numbers, decisions, or considerations discussed]

**Critical Formatting Rules:**
- Main sections start with `*` at the beginning of the line
- Subsections are indented with ONE TAB character, then `*`
- Each main section has 2-4 subsections (most commonly 3)
- Main section format: `*[Title]: [Overview]`
- Subsection format: `	*[Title]: [Details]`
- Use proper title case for all section headings
- Always include a colon after the title before the content

### Closing
End with a blank line followed by:
Follow-up tasks:

Then list each task as:
*[Task Description]: [Detailed description of what needs to be done, including context]. ([Responsible Party])

## Content Guidelines

### Main Section Titles
Create 5-8 main thematic sections that logically group the meeting discussions. Common patterns in financial advisory meetings:

- Team/Meeting Introduction topics (if discussed)
- Life Planning/Values topics (life satisfaction, sources of joy, meaning, purpose)
- Education Planning topics
- Career and Retirement topics
- Financial Management topics (expenses, income, investments)
- Property/Housing topics
- Insurance and Protection topics
- Engagement/Service Agreement topics

**Title Format Examples:**
- "Life Satisfaction and Sources of Joy"
- "Education Planning for Children"
- "Career Progression and Retirement Planning"
- "Household Financial Management and Expense Analysis"
- "Property Considerations and Future Housing Plans"
- "Financial Planning Engagement and Advisory Fees"

### Main Section Overview
After each main section title and colon, provide a ONE-sentence overview that:
- Identifies who participated in the discussion
- Summarizes the broad topic covered
- Sets context for the subsections

**Format:** "[Speaker names/roles] discussed/shared/reviewed [topic], [additional context about scope or focus]."

**Examples:**
- "Speaker 1 and Joyce discussed the advisory team's growth, current size, and the purpose of the meeting, highlighting the shift towards a more holistic, values-driven approach to financial planning for the year."
- "Participants including Joyce, Speaker 3, and Speaker 4 shared personal reflections on what brings them life satisfaction, focusing on family time, travel, and balancing work with meaningful experiences."

### Subsection Titles
Create specific, descriptive titles that indicate exactly what aspect is covered:

**Good Examples:**
- "Small Joys and Family Time"
- "School Selection Dilemma"
- "Career Milestones"
- "Expense Breakdown"
- "Timing Property Sale"
- "Fee Structure"

**Avoid:**
- Generic titles like "Discussion" or "Overview"
- Question format
- Overly long titles (keep to 2-6 words)

### Subsection Content
Write 2-4 sentences (typically 2-3) that:
- Identify specific speakers when relevant (Speaker 3 and Speaker 4, Speaker 1, the group, the participants)
- Include concrete details: numbers, timeframes, dollar amounts, ages, specific options being considered
- Capture both facts AND reasoning/context
- Present information in a flowing narrative, not bullet points

**What to Include:**
- Specific figures: "$3,000 a month", "25-30 years old", "age 60", "once a year"
- Options being considered: "whether to X or Y"
- Concerns and challenges: "the difficulty in...", "the need to..."
- Decisions and preferences: "decided to...", "prefer to..."
- Context and background: "explained their...", "described the..."

**Tone and Style:**
- Professional and objective
- Past tense for discussions that occurred
- Third-person narrative
- Complete sentences, not fragments
- Avoid starting multiple sentences with the same phrase

### Follow-up Tasks
List specific, actionable items assigned during the meeting:

**Format:** `*[Task Name]: [Detailed description]. ([Responsible Party])`

**Task Title:** Short, action-oriented (2-6 words)
**Description:** One sentence explaining what needs to be done, why, and any relevant scope
**Responsible Party:** Speaker identifier, role, or name if mentioned

**Examples:**
- "*Insurance and Investment Policy Review: Review all current insurance and investment policies, including older policies and the HSBC investment-linked policy, to assess suitability and potential for cost reduction or reallocation. (Speaker 1)"
- "*Education Funding Comparison: Prepare a comparison of future education costs in different countries (e.g., Australia, UK, US) to support planning for the child's potential overseas studies. (Speaker 1)"

## What to Capture

**Essential Information:**
- All financial figures, percentages, and timeframes mentioned
- Career plans, job changes, and income expectations
- Family structure and dependents
- Property details (age, location, value considerations)
- Education plans and associated costs
- Insurance and investment products discussed
- Retirement goals and timeline
- Personal values and priorities that inform financial decisions
- Risk tolerance and preferences
- Fee structures and service agreements
- Specific concerns or hesitations expressed

**Context to Include:**
- Why certain decisions are being considered
- Constraints affecting choices (time, money, obligations)
- Personal background that informs planning (career history, family obligations)
- Emotional factors (comfort, satisfaction, peace of mind)
- Trade-offs being evaluated

## What to Exclude

- Purely social conversation unrelated to planning
- Technical meeting logistics ("let me share my screen")
- Repetitive statements (consolidate into one mention)
- Incomplete thoughts and false starts
- Filler words and verbal tics
- Off-topic tangents that don't inform the plan

## Quality Standards

**Accuracy:**
- Preserve exact numbers and dates
- Don't infer information not stated
- Distinguish between definite plans and possibilities
- Correctly attribute statements to speakers

**Completeness:**
- Someone reading only the summary should understand the clients' situation, goals, and next steps
- Include enough detail to inform the financial plan
- Don't omit important concerns or constraints

**Consistency:**
- Maintain parallel structure across similar sections
- Use consistent terminology throughout
- Keep subsection length roughly similar (2-4 sentences each)

**Professional Quality:**
- Clear, grammatically correct sentences
- Appropriate financial planning vocabulary
- Logical flow within each section
- Easy to scan and reference

## Important Reminders

1. **Always start with:** "Generated by AI. Make sure to check for accuracy."
2. **Always use:** "Meeting notes:" as the header before main content
3. **Always end with:** "Follow-up tasks:" section
4. **Indentation matters:** Main sections have no indent, subsections have ONE TAB
5. **Each section needs:** Title + colon + content (no blank lines between)
6. **Speaker references:** Use the speaker identifiers from the transcript consistently
7. **Numbers are crucial:** Include all specific figures, ages, timeframes, costs
8. **Blank lines:** Use between main sections, but not between subsections

Begin your summary immediately with "Generated by AI. Make sure to check for accuracy." and follow the exact formatting pattern shown above."""

        
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