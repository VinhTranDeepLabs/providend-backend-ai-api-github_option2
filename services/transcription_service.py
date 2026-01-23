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
import re
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

def has_generic_speaker_labels(transcript: str) -> bool:
    """
    Check if transcript still has generic speaker labels like Guest-1, Speaker 1, etc.
    
    Args:
        transcript: Transcript string (can be JSON or plain text)
    
    Returns:
        True if generic labels found, False otherwise
    """
    generic_patterns = ['guest-', 'speaker 1', 'speaker 2', 'speaker 3', 'speaker 4', 'speaker 5']
    transcript_lower = transcript.lower()
    return any(pattern in transcript_lower for pattern in generic_patterns)

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
    

    def identify_speakers(self, transcript: str, meeting_id: str, conn) -> dict:
        """
        Identify who each speaker is WITHOUT modifying the transcript.
        
        Args:
            transcript: JSON string '[{"speaker": "Guest-1", "text": "..."}]'
            meeting_id: Meeting ID for DB lookup
            conn: Database connection
        
        Returns:
            {
                "speaker_mapping": {"Guest-1": "John (Advisor)", "Guest-2": "Sarah (Client)"},
                "confidence": "high/medium/low",
                "num_speakers": 2,
                "method": "database" | "transcript_analysis" | "mixed",
                "all_speaker_ids": ["Guest-1", "Guest-2"]
            }
        """
        try:
            # Parse transcript JSON
            transcript_list = json.loads(transcript)
            
            # Extract unique speaker IDs
            all_speaker_ids = set()
            for entry in transcript_list:
                if isinstance(entry, dict) and "speaker" in entry:
                    all_speaker_ids.add(entry["speaker"])
            
            num_speakers = len(all_speaker_ids)
            logger.info(f"[{meeting_id}] Detected {num_speakers} unique speakers: {all_speaker_ids}")
            
            # Get DB names
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
            
            # Limit transcript for LLM analysis (first N exchanges)
            max_exchanges = int(os.getenv("PROCESSOR_TRANSCRIPT_IDENTIFY_LENGTH", "20"))
            reduced_transcript = transcript_list[:max_exchanges]
            
            # Build LLM prompt with name instructions
            system_prompt = self._build_identification_prompt(
                advisor_name, 
                client_name, 
                num_speakers,
                list(all_speaker_ids)
            )
            
            user_prompt = f"""Analyze this transcript and identify the speakers:

{json.dumps(reduced_transcript, ensure_ascii=False, indent=2)}

Return the speaker mapping as JSON with keys matching the EXACT speaker labels from the transcript (case-sensitive).
Example: {{"Guest-1": "Name (Role)", "Guest-2": "Name (Role)"}}"""
            
            # Call LLM
            response = azure_openai_service.generate_json_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )
            
            speaker_mapping = response
            
            # Validate mapping has all speakers
            missing_speakers = all_speaker_ids - set(speaker_mapping.keys())
            if missing_speakers:
                logger.warning(f"[{meeting_id}] LLM didn't map all speakers. Missing: {missing_speakers}")
                # Add fallback mappings
                speaker_list = sorted(list(all_speaker_ids))
                for idx, speaker_id in enumerate(speaker_list):
                    if speaker_id not in speaker_mapping:
                        if idx == 0 and advisor_name:
                            speaker_mapping[speaker_id] = f"{advisor_name} (Advisor)"
                        elif idx == 1 and client_name:
                            speaker_mapping[speaker_id] = f"{client_name} (Client)"
                        elif idx == 0:
                            speaker_mapping[speaker_id] = "Advisor"
                        else:
                            speaker_mapping[speaker_id] = f"Client {idx}" if idx > 1 else "Client"
            
            # Determine confidence and method
            confidence = self._determine_confidence(advisor_name, client_name, num_speakers)
            method = self._determine_method(advisor_name, client_name)
            
            return {
                "speaker_mapping": speaker_mapping,
                "confidence": confidence,
                "num_speakers": num_speakers,
                "method": method,
                "all_speaker_ids": sorted(list(all_speaker_ids))
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[{meeting_id}] Failed to parse transcript JSON: {e}")
            raise ValueError(f"Invalid transcript format: {e}")
        except Exception as e:
            logger.error(f"[{meeting_id}] Error identifying speakers: {e}")
            raise


    def apply_speaker_mapping(self, transcript: str, speaker_mapping: dict) -> str:
        """
        Replace speaker labels with actual names in JSON transcript.
        
        Args:
            transcript: JSON string '[{"speaker": "Guest-1", "text": "..."}]'
            speaker_mapping: {"Guest-1": "John Wong (Advisor)", "Guest-2": "Sarah (Client)"}
        
        Returns:
            Modified transcript as JSON string
        """
        try:
            # Parse JSON string
            transcript_list = json.loads(transcript)
            
            speakers_replaced = set()
            
            # Replace speaker labels in each entry
            for entry in transcript_list:
                if isinstance(entry, dict) and "speaker" in entry:
                    original_speaker = entry["speaker"]
                    
                    # Try exact match first (case-sensitive)
                    if original_speaker in speaker_mapping:
                        entry["speaker"] = speaker_mapping[original_speaker]
                        speakers_replaced.add(original_speaker)
                    else:
                        # Try case-insensitive match
                        for key, value in speaker_mapping.items():
                            if key.lower() == original_speaker.lower():
                                entry["speaker"] = value
                                speakers_replaced.add(original_speaker)
                                break
            
            logger.info(f"Replaced {len(speakers_replaced)} unique speakers: {speakers_replaced}")
            
            # Convert back to JSON string
            return json.dumps(transcript_list, ensure_ascii=False)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse transcript as JSON: {e}")
            
            # Fallback: Simple string replacement (if transcript isn't JSON format)
            cleaned = transcript
            for old_label, new_label in speaker_mapping.items():
                # Replace in JSON context
                cleaned = cleaned.replace(f'"{old_label}"', f'"{new_label}"')
                # Replace standalone occurrences
                cleaned = cleaned.replace(old_label, new_label)
            
            logger.info(f"Applied fallback string replacement for {len(speaker_mapping)} mappings")
            return cleaned
        except Exception as e:
            logger.error(f"Error applying speaker mapping: {e}")
            raise


    def _build_identification_prompt(self, advisor_name: str, client_name: str, 
                                     num_speakers: int, speaker_ids: list) -> str:
        """
        Build LLM prompt based on available names.
        
        Args:
            advisor_name: Advisor name from DB (or None)
            client_name: Client name from DB (or None)
            num_speakers: Total number of speakers
            speaker_ids: List of actual speaker IDs (e.g., ["Guest-1", "Guest-2"])
        
        Returns:
            System prompt string for LLM
        """
        speaker_ids_str = ", ".join(f'"{sid}"' for sid in speaker_ids)
        
        if advisor_name and client_name:
            # Scenario A: Both names from database
            name_instructions = f"""
NAME ASSIGNMENT - DATABASE NAMES AVAILABLE:
- Advisor: "{advisor_name}" (from database - YOU MUST USE THIS EXACT NAME)
- Primary Client: "{client_name}" (from database - YOU MUST USE THIS EXACT NAME)
- Additional clients (if any): Extract from transcript if mentioned, otherwise use "Client 2", "Client 3", etc.

CRITICAL RULES:
1. You MUST use "{advisor_name}" for the advisor - do NOT extract a different name
2. You MUST use "{client_name}" for the primary client - do NOT extract a different name
3. Format: "Name (Role)" for all participants
4. Total speakers in transcript = {num_speakers}

Example output:
{{"Guest-1": "{advisor_name} (Advisor)", "Guest-2": "{client_name} (Client)"}}
"""
        elif advisor_name or client_name:
            # Scenario B: Partial names from database
            known_name = advisor_name or client_name
            known_role = "Advisor" if advisor_name else "Client"
            unknown_role = "Client" if advisor_name else "Advisor"
            
            name_instructions = f"""
NAME ASSIGNMENT - PARTIAL DATABASE NAMES:
- {known_role}: "{known_name}" (from database - YOU MUST USE THIS EXACT NAME)
- {unknown_role}: Extract from transcript if clearly mentioned, otherwise use just "{unknown_role}"
- Additional participants: Extract names or use "Client 2", "Client 3", etc.

CRITICAL RULES:
1. You MUST use "{known_name}" for the {known_role.lower()}
2. Format: "Name (Role)" when name is known, just "Role" when only role is known
3. Total speakers = {num_speakers}

Example outputs:
{{"Guest-1": "{known_name} ({known_role})", "Guest-2": "Sarah Lim (Client)", "Guest-3": "Client 2"}}
{{"Guest-1": "{known_name} ({known_role})", "Guest-2": "{unknown_role}"}}
"""
        else:
            # Scenario C: No names from database
            name_instructions = f"""
NAME ASSIGNMENT - NO DATABASE NAMES:
- Extract actual names from transcript if clearly mentioned (look for introductions)
- If no names found: Use "Advisor" for advisor, "Client" for primary client
- Additional clients: "Client 2", "Client 3", etc.

CRITICAL RULES:
1. Format: "Name (Role)" if name extracted, just "Role" if no name found
2. Total speakers = {num_speakers}

Example outputs (names found):
{{"Guest-1": "Christopher Wong (Advisor)", "Guest-2": "Michelle Tan (Client)", "Guest-3": "David Tan (Client)"}}

Example outputs (names NOT found):
{{"Guest-1": "Advisor", "Guest-2": "Client", "Guest-3": "Client 2"}}
"""
        
        return f"""You are an expert at analyzing financial advisory meeting transcripts.

TASK: Identify which speaker is the advisor and which are clients based on conversation patterns:
- Advisor: Asks discovery questions, provides advice, discusses financial products, leads meeting
- Client(s): Discusses personal finances, seeks guidance, answers questions about their situation

{name_instructions}

OUTPUT FORMAT:
- Return JSON object mapping speaker IDs to identities
- Keys must be EXACT speaker IDs from transcript: {speaker_ids_str}
- Include ALL {num_speakers} speakers
- Format values as: "Name (Role)" or just "Role"

CRITICAL: Your JSON keys must match these exact speaker IDs: {speaker_ids_str}
"""


    def _determine_confidence(self, advisor_name: str, client_name: str, num_speakers: int) -> str:
        """Determine confidence level for speaker identification"""
        if advisor_name and client_name:
            return "high"
        elif advisor_name or client_name:
            return "medium"
        else:
            # Low confidence if no DB names and multiple speakers
            return "low" if num_speakers > 2 else "medium"


    def _determine_method(self, advisor_name: str, client_name: str) -> str:
        """Determine which method was used for identification"""
        if advisor_name and client_name:
            return "database"
        elif advisor_name or client_name:
            return "mixed"
        else:
            return "transcript_analysis"

    def identify_and_replace_speakers(self, transcript: str, meeting_id: str, conn) -> str:
        """
        Identify speakers and replace labels in transcript (WRAPPER METHOD).
        
        This method maintains backward compatibility by combining:
        1. identify_speakers() - Get the mapping
        2. apply_speaker_mapping() - Apply the mapping
        
        Args:
            transcript: Raw transcript with generic speaker labels
            meeting_id: Meeting ID for context
            conn: Database connection
        
        Returns:
            Cleaned transcript with actual names/roles
        """
        try:
            logger.info(f"[{meeting_id}] Starting speaker identification and replacement...")
            
            # Step 1: Identify speakers
            identification_result = self.identify_speakers(
                transcript=transcript,
                meeting_id=meeting_id,
                conn=conn
            )
            
            speaker_mapping = identification_result["speaker_mapping"]
            confidence = identification_result["confidence"]
            method = identification_result["method"]
            
            logger.info(f"[{meeting_id}] Identified {len(speaker_mapping)} speakers "
                       f"(confidence: {confidence}, method: {method})")
            logger.info(f"[{meeting_id}] Speaker mapping: {speaker_mapping}")
            
            # Step 2: Apply mapping to transcript
            cleaned_transcript = self.apply_speaker_mapping(
                transcript=transcript,
                speaker_mapping=speaker_mapping
            )
            
            logger.info(f"[{meeting_id}] ✓ Speaker replacement completed successfully")
            
            return cleaned_transcript
            
        except Exception as e:
            logger.error(f"[{meeting_id}] ✗ Failed to identify/replace speakers: {e}")
            logger.exception(e)
            # Return original transcript on error
            return transcript