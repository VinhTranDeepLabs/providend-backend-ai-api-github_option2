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
        start_datetime: datetime = None,
        conn=None
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
        
            # 6. Create 'queued' entry in database (if conn provided)
            if conn:
                try:
                    from utils.db_utils import DatabaseUtils
                    db = DatabaseUtils(conn)
                    queue_result = db.insert_queued_transcription(
                        blob_name=blob_name,
                        meeting_id=meeting_id,
                        file_size_bytes=file_size_bytes
                    )
                    logger.info(f"✓ Audio queued for transcription: {queue_result['message']}")
                except Exception as e:
                    logger.warning(f"⚠ Failed to queue transcription (non-critical): {e}")
            
            # 7. Return success response
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
        language: str = 'en-SG',
        max_speakers: int = 4
    ) -> List[TranscriptionResult]:
        """
        Transcribe audio files with speaker diarization using API version 2025-10-15

        Args:
            audio_urls: List of blob URLs to audio files
            language: Locale code (default: 'en-SG'). Use specific locale, not 'auto'.
            max_speakers: Maximum number of speakers for diarization (default: 10, max: 36)

        Returns:
            List of TranscriptionResult objects, one per audio file
        """
        import time

        # ===== API 2025-10-15 endpoint =====
        endpoint = (
            f"https://{self.speech_region}.api.cognitive.microsoft.com"
            f"/speechtotext/transcriptions:submit?api-version=2025-10-15"
        )

        headers = {
            'Ocp-Apim-Subscription-Key': self.speech_key,
            'Content-Type': 'application/json'
        }

        # Use public blob URLs directly (no SAS tokens needed)
        logger.info(f"Audio URLs: {audio_urls}")

        # ===== Simplified diarization config for 2025-10-15 =====
        # No more separate 'diarizationEnabled' + nested 'diarization.speakers.minCount/maxCount'
        # Now it's just: diarization: { enabled: true, maxSpeakers: N }
        properties = {
            'wordLevelTimestampsEnabled': True,
            'punctuationMode': 'DictatedAndAutomatic',
            'profanityFilterMode': 'None',
            'timeToLiveHours': 48,  # Was timeToLive ISO8601 string in v3.2, now integer hours
            'diarization': {
                'enabled': True,
                'maxSpeakers': max_speakers
            }
        }

        # ===== Handle language identification if needed =====
        # If your meetings have multiple languages (e.g. English + Chinese),
        # use languageIdentification instead of 'auto'
        if language == 'auto':
            # Instead of 'auto', use language identification with candidate locales
            language = 'en-SG'  # Primary locale must still be set
            properties['languageIdentification'] = {
                'candidateLocales': ['en-US', 'en-SG', 'zh-CN'],
                'mode': 'Continuous'
            }

        job_config = {
            'contentUrls': audio_urls,
            'locale': language,
            'displayName': f'Batch_Transcription_{int(time.time())}',
            'properties': properties
        }

        logger.info(f"Submitting transcription job: locale={language}, "
                    f"maxSpeakers={max_speakers}, files={len(audio_urls)}")

        # ===== Submit transcription job =====
        response = requests.post(endpoint, headers=headers, json=job_config)
        response.raise_for_status()

        response_data = response.json()

        # ===== Use 'self' URL for polling (not constructing URL manually) =====
        transcription_url = response_data['self']
        files_url = response_data['links']['files']

        logger.info(f"Job submitted: {transcription_url}")

        # ===== Poll for completion =====
        status = 'NotStarted'
        poll_count = 0
        max_polls = 360  # 30 minutes at 5-second intervals

        while status not in ('Succeeded', 'Failed') and poll_count < max_polls:
            time.sleep(5)
            poll_count += 1

            status_response = requests.get(transcription_url, headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data.get('status', 'Unknown')

            if poll_count % 12 == 0:  # Log every 60 seconds
                logger.info(f"Poll #{poll_count}: status={status}")

        if status == 'Failed':
            error_info = status_data.get('properties', {}).get('error', {})
            raise Exception(f"Transcription failed: {error_info}")

        if poll_count >= max_polls:
            raise Exception("Transcription timed out after 30 minutes")

        logger.info(f"Transcription succeeded after {poll_count * 5} seconds")

        # ===== Get results =====
        files_response = requests.get(files_url, headers=headers)
        files_response.raise_for_status()
        files_data = files_response.json()

        results = []

        for file_info in files_data.get('values', []):
            if file_info.get('kind') == 'Transcription':
                content_url = file_info.get('links', {}).get('contentUrl')
                if not content_url:
                    continue

                content_response = requests.get(content_url)
                content_response.raise_for_status()
                transcription_data = content_response.json()

                # ===== Parse diarized output with speaker labels =====
                speaker_segments = []
                max_end_time = 0.0

                for phrase in transcription_data.get('recognizedPhrases', []):
                    speaker = phrase.get('speaker', 0)
                    n_best = phrase.get('nBest', [])
                    text = n_best[0].get('display', '') if n_best else ''

                    start_time = phrase.get('offsetInTicks', 0) / 10_000_000
                    duration_ticks = phrase.get('durationInTicks', 0) / 10_000_000
                    end_time = start_time + duration_ticks

                    if end_time > max_end_time:
                        max_end_time = end_time

                    speaker_segments.append(SpeakerSegment(
                        speaker=f"Speaker {speaker}",
                        text=text,
                        start_time=start_time,
                        end_time=end_time
                    ))

                # ===== Build formatted transcript with speaker labels =====
                transcript_lines = []
                for seg in speaker_segments:
                    transcript_lines.append(f"{seg.speaker}: {seg.text}")

                formatted_transcript = '\n'.join(transcript_lines)

                # Determine audio URL for this result
                audio_url = audio_urls[0] if audio_urls else 'unknown'

                results.append(TranscriptionResult(
                    audio_url=audio_url,
                    transcript=formatted_transcript,
                    speaker_segments=speaker_segments,
                    language=language,
                    duration=max_end_time if speaker_segments else None
                ))

        # ===== Cleanup: Delete the transcription job =====
        try:
            requests.delete(transcription_url, headers=headers)
            logger.info("Transcription job cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

        logger.info(f"Returning {len(results)} transcription results")
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