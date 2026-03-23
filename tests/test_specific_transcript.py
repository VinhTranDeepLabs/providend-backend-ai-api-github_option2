import asyncio
import json
import logging
from services.client_preference_service import ClientPreferenceService

# Setup minimal logging to stdout
logging.basicConfig(level=logging.INFO)

async def test_transcript():
    try:
        with open("meeting_transcript.txt", "r", encoding="utf-8") as f:
            transcript = f.read()
            
        print("Transcript loaded. Length:", len(transcript))
        service = ClientPreferenceService()
        
        print("Calling _extract_preferences_with_llm...")
        result_json_str = service._extract_preferences_with_llm(transcript)
        
        print("\n=== EXTRACTION RESULT ===")
        print(result_json_str)
        with open("local_test_out.txt", "w", encoding="utf-8") as out_f:
            out_f.write(json.dumps(result_json_str, indent=2))

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_transcript())
