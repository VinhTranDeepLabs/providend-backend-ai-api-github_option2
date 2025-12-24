from openai import AzureOpenAI
from config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT
)
import json
from typing import Dict, Any

class AzureOpenAIService:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
        self.deployment = AZURE_OPENAI_DEPLOYMENT
    
    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Dict[str, Any] = None
    ) -> str:
        """
        Generate a completion using Azure OpenAI
        
        Args:
            system_prompt: System instruction
            user_prompt: User message
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Optional JSON schema for structured output
        
        Returns:
            Generated completion text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        kwargs = {
            "model": self.deployment,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        
        return response.choices[0].message.content
    
    def generate_json_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate a JSON-structured completion
        
        Args:
            system_prompt: System instruction
            user_prompt: User message
            temperature: Sampling temperature
        
        Returns:
            Parsed JSON response
        """
        response_text = self.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response_text)

# Singleton instance
azure_openai_service = AzureOpenAIService()