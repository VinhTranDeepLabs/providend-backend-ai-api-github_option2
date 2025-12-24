import requests
from typing import Tuple

class NetworkService:
    def __init__(self, timeout: int = 5):
        """
        Initialize Network Service
        
        Args:
            timeout: Timeout in seconds for connection check
        """
        self.timeout = timeout
        # Using multiple reliable endpoints for redundancy
        self.check_urls = [
            "https://www.google.com",
            # "https://1.1.1.1",  # Cloudflare DNS
            # "https://8.8.8.8"   # Google DNS
        ]
    
    def check_internet_connection(self) -> Tuple[bool, str]:
        """
        Check if internet connection is available
        
        Returns:
            Tuple of (is_online: bool, status_message: str)
        """
        for url in self.check_urls:
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=False
                )
                # If we get any response (even error codes), connection exists
                if response.status_code:
                    return True, "Online"
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                continue
            except requests.exceptions.RequestException:
                continue
        
        # If all checks failed
        return False, "Offline"

# Singleton instance
network_service = NetworkService()