"""
Simple test client to demonstrate API usage
Run the FastAPI server first: python main.py
Then run this script: python test_client.py
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Sample transcript for testing
SAMPLE_TRANSCRIPT = """
Advisor: Good morning! Thank you for meeting with me today. Let's start by getting to know you better. Can you tell me about your current occupation?

Client: Good morning! I'm a software engineer at a tech company.

Advisor: Great! And how many years of work experience do you have in your field?

Client: I've been working for about 8 years now.

Advisor: Excellent. Now, let's talk about your financial situation. What's your annual income?

Client: My annual income is around $120,000 per year.

Advisor: Thank you. Do you have any dependents?

Client: Yes, I have two children, ages 5 and 7.

Advisor: I see. What are your main financial goals for the next 5 years?

Client: I want to save for my children's education and also start building a retirement fund. Maybe buy a larger house too.

Advisor: Those are great goals. Do you currently have any investments?

Client: I have some money in a 401k through my employer, but that's about it. I'm not very familiar with other investment options.

Advisor: No problem, we can help with that. What about insurance - do you have any existing coverage?

Client: I have basic health insurance through work, but I don't have life insurance yet.
"""

def test_health_check():
    """Test the health check endpoint"""
    print("\n" + "="*50)
    print("Testing Health Check Endpoint")
    print("="*50)
    
    response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_summarize():
    """Test the summarization endpoint"""
    print("\n" + "="*50)
    print("Testing Summarization Endpoint")
    print("="*50)
    
    payload = {
        "transcript": SAMPLE_TRANSCRIPT
    }
    
    response = requests.post(f"{BASE_URL}/summarize", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_autofill_questions():
    """Test the autofill questions endpoint"""
    print("\n" + "="*50)
    print("Testing Autofill Questions Endpoint")
    print("="*50)
    
    payload = {
        "transcript": SAMPLE_TRANSCRIPT
    }
    
    response = requests.post(f"{BASE_URL}/autofill-questions", json=payload)
    print(f"Status Code: {response.status_code}")
    
    result = response.json()
    print(f"Success: {result['success']}")
    print(f"Number of answered questions: {len(result['answered_questions'])}")
    print("\nSample answered questions:")
    for qa in result['answered_questions'][:3]:
        print(f"\nQ: {qa['question']}")
        print(f"A: {qa['answer']}")
        print(f"Confidence: {qa['confidence']}")

def test_unanswered_questions():
    """Test the unanswered questions endpoint"""
    print("\n" + "="*50)
    print("Testing Unanswered Questions Endpoint")
    print("="*50)
    
    payload = {
        "transcript": SAMPLE_TRANSCRIPT
    }
    
    response = requests.post(f"{BASE_URL}/unanswered-questions", json=payload)
    print(f"Status Code: {response.status_code}")
    
    result = response.json()
    print(f"Success: {result['success']}")
    print(f"Total unanswered: {result['total_unanswered']}")
    print("\nUnanswered questions:")
    for question in result['unanswered_questions']:
        print(f"  - {question}")

def test_batch_transcribe():
    """Test the batch transcription endpoint"""
    print("\n" + "="*50)
    print("Testing Batch Transcription Endpoint")
    print("="*50)
    print("Note: This requires actual audio URLs from Azure Blob Storage")
    print("Skipping this test - uncomment and add valid URLs to test")
    
    # Uncomment and add valid audio URLs to test
    # payload = {
    #     "audio_urls": [
    #         "https://your-storage.blob.core.windows.net/audio/sample.wav"
    #     ],
    #     "language": "en-US"
    # }
    # 
    # response = requests.post(f"{BASE_URL}/batch-transcribe", json=payload)
    # print(f"Status Code: {response.status_code}")
    # print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Azure AI Gateway API - Test Client")
    print("="*50)
    print("Make sure the API server is running on http://localhost:8000")
    
    try:
        # Test all endpoints
        test_health_check()
        test_summarize()
        test_autofill_questions()
        test_unanswered_questions()
        test_batch_transcribe()
        
        print("\n" + "="*50)
        print("All tests completed!")
        print("="*50 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API server.")
        print("Please make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")