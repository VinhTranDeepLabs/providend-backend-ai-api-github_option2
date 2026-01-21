from datetime import datetime, timezone
import azure.cognitiveservices.speech as speechsdk
from config.settings import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
from models.schemas import TranscriptionResult, SpeakerSegment
from typing import List, Optional
from utils.db_utils import DatabaseUtils
from services.azure_openai_service import azure_openai_service
from fastapi import UploadFile, HTTPException, status
from utils.blob_utils import blob_storage_service
from dotenv import load_dotenv
import requests
import time
import json
import logging
import os

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meeting_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class TranscribeService:
    def __init__(self):
        self.speech_key = AZURE_SPEECH_KEY
        self.speech_region = AZURE_SPEECH_REGION
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )

    
    async def upload_audio_to_blob(
        self,
        meeting_id: str,
        audio_file: UploadFile,
        start_datetime: datetime = None
    ) -> dict:
        """
        Upload audio file to Azure Blob Storage with proper naming format
        
        Args:
            meeting_id: Meeting identifier
            audio_file: Uploaded audio file (WebM or WAV)
            start_datetime: Optional timestamp (defaults to NOW if not provided)
        
        Returns:
            Dict with upload result details
        """
        try:
            # 1. Validate file extension
            if not blob_storage_service.validate_audio_extension(audio_file.filename):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file type. Only .webm and .wav files are allowed."
                )
            
            # 2. Validate file size (300MB limit)
            MAX_FILE_SIZE = 300 * 1024 * 1024  # 300MB in bytes
            
            # Read file content
            file_content = await audio_file.read()
            file_size_bytes = len(file_content)
            
            if file_size_bytes > MAX_FILE_SIZE:
                file_size_mb = file_size_bytes / (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large ({file_size_mb:.1f}MB). Maximum allowed size is 300MB."
                )
            
            # 3. Set start_datetime to NOW if not provided
            if start_datetime is None:
                start_datetime = datetime.now(timezone.utc)
            
            # 4. Generate properly formatted blob name
            file_extension = os.path.splitext(audio_file.filename)[1].lstrip('.')
            blob_name = blob_storage_service.generate_audio_filename(
                meeting_id=meeting_id,
                start_datetime=start_datetime,
                extension=file_extension
            )
            
            logger.info(f"Uploading audio file: {blob_name} ({file_size_bytes / (1024 * 1024):.2f}MB)")
            
            # 5. Upload to blob storage (async, non-blocking I/O)
            blob_url = await blob_storage_service.upload_audio_file(
                file_content=file_content,
                blob_name=blob_name,
                overwrite=True
            )
            
            logger.info(f"✓ Upload successful: {blob_url}")
            
            # 6. Return success response
            return {
                "success": True,
                "message": "Audio file uploaded successfully",
                "blob_name": blob_name,
                "blob_url": blob_url,
                "meeting_id": meeting_id,
                "start_datetime": start_datetime.isoformat(),
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "file_extension": file_extension
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Error uploading audio file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload audio file: {str(e)}"
            )

    
    def format_timestamp(self, seconds):
        """Format seconds to HH:MM:SS"""
        seconds = int(seconds)
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    

    def batch_transcribe_urls(
        self,
        audio_urls: List[str],
        language: str = 'auto'
    ) -> List[TranscriptionResult]:
        """
        Transcribe audio files with speaker diarization

        Args:
            audio_urls: List of public URLs to audio files
            language: 'auto' for auto-detect, or specific locale like 'en-US', 'zh-CN', 'bn-IN'

        Returns:
            List of TranscriptionResult objects, one per audio file
        """

        base_url = f'https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2'
        transcriptions_url = f'{base_url}/transcriptions'

        headers = {
            'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY,
            'Content-Type': 'application/json'
        }

        # Configure language settings
        if language == 'auto':
            primary_locale = 'en-US'
            job_config = {
                'contentUrls': audio_urls,
                'properties': {
                    'diarizationEnabled': True,
                    'diarization': {
                        'speakers': {
                            'minCount': 1,
                            'maxCount': 10
                        }
                    },
                    'wordLevelTimestampsEnabled': True,
                    'punctuationMode': 'DictatedAndAutomatic',
                    'profanityFilterMode': 'Masked',
                    'languageIdentification': {
                        'candidateLocales': ['en-US', 'zh-CN'],
                        'mode': 'Continuous'
                    }
                },
                'locale': primary_locale,
                'displayName': f'Batch_Transcription_{int(time.time())}'
            }
        else:
            job_config = {
                'contentUrls': audio_urls,
                'properties': {
                    'diarizationEnabled': True,
                    'diarization': {
                        'speakers': {
                            'minCount': 1,
                            'maxCount': 10
                        }
                    },
                    'wordLevelTimestampsEnabled': True,
                    'punctuationMode': 'DictatedAndAutomatic',
                    'profanityFilterMode': 'Masked'
                },
                'locale': language,
                'displayName': f'Batch_Transcription_{int(time.time())}'
            }

        # Step 1: Create transcription job
        logger.info(f"Creating transcription job for: {audio_urls}")
        create_response = requests.post(transcriptions_url, headers=headers, json=job_config)

        if create_response.status_code != 201:
            raise Exception(f"Failed to create job: {create_response.text}")

        job_data = create_response.json()
        job_url = job_data['self']
        job_id = job_url.split('/')[-1]
        logger.info(f"Job created: {job_id}")

        # Step 2: Poll for completion
        max_wait_time = 600  # 10 minutes
        poll_interval = 5
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            time.sleep(poll_interval)
            elapsed_time += poll_interval

            status_response = requests.get(job_url, headers=headers)

            if status_response.status_code != 200:
                raise Exception(f"Failed to get status: {status_response.text}")

            job_status = status_response.json()
            status = job_status['status']

            logger.info(f"Status: {status} (elapsed: {elapsed_time}s)")

            if status == 'Succeeded':
                break
            elif status == 'Failed':
                error = job_status.get('properties', {}).get('error', {})
                raise Exception(f"Job failed: {error.get('message', 'Unknown error')}")
            elif status in ['NotStarted', 'Running']:
                continue

        if elapsed_time >= max_wait_time:
            raise Exception("Timeout: Job took longer than 10 minutes")

        # Step 3: Get all transcript files
        files_url = f"{job_url}/files"
        files_response = requests.get(files_url, headers=headers)

        if files_response.status_code != 200:
            raise Exception(f"Failed to get files: {files_response.text}")

        files_data = files_response.json()

        # Filter transcription files (one per audio URL)
        transcript_files = [f for f in files_data['values'] if f['kind'] == 'Transcription']

        if not transcript_files:
            raise Exception("No transcript files found")

        # Step 4: Process each transcript file
        results = []
        
        for transcript_file in transcript_files:
            transcript_url = transcript_file['links']['contentUrl']
            transcript_response = requests.get(transcript_url)

            if transcript_response.status_code != 200:
                logger.info(f"Warning: Failed to download transcript: {transcript_response.text}")
                continue

            transcript_json = transcript_response.json()
            
            # Extract source audio URL
            source_url = transcript_json.get('source', audio_urls[0] if len(audio_urls) == 1 else '')
            
            # Extract language
            detected_language = transcript_json.get('locale', language if language != 'auto' else 'en-US')
            
            # Step 5: Parse speaker segments
            speaker_segments = []
            transcript_lines = []
            max_end_time = 0.0

            if 'recognizedPhrases' in transcript_json:
                for phrase in transcript_json['recognizedPhrases']:
                    speaker_id = phrase.get('speaker', 0)
                    n_best = phrase.get('nBest', [])

                    if not n_best:
                        continue

                    best_result = n_best[0]
                    text = best_result.get('display', '')

                    if not text.strip():
                        continue

                    # Calculate start and end times
                    offset_ticks = phrase.get('offsetInTicks', 0)
                    duration_ticks = phrase.get('durationInTicks', 0)
                    
                    start_time = offset_ticks / 10_000_000  # Convert to seconds
                    end_time = (offset_ticks + duration_ticks) / 10_000_000
                    
                    max_end_time = max(max_end_time, end_time)

                    speaker_label = f"Speaker {speaker_id + 1}"

                    segment = SpeakerSegment(
                        speaker=speaker_label,
                        text=text,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    speaker_segments.append(segment)
                    transcript_lines.append(f"{speaker_label}: {text}")

            # Sort segments by start time
            speaker_segments.sort(key=lambda x: x.start_time if x.start_time else 0)

            # Create formatted transcript with speaker labels
            transcript = '\n'.join(transcript_lines)

            # Create TranscriptionResult
            result = TranscriptionResult(
                audio_url=source_url,
                transcript=transcript,
                speaker_segments=speaker_segments,
                language=detected_language,
                duration=max_end_time if max_end_time > 0 else None
            )
            
            results.append(result)

        # Step 6: Cleanup - delete job
        try:
            requests.delete(job_url, headers=headers)
            logger.info(f"Job {job_id} deleted")
        except:
            pass

        return results
        
    
    def aggregate_transcript(self, meeting_id: str, conn=None) -> str:
        """
        Aggregate transcript segments for a meeting into a single transcript.
        This uses the transcript stored in meeting_details (Option A).
        
        Args:
            meeting_id: The meeting ID
            conn: Database connection
        
        Returns:
            Aggregated transcript string
        """
        if conn is None:
            raise RuntimeError("DB connection not available")
        
        db = DatabaseUtils(conn)
        
        # Get meeting details which should have the aggregated transcript
        meeting_details = db.get_meeting_detail(meeting_id)
        
        if not meeting_details:
            raise ValueError(f"Meeting details not found for meeting_id: {meeting_id}")
        
        transcript = meeting_details.get("transcript")
        
        if not transcript:
            # If no transcript in meeting_details, try to aggregate from segments
            aggregated = db.aggregate_transcripts(meeting_id)
            
            if aggregated:
                # Save the aggregated transcript to meeting_details
                db.update_meeting_detail(meeting_id=meeting_id, transcript=aggregated)
                return aggregated
            else:
                raise ValueError(f"No transcript found for meeting_id: {meeting_id}")
        
        return transcript
    
    
    def get_transcript(self, meeting_id: str, conn=None) -> Optional[str]:
        """
        Retrieve the transcript for a specific meeting.
        This retrieves from meeting_details.transcript (Option A).
        
        Args:
            meeting_id: The meeting ID
            conn: Database connection
        
        Returns:
            Transcript string or None
        """
        if conn is None:
            raise RuntimeError("DB connection not available")
        
        db = DatabaseUtils(conn)
        
        # Get meeting details
        meeting_details = db.get_meeting_detail(meeting_id)
        
        if not meeting_details:
            return None
        
        return meeting_details.get("transcript")
    

    def identify_and_replace_speakers(self, transcript: str, meeting_id: str, conn) -> str:
        """
        Use LLM to identify speakers and replace generic labels with actual names/roles.
        
        Analyzes the conversation to determine:
        - Who is the advisor (asking questions, providing advice)
        - Who is the client (discussing personal finances, seeking help)
        - Additional clients (spouse, family members, etc.)
        - Extract actual names if mentioned in conversation
        
        Args:
            transcript: Raw transcript with generic speaker labels (Speaker 1, Speaker 2, etc.)
            meeting_id: Meeting ID to fetch advisor/client names as fallback
            conn: Database connection
        
        Returns:
            Cleaned transcript with meaningful speaker labels
        """
        try:
            # Get advisor and client names from database
            db = DatabaseUtils(conn)
            meeting = db.get_meeting(meeting_id)
            
            advisor_name = None
            client_name = None
            
            if meeting:
                if meeting.get("advisor_id"):
                    advisor = db.get_advisor(meeting["advisor_id"])
                    if advisor and advisor.get("name"):
                        advisor_name = advisor.get("name")
                
                if meeting.get("client_id"):
                    client = db.get_client(meeting["client_id"])
                    if client and client.get("name"):
                        client_name = client.get("name")

            # Reduce transcript only for identifying speakers
            transcript_list = json.loads(transcript)
            max_back_and_forth = int(os.getenv("PROCESSOR_TRANSCRIPT_IDNTIFY_LENGTH", 20))
            reduced_transcript = transcript_list[:max_back_and_forth]

            # Extract all unique speaker IDs from the full transcript to know how many speakers exist
            import re
            all_speaker_ids = set()
            for entry in transcript_list:
                if isinstance(entry, dict) and "speaker" in entry:
                    all_speaker_ids.add(entry["speaker"])
                elif isinstance(entry, str):
                    # If transcript is in string format with speaker labels
                    found_speakers = re.findall(r'(Guest-\d+|Speaker \d+)', entry)
                    all_speaker_ids.update(found_speakers)
            
            num_speakers = len(all_speaker_ids)
            logger.info(f"Detected {num_speakers} unique speakers in meeting {meeting_id}: {all_speaker_ids}")

            # Build system prompt based on available names
            if advisor_name and client_name:
                # Scenario A: Both names from database
                name_instructions = f"""
                NAME ASSIGNMENT - PRIORITY 1 (Database Names Available):
                - Advisor name from database: "{advisor_name}"
                - Primary Client name from database: "{client_name}"
                
                MEETING STRUCTURE:
                - There is always exactly 1 advisor and at least 1 client
                - There may be additional clients (spouse, family members, business partners)
                - The advisor typically speaks first and leads the meeting
                
                CRITICAL RULES:
                1. You MUST use "{advisor_name}" for the advisor - do NOT extract a different name from transcript
                2. You MUST use "{client_name}" for the primary client - do NOT extract a different name from transcript
                3. For additional clients (3rd, 4th, 5th participants):
                - Extract their actual names from transcript if mentioned
                - If names not mentioned, label as "Client 2", "Client 3", etc.
                4. Format: Use "Name (Role)" for all participants
                
                Example outputs:
                {{"Guest-1": "{advisor_name} (Advisor)", "Guest-2": "{client_name} (Client)"}}
                {{"Guest-1": "{advisor_name} (Advisor)", "Guest-2": "{client_name} (Client)", "Guest-3": "Mary Lim (Client)"}}
                {{"Guest-1": "{advisor_name} (Advisor)", "Guest-2": "{client_name} (Client)", "Guest-3": "Client 2"}}
                """
            elif advisor_name or client_name:
                # Scenario B: Partial names from database
                known_name = advisor_name or client_name
                known_role = "Advisor" if advisor_name else "Client"
                unknown_role = "Client" if advisor_name else "Advisor"
                
                name_instructions = f"""
                NAME ASSIGNMENT - MIXED PRIORITY (Partial Database Names):
                - {known_role} name from database: "{known_name}"
                - {unknown_role} name: NOT in database
                
                MEETING STRUCTURE:
                - There is always exactly 1 advisor and at least 1 client
                - There may be additional clients (spouse, family members, business partners)
                - The advisor typically speaks first and leads the meeting
                
                CRITICAL RULES:
                1. You MUST use "{known_name}" for the {known_role.lower()} - this is non-negotiable
                2. For the {unknown_role.lower()}: 
                - FIRST try to extract their actual name from the transcript (look for introductions)
                - If no name is mentioned, use just "{unknown_role}"
                3. For additional participants:
                - Extract their names from transcript if mentioned
                - If names not mentioned, label as "Client 2", "Client 3", etc.
                4. Format: Use "Name (Role)" when name is known, just "Role" when only role is known
                
                Example outputs:
                {{"Guest-1": "{known_name} ({known_role})", "Guest-2": "Sarah Lim (Client)", "Guest-3": "Client 2"}}
                {{"Guest-1": "{known_name} ({known_role})", "Guest-2": "{unknown_role}"}}
                """
            else:
                # Scenario C: No names from database
                name_instructions = """
                NAME ASSIGNMENT - PRIORITY 2 & 3 (Extract from Transcript or Use Roles):
                - No names available in database
                
                MEETING STRUCTURE:
                - There is always exactly 1 advisor and at least 1 client
                - There may be additional clients (spouse, family members, business partners)
                - The advisor typically speaks first and leads the meeting
                
                CRITICAL RULES:
                1. FIRST PRIORITY: Extract actual names from the transcript if clearly mentioned
                - Look for direct introductions: "Hi, I'm John", "My name is Sarah"
                - Look for being addressed: "Nice to meet you, David"
                - Look for self-references: "I'm Michael", "This is Lisa"
                2. SECOND PRIORITY: If names are NOT clearly stated in transcript:
                - Use "Advisor" for the financial advisor
                - Use "Client" for the primary client
                - Use "Client 2", "Client 3" for additional clients
                3. Format: Use "Name (Role)" if name extracted, just "Role" if no name found
                
                Example outputs (names found):
                {"Guest-1": "Christopher Wong (Advisor)", "Guest-2": "Michelle Tan (Client)", "Guest-3": "David Tan (Client)"}
                
                Example outputs (names not found):
                {"Guest-1": "Advisor", "Guest-2": "Client", "Guest-3": "Client 2"}
                """
            
            # Prepare LLM prompt for speaker identification
            system_prompt = f"""You are an expert at analyzing financial advisory meeting transcripts.

            Your task is to identify which speaker is the financial advisor and which are the clients.

            IDENTIFICATION CLUES:
            - Advisor: Asks discovery questions, provides advice, discusses financial products, uses professional language, explains concepts, leads the meeting
            - Client(s): Answer questions about their situation, discuss personal finances, ask for help, express concerns
            - Additional clients are often family members (spouse, children) or business partners

            {name_instructions}

            OUTPUT FORMAT:
            Return a JSON object mapping each speaker ID to their identity.
            - Only include speaker IDs that actually appear in the transcript (Guest-1, Guest-2, Guest-3, etc.)
            - There should be exactly 1 advisor
            - There should be at least 1 client, possibly more
            - Always return valid JSON
            """

            user_prompt = f"""Analyze this transcript and identify the speakers:

            {reduced_transcript}

            Return the speaker mapping as JSON."""

            # Call Azure OpenAI
            response = azure_openai_service.generate_json_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3  # Low temperature for consistent identification
            )
            
            # Extract speaker mapping from response
            speaker_mapping = response
            
            if not speaker_mapping or not isinstance(speaker_mapping, dict):
                logger.info(f"Warning: Invalid LLM response for meeting {meeting_id}, using fallback names")
                
                # Dynamic fallback logic respecting hierarchy and handling N speakers
                speaker_mapping = {}
                speaker_ids = sorted(list(all_speaker_ids))  # Sort to ensure consistent ordering
                
                if not speaker_ids:
                    # If we couldn't detect speaker IDs, use generic fallback
                    speaker_ids = ["Speaker 1", "Speaker 2"]
                
                # First speaker is typically the advisor
                if len(speaker_ids) >= 1:
                    if advisor_name:
                        speaker_mapping[speaker_ids[0]] = f"{advisor_name} (Advisor)"
                    else:
                        speaker_mapping[speaker_ids[0]] = "Advisor"
                
                # Second speaker is the primary client
                if len(speaker_ids) >= 2:
                    if client_name:
                        speaker_mapping[speaker_ids[1]] = f"{client_name} (Client)"
                    else:
                        speaker_mapping[speaker_ids[1]] = "Client"
                
                # Additional speakers are additional clients
                for i, speaker_id in enumerate(speaker_ids[2:], start=2):
                    speaker_mapping[speaker_id] = f"Client {i}"
                
                logger.info(f"Applied fallback mapping for {len(speaker_ids)} speakers")
            
            # Replace speaker labels in transcript
            cleaned_transcript = transcript
            for old_label, new_label in speaker_mapping.items():
                cleaned_transcript = cleaned_transcript.replace(f"{old_label}", f"{new_label}")
            
            logger.info(f"Speaker identification complete for meeting {meeting_id}")
            logger.info(f"Mapping: {speaker_mapping}")
            
            return cleaned_transcript
            
        except Exception as e:
            logger.info(f"Speaker identification failed for meeting {meeting_id}: {e}")
            logger.info(f"Returning original transcript unchanged")
            return transcript  # Return original on failure