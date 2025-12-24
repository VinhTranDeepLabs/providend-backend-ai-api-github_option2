import azure.cognitiveservices.speech as speechsdk
from config.settings import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
from models.schemas import TranscriptionResult, SpeakerSegment
from typing import List, Optional
from utils.db_utils import DatabaseUtils
import requests
import time

class TranscribeService:
    def __init__(self):
        self.speech_key = AZURE_SPEECH_KEY
        self.speech_region = AZURE_SPEECH_REGION
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
    
    def batch_transcribe_urls(
        self,
        audio_urls: List[str],
        language: str = "en-US"
    ) -> List[TranscriptionResult]:
        """
        Perform batch transcription with speaker diarization using Azure Batch Transcription API
        
        Args:
            audio_urls: List of publicly accessible audio file URLs
            language: Language code (default: en-US)
        
        Returns:
            List of TranscriptionResult objects
        """
        # Batch Transcription REST API endpoint
        endpoint = f"https://{self.speech_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.speech_key,
            "Content-Type": "application/json"
        }
        
        # Create batch transcription job
        transcription_definition = {
            "contentUrls": audio_urls,
            "properties": {
                "diarizationEnabled": True,
                "wordLevelTimestampsEnabled": True,
                "punctuationMode": "DictatedAndAutomatic",
                "profanityFilterMode": "Masked"
            },
            "locale": language,
            "displayName": f"Batch Transcription {time.time()}"
        }
        
        # Submit transcription job
        response = requests.post(endpoint, headers=headers, json=transcription_definition)
        response.raise_for_status()
        
        transcription_location = response.headers.get("Location")
        transcription_id = response.json().get("self")
        
        # Poll for completion
        status = "NotStarted"
        while status not in ["Succeeded", "Failed"]:
            time.sleep(5)  # Wait 5 seconds between polls
            
            status_response = requests.get(transcription_id, headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "Failed":
                raise Exception(f"Transcription failed: {status_data.get('properties', {}).get('error', {})}")
        
        # Get transcription files
        files_url = f"{transcription_id}/files"
        files_response = requests.get(files_url, headers=headers)
        files_response.raise_for_status()
        files_data = files_response.json()
        
        results = []
        
        # Process each transcription result
        for file_info in files_data.get("values", []):
            if file_info.get("kind") == "Transcription":
                content_url = file_info.get("links", {}).get("contentUrl")
                
                # Download transcription result
                content_response = requests.get(content_url)
                content_response.raise_for_status()
                transcription_data = content_response.json()
                
                # Parse combined transcript and speaker segments
                combined_phrases = transcription_data.get("combinedRecognizedPhrases", [{}])[0]
                full_transcript = combined_phrases.get("display", "")
                
                speaker_segments = []
                for phrase in transcription_data.get("recognizedPhrases", []):
                    speaker = phrase.get("speaker", "Unknown")
                    text = phrase.get("nBest", [{}])[0].get("display", "")
                    start_time = phrase.get("offsetInTicks", 0) / 10000000  # Convert ticks to seconds
                    duration = phrase.get("durationInTicks", 0) / 10000000
                    end_time = start_time + duration
                    
                    speaker_segments.append(SpeakerSegment(
                        speaker=f"Speaker {speaker}",
                        text=text,
                        start_time=start_time,
                        end_time=end_time
                    ))
                
                # Find matching audio URL (simplified approach)
                audio_url = audio_urls[0] if audio_urls else "unknown"
                
                results.append(TranscriptionResult(
                    audio_url=audio_url,
                    transcript=full_transcript,
                    speaker_segments=speaker_segments,
                    language=language,
                    duration=speaker_segments[-1].end_time if speaker_segments else None
                ))
        
        # Clean up: Delete the transcription job
        requests.delete(transcription_id, headers=headers)
        
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