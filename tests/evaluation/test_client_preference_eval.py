"""
Client Preference Agent Evaluation with DeepEval
Tests the correctness and anti-hallucination of ClientPreferenceService.
Pushes metrics directly to Confident AI dashboard.
"""

import os
import sys
import json
import deepeval
from deepeval import evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.models import AzureOpenAIModel

# Add root folder to python path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir)) # Up to tests/, then up to root! 
# Wait, if script is in tests/evaluation/test_client_preference_eval.py:
# current_dir = tests/evaluation
# root_dir = tests/evaluation/../.. = root!

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from services.client_preference_service import ClientPreferenceService
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

EVAL_MODEL = create_azure_model()


# ==================== TEST DATA ====================

RICH_TRANSCRIPT = """
Advisor: How's your weekend been?
Client: Great! Played golf on Saturday as usual at Sentosa Golf Club. 
Then we went to this amazing omakase place in town - I love Japanese food.
My wife and I are planning a trip to Hokkaido next month for our anniversary.
We just adopted a labrador, his name is Charlie.
I've been watching that new Netflix series "The Bear" - have you seen it?
Oh and you know me, die-hard Liverpool fan. What a season!
"""

EXPECTED_RICH_PREFERENCES = """
Client details:
- Hobbies: Golf at Sentosa Golf Club
- Favorite Foods: Japanese, Omakase
- Travel: Hokkaido next month (Anniversary)
- Pets: Labrador named Charlie
- TV/Media: Watching "The Bear" on Netflix
- Sports Team: Liverpool Fan
"""

FINANCE_ONLY_TRANSCRIPT = """
Advisor: Let's review your portfolio.
Client: Yes, I want to increase my equity allocation.
The market looks good and I'm comfortable with moderate risk.
My CPF is growing well too. Let's discuss retirement timeline.
I want to put some funds into a Singapore REITs ETF and some into fixed deposits.
"""

EXPECTED_FINANCE_PREFERENCES = """
No personal facts or client preferences found.
"""

# ==================== METRICS SETUP ====================

PREFERENCE_ACCURACY_METRIC = GEval(
    name="Preference Extraction Correctness",
    criteria="""Evaluate the correctness of extracted client preferences compared to the expected facts list.
    Check if:
    1. The extracted dict matches explicitly stated client facts.
    2. Numerical/Text amounts are correct (e.g., location named accurately).
    3. NO fictional items were added.
    4. Sub-category groupings are logical and accurate.""",
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT
    ],
    threshold=0.8,
    model=EVAL_MODEL
)

ANTI_HALLUCINATION_METRIC = GEval(
    name="Anti-Hallucination Guardrail",
    criteria="""Ensure the actual output DOES NOT contain personal facts when input contains pure financial discussions.
    Check if ANY personal facts like hobbies, sports, or family are extracted from strictly finance data.
    If actual output contains anything other than 'No preferences found' or empty list for categories, fail.""",
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT
    ],
    threshold=0.8,
    model=EVAL_MODEL
)


# ==================== EVALUATION LOGIC ====================

def run_evaluation():
    print("="*60)
    print("CLIENT PREFERENCE AGENT TEST SUITE")
    print("="*60)
    
    service = ClientPreferenceService()
    
    test_cases = []
    
    # 1. Evaluate Rich Transcript
    print("\n📝 running Rich Transcript Extraction...")
    rich_result = service.extract_preferences(
        transcript=RICH_TRANSCRIPT, 
        meeting_id="TEST-RICH-001",
        conn=None
    )
    # Convert response to string representation for GEval
    rich_pref_string = json.dumps(rich_result.get("client_preferences", {}), indent=2)
    
    test_cases.append(
        LLMTestCase(
            input=RICH_TRANSCRIPT,
            actual_output=rich_pref_string,
            expected_output=EXPECTED_RICH_PREFERENCES,
            additional_metadata={"test_type": "rich_transcript_extraction"}
        )
    )
    
    # 2. Evaluate Anti-Hallucination
    print("\n📝 running Anti-Hallucination Extraction...")
    finance_result = service.extract_preferences(
        transcript=FINANCE_ONLY_TRANSCRIPT, 
        meeting_id="TEST-FINANCE-001",
        conn=None
    )
    finance_pref_string = json.dumps(finance_result.get("client_preferences", {}), indent=2)
    
    test_cases.append(
        LLMTestCase(
            input=FINANCE_ONLY_TRANSCRIPT,
            actual_output=finance_pref_string,
            expected_output=EXPECTED_FINANCE_PREFERENCES,
            additional_metadata={"test_type": "anti_hallucination_extraction"}
        )
    )
    
    print("\n" + "="*60)
    print("EVALUATION")
    print("="*60)
    
    # Force login inside script to ensure dashboard push
    deepeval.login(api_key=os.getenv("DEEPEVAL_API_KEY"))
    
    results_rich = evaluate(
        test_cases=[test_cases[0]],
        metrics=[PREFERENCE_ACCURACY_METRIC],
    )
    
    results_finance = evaluate(
        test_cases=[test_cases[1]],
        metrics=[ANTI_HALLUCINATION_METRIC],
    )
    
    results = [results_rich, results_finance]
    
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print("\n📊 View detailed results at: https://app.confident-ai.com")
    return results

if __name__ == "__main__":
    run_evaluation()
