"""
Chatbot Testing with DeepEval (Azure OpenAI) - Confident AI Integration
Tests for Q&A accuracy and grounding of meeting chatbot responses

Run with: deepeval test run test_chatbot_deepeval.py
View results at: https://app.confident-ai.com
"""

import os
import sys
import pytest
from typing import List, Dict

import deepeval
from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, GEval
from deepeval.models import AzureOpenAIModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from services.azure_openai_service import azure_openai_service
from dotenv import load_dotenv

load_dotenv()


# ==================== AZURE MODEL SETUP ====================

def create_azure_model() -> AzureOpenAIModel:
    """Create Azure OpenAI model for DeepEval evaluation"""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or "gpt-4.1"
    
    return AzureOpenAIModel(
        model=deployment,
        deployment_name=deployment,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview"
    )


# ==================== CHATBOT WRAPPER ====================

class ChatbotTestWrapper:
    """
    Wrapper to simulate chatbot responses without DB dependencies.
    Mimics the LLM call logic from ChatService.generate_chat_response()
    """
    
    def __init__(self, transcript: str, summary: str, meeting_name: str = "Test Meeting"):
        self.transcript = transcript
        self.summary = summary
        self.meeting_name = meeting_name
    
    def generate_response(self, question: str) -> str:
        """Generate chatbot response for a question using meeting context."""
        system_prompt = f"""You are an AI assistant helping a financial advisor analyze meeting data.

Meeting Context:
- Meeting: {self.meeting_name}

Meeting Transcript:
{self.transcript if self.transcript else "No transcript available"}

Meeting Summary:
{self.summary if self.summary else "No summary available"}

Your role is to:
1. Answer questions about this specific meeting
2. Reference information from the transcript and summary
3. Provide insights based on the meeting content
4. Be concise and professional, respond in point form wherever appropriate unless asked otherwise.
5. At the end of your response, please ask if the advisor needs any further elaboration on the points discussed whenever applicable and avoid offering guidance on next steps unless specifically asked.

If chart data is provided, analyze it in the context of the meeting discussion."""

        user_prompt = f"Advisor's Question: {question}"
        
        response = azure_openai_service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.strip()


# ==================== TEST DATA ====================

SAMPLE_TRANSCRIPT = """
Advisor: Good morning, Mr. Tan. Thank you for meeting with me today.

Mr. Tan: Good morning. Happy to be here.

Advisor: Let's start by discussing your current financial situation. Can you tell me about your current portfolio?

Mr. Tan: Sure. My current portfolio is valued at $500,000. I have about $300,000 in equities and $200,000 in bonds.

Advisor: Excellent. And what are your retirement goals?

Mr. Tan: I'd like to retire at age 60, which is in about 15 years. I'm hoping to have around $2 million by then.

Advisor: That's a clear goal. Based on your current portfolio and timeline, I recommend increasing your CPF contributions by $500 per month. This will help you reach your retirement goal more comfortably.

Mr. Tan: That sounds reasonable. What about life insurance?

Advisor: Given that you have two young children, I recommend a term life insurance policy with a coverage of about 5 years of your annual income, which would be around $600,000. This would provide income replacement if something happens to you.

Mr. Tan: Okay, I'll need to think about that. What are the next steps?

Advisor: I'll send you a detailed proposal by next week, including the CPF contribution plan and the insurance options. We can schedule a follow-up meeting to discuss any questions you have.

Mr. Tan: Perfect. Thank you for your time.
"""

SAMPLE_SUMMARY = """
Meeting Objective: Initial financial planning consultation with Mr. Tan to discuss retirement goals and insurance needs.

Client Situation: Mr. Tan has a current portfolio valued at $500,000 ($300,000 equities, $200,000 bonds). He is 45 years old with two young children.

Goals: Mr. Tan wants to retire at age 60 with approximately $2 million in savings. 

Recommendations:
- Increase CPF contributions by $500 per month
- Consider term life insurance with $600,000 coverage (5 years income replacement)

Next Steps: Advisor will send detailed proposal by next week and schedule follow-up meeting.
"""

# Build retrieval context for grounding tests
RETRIEVAL_CONTEXT = [
    f"Meeting Transcript:\n{SAMPLE_TRANSCRIPT}",
    f"Meeting Summary:\n{SAMPLE_SUMMARY}"
]


# ==================== METRICS SETUP ====================

EVAL_MODEL = create_azure_model()

FAITHFULNESS_METRIC = FaithfulnessMetric(
    threshold=0.9,
    model=EVAL_MODEL
)

ACCURACY_METRIC = GEval(
    name="Q&A Factual Accuracy",
    criteria="""Evaluate the factual accuracy of the chatbot's response compared to the expected answer.
    Check if:
    1. The response contains the key facts from the expected answer
    2. Numerical values (amounts, dates, percentages) are correct
    3. Names and entities are accurately mentioned
    4. The response does not contradict the expected answer
    5. The core information is preserved even if wording differs""",
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT
    ],
    threshold=0.8,
    model=EVAL_MODEL
)


# ==================== TEST CASE GENERATION ====================

def generate_accuracy_test_cases() -> List[LLMTestCase]:
    """Generate test cases for Q&A accuracy tests"""
    chatbot = ChatbotTestWrapper(
        transcript=SAMPLE_TRANSCRIPT,
        summary=SAMPLE_SUMMARY,
        meeting_name="Financial Planning - Mr. Tan"
    )
    
    accuracy_qa_pairs = [
        {
            "question": "What is the client's current portfolio value?",
            "expected_answer": "The client's current portfolio is valued at $500,000, with $300,000 in equities and $200,000 in bonds."
        },
        {
            "question": "How much does Mr. Tan want to have by retirement?",
            "expected_answer": "Mr. Tan hopes to have around $2 million by retirement."
        }
    ]
    
    test_cases = []
    for qa in accuracy_qa_pairs:
        actual_output = chatbot.generate_response(qa["question"])
        test_cases.append(
            LLMTestCase(
                input=qa["question"],
                actual_output=actual_output,
                expected_output=qa["expected_answer"],
                retrieval_context=RETRIEVAL_CONTEXT,
                additional_metadata={
                    "test_type": "qa_accuracy",
                    "meeting_name": "Financial Planning - Mr. Tan"
                }
            )
        )
    
    return test_cases


def generate_grounding_test_cases() -> List[LLMTestCase]:
    """Generate test cases for Q&A grounding/faithfulness tests"""
    chatbot = ChatbotTestWrapper(
        transcript=SAMPLE_TRANSCRIPT,
        summary=SAMPLE_SUMMARY,
        meeting_name="Financial Planning - Mr. Tan"
    )
    
    grounding_questions = [
        "What is the client's current portfolio value?",
        "Does the client have any children?",
    ]
    
    test_cases = []
    for question in grounding_questions:
        actual_output = chatbot.generate_response(question)
        test_cases.append(
            LLMTestCase(
                input=question,
                actual_output=actual_output,
                retrieval_context=RETRIEVAL_CONTEXT,
                additional_metadata={
                    "test_type": "qa_grounding",
                    "meeting_name": "Financial Planning - Mr. Tan"
                }
            )
        )
    
    return test_cases


# ==================== PYTEST TEST CASES (Generated at module load) ====================

# Generate test cases once at module level for pytest parametrization
# These are cached to avoid regenerating for each test
_accuracy_test_cases = None
_grounding_test_cases = None


def get_accuracy_test_cases():
    """Lazy load accuracy test cases"""
    global _accuracy_test_cases
    if _accuracy_test_cases is None:
        _accuracy_test_cases = generate_accuracy_test_cases()
    return _accuracy_test_cases


def get_grounding_test_cases():
    """Lazy load grounding test cases"""
    global _grounding_test_cases
    if _grounding_test_cases is None:
        _grounding_test_cases = generate_grounding_test_cases()
    return _grounding_test_cases


# ==================== PYTEST TEST FUNCTIONS ====================

@pytest.mark.parametrize("test_index", range(2))  # Updated to match actual count
def test_qa_factual_accuracy(test_index):
    """Test that chatbot responses are factually accurate"""
    test_cases = get_accuracy_test_cases()
    assert_test(test_cases[test_index], [ACCURACY_METRIC])


@pytest.mark.parametrize("test_index", range(2))  # Updated to match actual count
def test_qa_faithfulness(test_index):
    """Test that chatbot responses are grounded in the meeting context"""
    test_cases = get_grounding_test_cases()
    assert_test(test_cases[test_index], [FAITHFULNESS_METRIC])


# ==================== ALTERNATIVE: DATASET-BASED EVALUATION ====================

def run_dataset_evaluation():
    """
    Alternative method: Run evaluation using EvaluationDataset
    This also pushes results to Confident AI
    
    Run this directly: python test_chatbot_deepeval.py
    """
    print("="*60)
    print("CHATBOT TEST SUITE - Dataset Evaluation Mode")
    print("="*60)
    print(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"Model: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')}")
    
    # Generate all test cases
    print("\n📝 Generating test cases...")
    accuracy_cases = generate_accuracy_test_cases()
    grounding_cases = generate_grounding_test_cases()
    
    print(f"  - Accuracy test cases: {len(accuracy_cases)}")
    print(f"  - Grounding test cases: {len(grounding_cases)}")
    
    # Run accuracy evaluation directly with test_cases list
    print("\n" + "="*60)
    print("TEST 1: Q&A ACCURACY")
    print("="*60)
    
    # Force login inside script to ensure dashboard push
    deepeval.login(api_key=os.getenv("DEEPEVAL_API_KEY"))
    
    accuracy_results = deepeval.evaluate(
        test_cases=accuracy_cases,
        metrics=[ACCURACY_METRIC],
    )
    
    # Run grounding evaluation
    print("\n" + "="*60)
    print("TEST 2: Q&A GROUNDING/FAITHFULNESS")
    print("="*60)
    
    grounding_results = deepeval.evaluate(
        test_cases=grounding_cases,
        metrics=[FAITHFULNESS_METRIC],
    )
    
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print("\n📊 View detailed results at: https://app.confident-ai.com")
    
    return accuracy_results, grounding_results


# ==================== MAIN ====================

if __name__ == "__main__":
    # Verify Azure OpenAI configuration
    required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"✗ Missing environment variables: {', '.join(missing)}")
        print("\nRequired environment variables:")
        print("  - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL")
        print("  - AZURE_OPENAI_API_KEY: Your Azure OpenAI API key")
        print("  - AZURE_OPENAI_DEPLOYMENT_NAME: Model deployment name (default: gpt-4.1)")
        print("  - AZURE_OPENAI_API_VERSION: API version (default: 2024-02-15-preview)")
        print("  - DEEPEVAL_API_KEY: Your Confident AI API key (for dashboard)")
        sys.exit(1)
    
    # Check for Confident AI API key
    if not os.getenv("DEEPEVAL_API_KEY"):
        print("⚠️  Warning: DEEPEVAL_API_KEY not set. Results won't be pushed to Confident AI.")
        print("   Set it with: export DEEPEVAL_API_KEY=your_api_key")
        print("   Or run: deepeval login\n")
    
    # Run dataset-based evaluation (pushes to Confident AI)
    run_dataset_evaluation()