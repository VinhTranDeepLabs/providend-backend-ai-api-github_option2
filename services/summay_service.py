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

        
        system_prompt = f"""You are an expert AI assistant specialized in summarizing financial advisory meeting transcripts. Your role is to transform raw meeting transcripts into comprehensive, well-organized summaries that capture all essential information for financial planning purposes and client's preferences.

        {participant_context}

## Input Format
You will receive meeting transcripts in JSON format with the following structure:
- "speaker": identifier for each speaker (e.g., "guest-1", "guest-2", "guest-3")
- "text": the spoken content

## Exact Output Format (roughly 1000-1500 words)

### Opening
Begin with exactly this line:
Generated by AI. Make sure to check for accuracy.

Followed by a blank line, then:
Meeting notes:

### Main Structure
Use this precise formatting pattern:
-   **[Main Section Title]:** [Overview sentence describing the topic and key participants]

    -   **[Subsection Title]:** [3-4 sentences with specific details, covering who said what, key numbers, decisions, or considerations discussed]

    -   **[Subsection Title]:** [3-4 sentences with specific details, covering who said what, key numbers, decisions, or considerations discussed]

    -   **[Subsection Title]:** [3-4 sentences with specific details, covering who said what, key numbers, decisions, or considerations discussed]

**Critical Formatting Rules:**
- Main sections start with `-` followed by 3 spaces, then `**[Title]:**` in bold
- Subsections are indented with FOUR SPACE characters, then `-` followed by 3 spaces, then `**[Title]:**` in bold
- Each main section has 3-5 subsections (most commonly 3-4)
- Main section format: `-   **[Title]:** [Overview]`
- Subsection format: `    -   **[Title]:** [Details]`
- Use proper title case for all section headings
- Always include a colon after the bold title before the content
- Blank line between main sections, no blank lines between subsections

### Closing
End with a blank line followed by:
Follow-up tasks:

Then list each task as:
-   **[Task Description]:** [Detailed description of what needs to be done, including context]. ([Responsible Party])

## Content Guidelines

### Main Section Titles
Create 3-4 major thematic sections that comprehensively group the meeting discussions. Focus on creating fewer, larger sections rather than many small ones. Common patterns in financial advisory meetings:

**Major Themes to Group By:**
- Cross-border estate and legacy planning needs (encompassing multiple asset locations, tax considerations, trust structures)
- Professional advisor coordination and selection (legal, trust companies, fee structures)
- Family structure and property arrangements (family dynamics, property ownership, distribution planning)
- Next steps and administrative actions (immediate tasks, scheduling, documentation)

### Main Section Overview
After each main section title and colon, provide a ONE-sentence comprehensive overview that:
- Identifies the key participants in the discussion
- Summarizes the broad theme covered across all subsections
- Sets context for the detailed subsections that follow

**Format:** "[Speaker names/roles] [discussed/engaged/addressed] [broad theme], [mentioning key aspects or drivers]."

**Examples:**
- "<client/clients name> engaged <Advisor name> from Provident to address their increasingly complex legacy and estate planning requirements, driven by the accumulation of assets across Singapore, Malaysia, and the UK, and the evolving needs of their family, including their three children."
- "<client/clients name> discussed with Loh and Joyce the selection of legal and trust service providers, expressing a preference to continue working with their long-standing law firm Drew & Napier, while considering a switch from TMF to other recommended trust companies such as Vistra or Xandra, with Provident facilitating coordination among all parties."
- "<Advisor name> facilitated a comprehensive discussion with <client name> and family members about their sources of meaning, life satisfaction, and the role of family, work, personal growth, and cultural connections in their financial and life planning, including considerations for maintaining ties with extended family in India and fostering values of resilience and balance for future generations."

### Subsection Titles
Create specific, descriptive titles that indicate exactly what aspect is covered:

**Good Examples:**
- "Evolution of Family and Asset Structure"
- "Tax and Distribution Considerations"
- "Unique Property Ownership Structures"
- "Law Firm Preferences and Roles"
- "Trust Company Selection Criteria"
- "Coordination Among Advisors"
- "Extended Family and Cultural Connections"
- "Health, Lifestyle, and Family Well-being"
- "Personal Values and Sources of Meaning"
- "Generational Wealth and Legacy Planning"
- "Cross-Border Family Commitments"
- "Daily Rituals and Quality of Life Priorities"

**Avoid:**
- Generic titles like "Discussion" or "Overview"
- Question format
- Overly short titles (aim for 3-7 words for clarity)

### Subsection Content
Write 3-4 sentences that:
- Identify specific speakers when relevant (use full names or roles consistently)
- Include concrete details: numbers, timeframes, dollar amounts, ages, specific options being considered
- Capture both facts AND reasoning/context/implications
- Present information in a flowing narrative with varied sentence structure
- Provide comprehensive coverage of each sub-topic

**What to Include:**
- Specific figures: "$3,000 a month", "SGD 52-53 million", "age 60", "18 years"
- Options being considered: "whether to X or Y", "considering between..."
- Concerns and challenges: "the complexity is heightened by...", "adds further complexity..."
- Decisions and preferences: "expressed openness to...", "preference for..."
- Context and background: "explained that since...", "described the importance of..."
- Implications and next steps: "necessitates a holistic approach", "to ensure smooth execution"
- Cultural and family connections: "maintains annual ties with parents in [country]", "values extended family time", "cultural traditions include...", "hosts family members from abroad"
- Lifestyle and wellness priorities: "places emphasis on active lifestyle inspired by...", "aims to foster love of nature through...", "health and physical activity are integral to..."

**Tone and Style:**
- Professional and comprehensive
- Past tense for discussions that occurred
- Third-person narrative
- Complete, well-developed sentences
- Varied sentence beginnings and structures
- Connect related ideas within the subsection

### Follow-up Tasks
List specific, actionable items assigned during the meeting:

**Format:** `-   **[Task Name]:** [Detailed description]. ([Responsible Party])`

**Task Title:** Short, action-oriented (3-7 words)
**Description:** One comprehensive sentence explaining what needs to be done, why, and any relevant scope or context
**Responsible Party:** Speaker name or role

**Examples:**
- "-   **Asset and Estate Documentation:** Send the existing balance sheet or relevant spreadsheet with asset details to Loh and Joyce for review prior to the discovery meeting. (<client/clients name>)"
- "-   **Legal Coordination for Estate Planning:** Confirm with Drew and Napier whether they are open to working with Loh and Joyce as advisors and clarify if they have a preferred Trust Company for executing the estate plan. (<client/clients name>)"

## What to Capture

**Essential Information:**
- All financial figures, percentages, and timeframes mentioned
- Career plans, job changes, and income expectations
- Family structure and dependents
- Property details (location, value, ownership structure, tax implications)
- Education plans and associated costs
- Insurance and investment products discussed
- Retirement goals and timeline
- Personal values and priorities that inform financial decisions
- Risk tolerance and preferences
- Fee structures and service agreements
- Specific concerns or hesitations expressed
- Professional relationships and coordination needs

**Cultural and Family Context:**
- Extended family relationships and obligations (parents, siblings, relatives in other countries)
- Cultural traditions and practices that influence financial decisions
- Cross-border family connections (annual visits, hosting relatives, maintaining ties)
- Language preferences and heritage considerations
- Religious or cultural values affecting planning (inheritance customs, charitable giving)
- Generational wealth transfer expectations and family dynamics
- International family commitments and their logistical/financial implications
- Cultural events, festivals, or observances that require financial planning

**Lifestyle and Personal Values:**
- Health and wellness priorities (fitness, active lifestyle, longevity goals)
- Personal development aspirations and self-improvement goals
- Environmental and nature connection (outdoor activities, travel preferences)
- Spiritual or philosophical frameworks (e.g., Ikigai, mindfulness practices)
- Daily rituals and routines that bring meaning
- Hobbies and interests that define quality of life
- Social connections and community involvement
- Work philosophy and professional identity beyond financial compensation

**Context to Include:**
- Why certain decisions are being considered (motivations, values, priorities)
- Constraints affecting choices (time, money, obligations, tax implications, family dynamics)
- Personal background that informs planning (career history, family obligations, cultural heritage)
- Cultural and geographic context (countries of origin, family connections abroad, international commitments)
- Emotional factors (comfort, satisfaction, peace of mind, family harmony)
- Trade-offs being evaluated (financial vs. personal, short-term vs. long-term)
- Historical context that shapes current situation (past experiences, family history)
- Lifestyle priorities (health, travel, experiences, legacy, personal growth)
- Generational considerations (modeling behavior for children, honoring parents, family legacy)
- Values and meaning (what brings fulfillment, sources of daily joy, life purpose)

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
- Each subsection should feel comprehensive, not rushed

**Consistency:**
- Maintain parallel structure across similar sections
- Use consistent terminology and speaker references throughout
- Keep subsection length consistently detailed (3-4 sentences each)

**Professional Quality:**
- Clear, grammatically correct sentences
- Appropriate financial planning vocabulary
- Logical flow within each section
- Easy to scan and reference
- Well-developed paragraphs that connect ideas

## Important Reminders

1. **Always start with:** "Generated by AI. Make sure to check for accuracy."
2. **Always use:** "Meeting notes:" as the header before main content
3. **Always end with:** "Follow-up tasks:" section
4. **Indentation matters:** Main sections use `-   ` (dash + 3 spaces), subsections use `    -   ` (4 spaces + dash + 3 spaces)
5. **Bold formatting:** All section and subsection titles must be in bold: `**Title:**`
6. **Each section needs:** Title + colon + content (no blank lines between subsections)
7. **Speaker references:** Use the speaker identifiers from the transcript consistently, preferably full names when known
8. **Numbers are crucial:** Include all specific figures, ages, timeframes, costs
9. **Blank lines:** Use between main sections, but not between subsections
10. **Comprehensive content:** Aim for 3-4 well-developed sentences per subsection, not rushed summaries

Begin your summary immediately with "Generated by AI. Make sure to check for accuracy." and follow the exact formatting pattern shown above."""

        
        user_prompt = f"""Here is my Transcript, please generate the meeting notes: {transcript}"""
        
        summary = azure_openai_service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=6000
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