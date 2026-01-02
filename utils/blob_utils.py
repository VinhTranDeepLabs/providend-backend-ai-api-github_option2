from azure.storage.blob import BlobClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import time
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

class BlobUtils:
    """Utility class for Azure Blob Storage operations"""
    
    def __init__(self):
        """Initialize blob storage configuration"""
        self.account_name = os.getenv("BLOB_ACCOUNT_NAME")
        self.container_name = os.getenv("BLOB_CONTAINER_NAME")
        self.account_key = os.getenv("BLOB_ACCOUNT_KEY")
        
        if not all([self.account_name, self.container_name, self.account_key]):
            raise ValueError("Missing required blob storage environment variables: BLOB_ACCOUNT_NAME, BLOB_CONTAINER_NAME, BLOB_ACCOUNT_KEY")
        
        self.connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
    
    def generate_random_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename with timestamp hash
        
        Args:
            original_filename: Original filename with extension
        
        Returns:
            New filename in format: filename-hash.ext
        """
        timestamp = str(time.time()).encode('utf-8')
        random_hash = hashlib.sha256(timestamp).hexdigest()[:12]
        file_extension = os.path.splitext(original_filename)[1]
        file_wo_extension = original_filename.split(".")[0]
        
        return f"{file_wo_extension}-{random_hash}{file_extension}"
    
    def upload_blob(self, source_directory: str) -> str:
        """
        Upload a file to blob storage
        
        Args:
            source_directory: Path to local file
        
        Returns:
            URL of uploaded blob (without SAS token)
        """
        filename = os.path.basename(source_directory)
        target_filename = self.generate_random_filename(filename)
        
        blob = BlobClient.from_connection_string(
            conn_str=self.connection_string,
            container_name=self.container_name,
            blob_name=target_filename
        )
        
        with open(source_directory, "rb") as data:
            blob.upload_blob(data)
        
        link = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{target_filename}"
        
        return link
    
    def download_blob(self, blob_name: str, destination_directory: str = None) -> str:
        """
        Download a blob from Azure Storage
        
        Args:
            blob_name: Name of the blob to download, or full URL
            destination_directory: Local directory to save the file. If None, saves to current directory
        
        Returns:
            Path to the downloaded file
        """
        # If a URL is provided, extract the blob name
        if blob_name.startswith("https://"):
            blob_name = self._extract_blob_name(blob_name)
        
        # Set destination directory
        if destination_directory is None:
            destination_directory = os.getcwd()
        
        # Create destination directory if it doesn't exist
        os.makedirs(destination_directory, exist_ok=True)
        
        # Full path for the downloaded file
        local_filename = os.path.join(destination_directory, blob_name)
        
        # Create blob client
        blob = BlobClient.from_connection_string(
            conn_str=self.connection_string,
            container_name=self.container_name,
            blob_name=blob_name
        )
        
        # Download the blob
        with open(local_filename, "wb") as download_file:
            download_file.write(blob.download_blob().readall())
        
        return local_filename
    
    def generate_sas_url(self, blob_name: str, expiry_hours: int = 2) -> str:
        """
        Generate a SAS URL for a blob with read permissions
        
        Args:
            blob_name: Name of the blob (e.g., "file.wav")
            expiry_hours: Hours until SAS token expires (default: 2)
        
        Returns:
            Full blob URL with SAS token
        """
        # If blob_name is a full URL, extract just the blob name
        if blob_name.startswith("https://"):
            blob_name = self._extract_blob_name(blob_name)
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
            start=datetime.utcnow() - timedelta(minutes=5)  # Allow 5 min clock skew
        )
        
        blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
        
        return blob_url
    
    def get_url_with_sas(self, blob_url: str, expiry_hours: int = 2) -> str:
        """
        Take any blob URL and ensure it has a SAS token
        
        Args:
            blob_url: Blob URL (with or without SAS)
            expiry_hours: Hours until SAS token expires (default: 2)
        
        Returns:
            Blob URL with SAS token
        """
        # If URL already has SAS (contains "?"), return as-is
        if "?" in blob_url:
            return blob_url
        
        # If URL is from this storage account, add SAS
        if self.account_name in blob_url:
            return self.generate_sas_url(blob_url, expiry_hours)
        
        # External URL, return as-is
        return blob_url
    
    def _extract_blob_name(self, url: str) -> str:
        """
        Extract blob name from full URL
        
        Args:
            url: Full blob URL
        
        Returns:
            Blob name only
        """
        # URL format: https://accountname.blob.core.windows.net/containername/blobname
        # or with SAS: https://accountname.blob.core.windows.net/containername/blobname?sv=...
        
        # Remove SAS token if present
        url_without_sas = url.split("?")[0]
        
        # Extract blob name (everything after container name)
        blob_name = url_without_sas.split(f"{self.container_name}/")[-1]
        
        return blob_name
    
    def list_blobs(self, prefix: str = None) -> list:
        """
        List all blobs in container
        
        Args:
            prefix: Optional prefix to filter blobs
        
        Returns:
            List of blob names
        """
        from azure.storage.blob import BlobServiceClient
        
        blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        container_client = blob_service_client.get_container_client(self.container_name)
        
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]


# Singleton instance
blob_utils = BlobUtils()