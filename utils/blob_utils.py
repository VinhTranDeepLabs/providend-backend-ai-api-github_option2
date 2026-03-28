"""
Blob Storage Utilities for Azure Blob Storage operations
"""
import os
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Blob Storage Configuration
BLOB_ACCOUNT_NAME = os.getenv("BLOB_ACCOUNT_NAME")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")
BLOB_ACCOUNT_KEY = os.getenv("BLOB_ACCOUNT_KEY")


class BlobStorageService:
    """Service for Azure Blob Storage operations"""
    
    def __init__(self):
        self.account_name = BLOB_ACCOUNT_NAME
        self.container_name = BLOB_CONTAINER_NAME
        self.account_key = BLOB_ACCOUNT_KEY
        
        # Create connection string
        self.connection_string = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={self.account_name};"
            f"AccountKey={self.account_key};"
            f"EndpointSuffix=core.windows.net"
        )
        
        # Initialize blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
    
    def generate_audio_filename(self, meeting_id: str, start_datetime: datetime, extension: str) -> str:
        """
        Generate filename in format expected by background_batch_transcribe.py
        
        Format: <meeting_id>_<YYYY-MM-DD HH-MM-SS+00>.extension
        Example: MTG001_2024-12-29 14-30-00+00.wav
        
        Args:
            meeting_id: Meeting identifier
            start_datetime: Timestamp for the audio (UTC)
            extension: File extension (webm, wav)
        
        Returns:
            Formatted filename string
        """
        # Ensure datetime is in UTC
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        else:
            start_datetime = start_datetime.astimezone(timezone.utc)
        
        # Format: YYYY-MM-DD HH-MM-SS+00
        date_str = start_datetime.strftime("%Y-%m-%d")
        time_str = start_datetime.strftime("%H-%M-%S")
        timezone_str = "+00"  # Always UTC
        
        # Remove leading dot from extension if present
        extension = extension.lstrip('.')
        
        filename = f"{meeting_id}_{date_str} {time_str}{timezone_str}.{extension}"
        return filename
    
    async def upload_audio_file(self, file_content: bytes, blob_name: str, overwrite: bool = True) -> str:
        """
        Upload audio file to Azure Blob Storage
        
        Args:
            file_content: File content as bytes
            blob_name: Name for the blob (filename)
            overwrite: Whether to overwrite existing blob (default: True)
        
        Returns:
            Public URL of the uploaded blob
        """
        try:
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload file (Azure SDK handles this synchronously, but we run in executor)
            # This prevents blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: blob_client.upload_blob(
                    file_content,
                    overwrite=overwrite,
                    blob_type="BlockBlob"
                )
            )
            
            # Return public URL
            blob_url = self.get_blob_url(blob_name)
            return blob_url
            
        except Exception as e:
            raise Exception(f"Failed to upload to blob storage: {str(e)}")
    
    def get_blob_url(self, blob_name: str) -> str:
        """
        Construct public URL for a blob.
        Applies URL encoding to handle spaces and special characters
        (e.g. '+' timezone offset) in filenames — required by Azure Batch Transcription.
        
        Args:
            blob_name: Name of the blob
        
        Returns:
            Public URL string with percent-encoded blob name
        """
        import urllib.parse
        encoded_blob_name = urllib.parse.quote(blob_name)
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{encoded_blob_name}"
    
    def get_sas_url(self, blob_name: str, expiry_hours: int = 2) -> str:
        """
        Generate a SAS URL for a blob that remains active for a limited time.
        Required for Azure Speech Batch Transcription to access private blobs.
        
        Args:
            blob_name: Name of the blob
            expiry_hours: How long the SAS token should be valid (default: 2 hours)
            
        Returns:
            Full SAS URI for the blob
        """
        try:
            import urllib.parse
            
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
            )
            
            # Azure Batch Transcription requires strict URL encoding for spaces
            encoded_blob_name = urllib.parse.quote(blob_name)
            blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{encoded_blob_name}"
            
            return f"{blob_url}?{sas_token}"
        except Exception as e:
            # Fallback to normal URL if SAS generation fails
            print(f"Warning: Failed to generate SAS token for {blob_name}: {e}")
            return self.get_blob_url(blob_name)

    def validate_audio_extension(self, filename: str) -> bool:
        """
        Validate that file has an allowed audio extension
        
        Args:
            filename: Name of the file
        
        Returns:
            True if extension is allowed, False otherwise
        """
        allowed_extensions = ['.webm', '.wav']
        extension = os.path.splitext(filename)[1].lower()
        return extension in allowed_extensions


# Singleton instance
blob_storage_service = BlobStorageService()