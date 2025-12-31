import azure.cognitiveservices.speech as speechsdk
from config.settings import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
from models.schemas import TranscriptionResult, SpeakerSegment
from typing import List, Optional
from utils.db_utils import DatabaseUtils
import requests
import time
import json

class TranscribeService:
    def __init__(self):
        self.speech_key = AZURE_SPEECH_KEY
        self.speech_region = AZURE_SPEECH_REGION
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
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
        print(f"Creating transcription job for: {audio_urls}")
        create_response = requests.post(transcriptions_url, headers=headers, json=job_config)

        if create_response.status_code != 201:
            raise Exception(f"Failed to create job: {create_response.text}")

        job_data = create_response.json()
        job_url = job_data['self']
        job_id = job_url.split('/')[-1]
        print(f"Job created: {job_id}")

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

            print(f"Status: {status} (elapsed: {elapsed_time}s)")

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
                print(f"Warning: Failed to download transcript: {transcript_response.text}")
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
            print(f"Job {job_id} deleted")
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