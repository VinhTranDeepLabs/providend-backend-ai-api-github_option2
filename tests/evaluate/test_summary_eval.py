"""
Summary Testing with DeepEval (Azure OpenAI)
Streamlined tests for meeting summary quality evaluation

Metrics included (6 essential tests):
  1. Faithfulness: Claims supported by transcript
  2. Summarization Completeness: Key facts presence check (GEval - not penalizing extra context)
  3. Manual Coverage: Deterministic key info validation
  4. Financial Accuracy: Monetary data accuracy (GEval)
  5. Professional Tone: Language appropriateness (GEval)
  6. Consistency: Cross-run stability (GEval)

Removed metrics (redundant):
  - Hallucination (covered by Faithfulness)
  - Contextual Recall (covered by Summarization Completeness)
  - Answer Relevancy (not applicable to summarization)
  - Bias (low value for factual summaries)
  - Clarity (covered by Professional Tone)
  - Action Items (covered by Summarization Completeness)

Note: SummarizationMetric was replaced with custom GEval because it penalized
additional professional context/explanations added by the summary service.

Run options:
  - deepeval test run test_summary_eval_v2.py      (pytest mode, pushes to Confident AI)
  - deepeval test run test_summary_eval_v2.py -v   (verbose mode)
  - python test_summary_eval_v2.py                 (standalone mode with detailed output)
"""

import os
import sys
import json
import time
import pytest
from typing import List, Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import deepeval
from deepeval import assert_test, evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    GEval
)
from deepeval.models import AzureOpenAIModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.dataset import EvaluationDataset

from services.summay_service import SummaryService
from services.meeting_service import MeetingService
from utils.db_utils import DatabaseUtils
import psycopg2
from dotenv import load_dotenv

load_dotenv()


# ==================== CONFIGURATION ====================

# Rate limiting for Azure OpenAI
RATE_LIMIT_DELAY = 5      # Seconds between API calls
ERROR_DELAY = 10          # Seconds after error

# Test run configurations
CONSISTENCY_RUNS = 3      # Standalone mode (reduced from 5)
PYTEST_CONSISTENCY_RUNS = 2  # Pytest mode

# Metric thresholds (6 metrics only)
THRESHOLDS = {
    "faithfulness": 0.90,
    "summarization": 0.70,
    "financial_accuracy": 0.90,  # High threshold for financial data
    "tone": 0.80,
    "consistency": 0.80,
    "coverage": 0.70            # Manual coverage check
}


# ==================== SAMPLE TEST DATA ====================

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

SAMPLE_KEY_INFO = {
    "amounts": ["$500,000", "$300,000", "$200,000", "$2 million", "$500", "$600,000"],
    "dates": ["age 60", "15 years", "next week"],
    "decisions": ["CPF contributions", "term life insurance"],
    "action_items": ["send detailed proposal", "schedule follow-up"]
}

# Key items to check in summarization (used by GEval criteria)
# These are embedded directly in the GEval criteria string for clarity
SUMMARIZATION_KEY_ITEMS = [
    "Portfolio value of $500,000",
    "Equities allocation of $300,000",
    "Bonds allocation of $200,000",
    "Retirement goal of $2 million",
    "Retirement age 60 or 15 years timeline",
    "CPF contribution recommendation of $500 per month",
    "Term life insurance recommendation",
    "Insurance coverage amount of $600,000",
    "Proposal to be sent by next week",
    "Follow-up meeting to be scheduled"
]


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


# ==================== METRIC FACTORY ====================

def create_all_metrics(azure_model: AzureOpenAIModel) -> Dict[str, Any]:
    """
    Create evaluation metrics for streamlined summary testing.
    Returns a dictionary of metric name -> metric instance.
    
    Only 6 essential metrics:
    1. Faithfulness - grounding check
    2. Summarization - completeness check
    3. Financial Accuracy - critical for compliance
    4. Professional Tone - quality assurance
    5. Consistency - stability check
    (Manual Coverage is not a DeepEval metric)
    """
    
    metrics = {}
    
    # ----- Core DeepEval Metrics -----
    
    # 1. Faithfulness - Are claims supported by the transcript?
    metrics["faithfulness"] = FaithfulnessMetric(
        threshold=THRESHOLDS["faithfulness"],
        model=azure_model,
        verbose_mode=True
    )
    
    # 2. Summarization Completeness - Key facts presence check (custom GEval)
    # NOTE: Using GEval instead of SummarizationMetric because SummarizationMetric
    # penalizes additional context/explanations added by the summary service.
    # This custom metric only checks if key facts are present.
    metrics["summarization"] = GEval(
        name="Summary Completeness",
        criteria="""Evaluate if the summary captures all key information from the transcript.
        
        Check if these items are mentioned in the summary:
        1. Portfolio value of $500,000
        2. Equities allocation of $300,000
        3. Bonds allocation of $200,000
        4. Retirement goal of $2 million
        5. Retirement age 60 or 15 years timeline
        6. CPF contribution recommendation of $500 per month
        7. Term life insurance recommendation
        8. Insurance coverage amount of $600,000
        9. Proposal to be sent by next week
        10. Follow-up meeting to be scheduled
        
        IMPORTANT: Additional professional context, explanations, rationale, or 
        enriched framing added by the summary service should NOT be penalized. 
        Only check if the key facts listed above are present.
        
        Score 0-1 based on how many of the 10 items are mentioned.
        - 1.0 = All 10 items present
        - 0.7 = 7 items present
        - 0.5 = 5 items present
        - etc.""",
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT
        ],
        threshold=THRESHOLDS["summarization"],
        model=azure_model,
        verbose_mode=True
    )
    
    # ----- Custom GEval Metrics -----
    
    # 3. Financial Accuracy - Critical for compliance
    metrics["financial_accuracy"] = GEval(
        name="Financial Accuracy",
        criteria="""Evaluate the accuracy of financial information in the summary:
        1. Are all monetary amounts exactly correct (no rounding errors)?
        2. Are percentages and rates accurately stated?
        3. Are financial product names and terms correct?
        4. Are no financial figures hallucinated or fabricated?
        5. Do recommendations match what was discussed in the transcript?
        
        This is critical for financial advisory compliance. Score strictly.""",
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.RETRIEVAL_CONTEXT
        ],
        threshold=THRESHOLDS["financial_accuracy"],
        model=azure_model,
        verbose_mode=True
    )
    
    # 4. Professional Tone - Language appropriateness
    metrics["tone"] = GEval(
        name="Professional Tone",
        criteria="""Evaluate the professionalism and appropriateness of the summary's tone:
        1. Is the language formal and professional?
        2. Is it free from casual or colloquial expressions?
        3. Is client information presented respectfully?
        4. Is the tone consistent throughout the summary?
        5. Is it appropriate for a financial advisory context?
        6. Is the summary well-structured and easy to read?
        
        Score based on suitability for professional/compliance use.""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=THRESHOLDS["tone"],
        model=azure_model,
        verbose_mode=True
    )
    
    # 5. Consistency - Cross-run stability
    metrics["consistency"] = GEval(
        name="Summary Consistency",
        criteria="""Evaluate the semantic consistency between two summaries of the same meeting:
        1. Do both summaries capture the same key information and decisions?
        2. Are the same facts and figures presented?
        3. Do they convey the same overall meaning?
        4. Is the structure and organization similar?
        5. Would a reader get the same understanding from both?
        
        Score based on how semantically equivalent the two summaries are.""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT
        ],
        threshold=THRESHOLDS["consistency"],
        model=azure_model,
        verbose_mode=True
    )
    
    return metrics


# ==================== HELPER FUNCTIONS ====================

def generate_summary(summary_service: SummaryService, transcript: str, 
                    meeting_id: str, conn=None) -> str:
    """Generate summary using the summary service with debug logging"""
    print(f"\n[DEBUG] generate_summary called for meeting_id: {meeting_id}")
    print(f"[DEBUG] Transcript length: {len(transcript)} characters")
    
    try:
        summary = summary_service.generate_summary(
            transcript=transcript,
            meeting_id=meeting_id,
            created_by="TEST_SYSTEM",
            conn=conn
        )
        
        print(f"[DEBUG] Summary generation successful")
        print(f"[DEBUG] Summary length: {len(summary) if summary else 0} characters")
        print(f"[DEBUG] Summary is None: {summary is None}")
        print(f"[DEBUG] Summary is empty string: {summary == ''}")
        
        if summary:
            print(f"[DEBUG] Summary preview (first 500 chars):")
            print(f"[DEBUG] {summary[:500]}...")
        else:
            print(f"[DEBUG] WARNING: Summary is empty or None!")
        
        return summary
        
    except Exception as e:
        print(f"[DEBUG] ERROR in generate_summary: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise


def check_key_info_coverage(summary: str, key_info: Dict[str, List[str]]) -> Dict[str, Any]:
    """Check if key information appears in summary (manual validation)"""
    summary_lower = summary.lower()
    
    results = {
        'amounts_covered': 0,
        'amounts_total': len(key_info.get('amounts', [])),
        'dates_covered': 0,
        'dates_total': len(key_info.get('dates', [])),
        'decisions_covered': 0,
        'decisions_total': len(key_info.get('decisions', [])),
        'actions_covered': 0,
        'actions_total': len(key_info.get('action_items', [])),
        'missed_items': []
    }
    
    for amount in key_info.get('amounts', []):
        if amount.lower() in summary_lower:
            results['amounts_covered'] += 1
        else:
            results['missed_items'].append(f"Amount: {amount}")
    
    for date in key_info.get('dates', []):
        if date.lower() in summary_lower:
            results['dates_covered'] += 1
        else:
            results['missed_items'].append(f"Date: {date}")
    
    for decision in key_info.get('decisions', []):
        if decision.lower() in summary_lower:
            results['decisions_covered'] += 1
        else:
            results['missed_items'].append(f"Decision: {decision}")
    
    for action in key_info.get('action_items', []):
        if action.lower() in summary_lower:
            results['actions_covered'] += 1
        else:
            results['missed_items'].append(f"Action: {action}")
    
    total_items = (results['amounts_total'] + results['dates_total'] + 
                  results['decisions_total'] + results['actions_total'])
    covered_items = (results['amounts_covered'] + results['dates_covered'] + 
                    results['decisions_covered'] + results['actions_covered'])
    
    results['coverage_score'] = covered_items / total_items if total_items > 0 else 0
    
    return results


def create_test_case(
    input_text: str,
    actual_output: str,
    transcript: str,
    meeting_id: str,
    test_type: str,
    expected_output: str = None,
    extra_metadata: Dict = None
) -> LLMTestCase:
    """Create a standardized test case with metadata for Confident AI dashboard"""
    
    print(f"\n[DEBUG] create_test_case called:")
    print(f"[DEBUG]   test_type: {test_type}")
    print(f"[DEBUG]   meeting_id: {meeting_id}")
    print(f"[DEBUG]   actual_output length: {len(actual_output) if actual_output else 0}")
    
    if not actual_output:
        print(f"[DEBUG] WARNING: actual_output is empty/None!")
    
    metadata = {
        "meeting_id": meeting_id,
        "test_type": test_type,
        "transcript_length": len(transcript),
        "summary_length": len(actual_output) if actual_output else 0,
        "timestamp": datetime.now().isoformat()
    }
    
    if extra_metadata:
        metadata.update(extra_metadata)
    
    return LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        expected_output=expected_output,
        retrieval_context=[transcript],
        context=[transcript],
        additional_metadata=metadata
    )


# ==================== PYTEST FIXTURES ====================

@pytest.fixture(scope="module")
def azure_model():
    """Shared Azure model instance"""
    return create_azure_model()


@pytest.fixture(scope="module")
def all_metrics(azure_model):
    """All evaluation metrics"""
    return create_all_metrics(azure_model)


@pytest.fixture(scope="module")
def summary_service():
    """Shared summary service instance"""
    return SummaryService()


@pytest.fixture(scope="module")
def db_connection():
    """Database connection fixture"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT", "5432"),
            sslmode="require"
        )
        yield conn
        conn.close()
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        yield None


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Add delay between all tests to avoid rate limits"""
    yield
    time.sleep(RATE_LIMIT_DELAY)


# ==================== PYTEST TEST CLASSES (6 TESTS) ====================

class TestFaithfulness:
    """
    Test 1: Summary Faithfulness
    
    Purpose: Verifies that all claims made in the generated summary are 
    supported by and traceable to the original transcript.
    
    Why it matters: Ensures the summary doesn't make unsupported assertions,
    which is critical for financial compliance and accuracy.
    """
    
    def test_summary_faithfulness(self, summary_service, all_metrics, db_connection):
        """Test that summary claims are supported by transcript"""
        print("\n" + "="*60)
        print("TEST 1: FAITHFULNESS")
        print("Checking if all claims are grounded in the transcript...")
        print("="*60)
        
        summary = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-faithful-1", db_connection
        )
        
        if not summary:
            pytest.fail("Summary generation returned empty/None result")
        
        test_case = create_test_case(
            input_text="Summarize this financial advisory meeting",
            actual_output=summary,
            transcript=SAMPLE_TRANSCRIPT,
            meeting_id="pytest-faithful-1",
            test_type="faithfulness"
        )
        
        try:
            all_metrics["faithfulness"].measure(test_case)
            score = all_metrics["faithfulness"].score
            reason = all_metrics["faithfulness"].reason
            
            print(f"\n[RESULT] Faithfulness score: {score}")
            print(f"[RESULT] Reason: {reason}")
            
            if score is None:
                print("[WARNING] FaithfulnessMetric returned None score!")
            
            assert_test(test_case, [all_metrics["faithfulness"]])
            
        except Exception as e:
            print(f"[ERROR] Exception during evaluation: {type(e).__name__}: {e}")
            raise


class TestSummarizationQuality:
    """
    Test 2: Summarization Completeness
    
    Purpose: Evaluates if the summary captures all key information from the
    transcript by checking for 10 specific data points.
    
    Why it matters: Ensures completeness - all important facts, figures,
    recommendations, and action items are included.
    
    Note: Uses custom GEval instead of SummarizationMetric to avoid penalizing
    additional professional context added by the summary service.
    """
    
    def test_summarization_quality(self, summary_service, all_metrics, db_connection):
        """Test that key facts are present in the summary"""
        print("\n" + "="*60)
        print("TEST 2: SUMMARIZATION COMPLETENESS")
        print("Checking if key facts are present in the summary...")
        print("="*60)
        
        summary = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-summarization-1", db_connection
        )
        
        # GEval needs retrieval_context for comparison
        test_case = LLMTestCase(
            input="Check if summary contains all key information from the transcript",
            actual_output=summary,
            retrieval_context=[SAMPLE_TRANSCRIPT],
            additional_metadata={
                "meeting_id": "pytest-summarization-1",
                "test_type": "summarization_completeness"
            }
        )
        
        print(f"\n[INFO] Checking for 10 key items:")
        print("  1. Portfolio value ($500,000)")
        print("  2. Equities allocation ($300,000)")
        print("  3. Bonds allocation ($200,000)")
        print("  4. Retirement goal ($2 million)")
        print("  5. Retirement timeline (age 60 / 15 years)")
        print("  6. CPF recommendation ($500/month)")
        print("  7. Term life insurance recommendation")
        print("  8. Insurance coverage ($600,000)")
        print("  9. Proposal by next week")
        print("  10. Follow-up meeting")
        
        try:
            all_metrics["summarization"].measure(test_case)
            score = all_metrics["summarization"].score
            reason = all_metrics["summarization"].reason
            
            print(f"\n[RESULT] Summarization Completeness score: {score}")
            print(f"[RESULT] Reason: {reason}")
            
            assert_test(test_case, [all_metrics["summarization"]])
            
        except Exception as e:
            print(f"[ERROR] Exception during evaluation: {type(e).__name__}: {e}")
            raise


class TestManualCoverage:
    """
    Test 3: Manual Coverage Check
    
    Purpose: Deterministic validation that specific key information 
    (amounts, dates, decisions, action items) appears in the summary.
    
    Why it matters: Provides a reliable fallback check that doesn't depend
    on LLM evaluation - uses simple string matching.
    """
    
    def test_manual_coverage(self, summary_service, db_connection):
        """Test key information coverage using string matching"""
        print("\n" + "="*60)
        print("TEST 3: MANUAL COVERAGE")
        print("Checking if key items appear in summary (string matching)...")
        print("="*60)
        
        summary = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-coverage-1", db_connection
        )
        
        coverage = check_key_info_coverage(summary, SAMPLE_KEY_INFO)
        
        print(f"\n[INFO] Coverage breakdown:")
        print(f"  Amounts: {coverage['amounts_covered']}/{coverage['amounts_total']}")
        print(f"  Dates: {coverage['dates_covered']}/{coverage['dates_total']}")
        print(f"  Decisions: {coverage['decisions_covered']}/{coverage['decisions_total']}")
        print(f"  Action Items: {coverage['actions_covered']}/{coverage['actions_total']}")
        
        if coverage['missed_items']:
            print(f"\n[WARNING] Missed items:")
            for item in coverage['missed_items']:
                print(f"  - {item}")
        
        print(f"\n[RESULT] Coverage score: {coverage['coverage_score']:.1%}")
        print(f"[RESULT] Threshold: {THRESHOLDS['coverage']:.1%}")
        
        assert coverage['coverage_score'] >= THRESHOLDS["coverage"], \
            f"Coverage {coverage['coverage_score']:.1%} below threshold {THRESHOLDS['coverage']:.1%}. Missing: {coverage['missed_items']}"


class TestFinancialAccuracy:
    """
    Test 4: Financial Accuracy
    
    Purpose: Evaluates accuracy of financial information - monetary amounts,
    percentages, product names, and recommendations.
    
    Why it matters: Critical for financial advisory compliance. Incorrect
    financial figures could lead to regulatory issues or client harm.
    """
    
    def test_financial_accuracy(self, summary_service, all_metrics, db_connection):
        """Test that financial information is accurately captured"""
        print("\n" + "="*60)
        print("TEST 4: FINANCIAL ACCURACY")
        print("Checking if financial data is exact and correct...")
        print("="*60)
        
        summary = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-financial-1", db_connection
        )
        
        test_case = create_test_case(
            input_text="Summarize financial details from the meeting",
            actual_output=summary,
            transcript=SAMPLE_TRANSCRIPT,
            meeting_id="pytest-financial-1",
            test_type="financial_accuracy"
        )
        
        try:
            all_metrics["financial_accuracy"].measure(test_case)
            score = all_metrics["financial_accuracy"].score
            reason = all_metrics["financial_accuracy"].reason
            
            print(f"\n[RESULT] Financial Accuracy score: {score}")
            print(f"[RESULT] Reason: {reason}")
            
            assert_test(test_case, [all_metrics["financial_accuracy"]])
            
        except Exception as e:
            print(f"[ERROR] Exception during evaluation: {type(e).__name__}: {e}")
            raise


class TestProfessionalTone:
    """
    Test 5: Professional Tone
    
    Purpose: Evaluates professionalism, language appropriateness, structure,
    and readability of the summary.
    
    Why it matters: Summaries are used for compliance records and client
    communications - they must be professional and well-structured.
    """
    
    def test_professional_tone(self, summary_service, all_metrics, db_connection):
        """Test summary professional tone and structure"""
        print("\n" + "="*60)
        print("TEST 5: PROFESSIONAL TONE")
        print("Checking language, structure, and professionalism...")
        print("="*60)
        
        summary = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-tone-1", db_connection
        )
        
        test_case = create_test_case(
            input_text="Summarize meeting for compliance records",
            actual_output=summary,
            transcript=SAMPLE_TRANSCRIPT,
            meeting_id="pytest-tone-1",
            test_type="professional_tone"
        )
        
        try:
            all_metrics["tone"].measure(test_case)
            score = all_metrics["tone"].score
            reason = all_metrics["tone"].reason
            
            print(f"\n[RESULT] Professional Tone score: {score}")
            print(f"[RESULT] Reason: {reason}")
            
            assert_test(test_case, [all_metrics["tone"]])
            
        except Exception as e:
            print(f"[ERROR] Exception during evaluation: {type(e).__name__}: {e}")
            raise


class TestConsistency:
    """
    Test 6: Semantic Consistency
    
    Purpose: Tests that multiple summaries generated from the same transcript
    are semantically consistent - they convey the same key information.
    
    Why it matters: Ensures the summary service produces reliable, repeatable
    outputs. Important for trust and quality assurance.
    """
    
    def test_semantic_consistency(self, summary_service, all_metrics, db_connection):
        """Test that multiple summaries are semantically consistent"""
        print("\n" + "="*60)
        print("TEST 6: SEMANTIC CONSISTENCY")
        print("Checking if multiple runs produce consistent summaries...")
        print("="*60)
        
        print("\n[INFO] Generating first summary (baseline)...")
        summary1 = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-consist-1", db_connection
        )
        
        time.sleep(RATE_LIMIT_DELAY)
        
        print("[INFO] Generating second summary...")
        summary2 = generate_summary(
            summary_service, SAMPLE_TRANSCRIPT, "pytest-consist-2", db_connection
        )
        
        time.sleep(RATE_LIMIT_DELAY)
        
        print("[INFO] Evaluating consistency between summaries...")
        
        test_case = LLMTestCase(
            input="Compare semantic consistency of two meeting summaries",
            actual_output=summary2,
            expected_output=summary1,
            additional_metadata={
                "meeting_id": "pytest-consistency",
                "test_type": "consistency",
                "summary1_length": len(summary1),
                "summary2_length": len(summary2)
            }
        )
        
        try:
            all_metrics["consistency"].measure(test_case)
            score = all_metrics["consistency"].score
            reason = all_metrics["consistency"].reason
            
            print(f"\n[RESULT] Consistency score: {score}")
            print(f"[RESULT] Reason: {reason}")
            
            assert_test(test_case, [all_metrics["consistency"]])
            
        except Exception as e:
            print(f"[ERROR] Exception during evaluation: {type(e).__name__}: {e}")
            raise


# ==================== COMPREHENSIVE EVALUATION (Dataset Mode) ====================

def run_comprehensive_evaluation(
    summary_service: SummaryService,
    metrics: Dict[str, Any],
    transcript: str = SAMPLE_TRANSCRIPT,
    meeting_id: str = "comprehensive-eval",
    conn = None
) -> Dict[str, Any]:
    """
    Run comprehensive evaluation using EvaluationDataset.
    This pushes all results to Confident AI in a single batch.
    """
    
    print("\n" + "="*60)
    print("COMPREHENSIVE EVALUATION (Dataset Mode)")
    print("="*60)
    
    # Generate summary once
    print("\nGenerating summary...")
    summary = generate_summary(summary_service, transcript, meeting_id, conn)
    print(f"  ✓ Summary generated ({len(summary)} chars)")
    
    # Create test cases for each metric type
    test_cases = []
    
    # 1. Faithfulness test case
    test_cases.append(LLMTestCase(
        input="Summarize this financial advisory meeting",
        actual_output=summary,
        retrieval_context=[transcript],
        additional_metadata={"test_type": "faithfulness", "meeting_id": meeting_id}
    ))
    
    # 2. Summarization completeness test case
    test_cases.append(LLMTestCase(
        input="Check if summary contains all key information from the transcript",
        actual_output=summary,
        retrieval_context=[transcript],
        additional_metadata={"test_type": "summarization_completeness", "meeting_id": meeting_id}
    ))
    
    # 3. Financial accuracy test case
    test_cases.append(LLMTestCase(
        input="Summarize financial details",
        actual_output=summary,
        retrieval_context=[transcript],
        additional_metadata={"test_type": "financial_accuracy", "meeting_id": meeting_id}
    ))
    
    # 4. Tone test case
    test_cases.append(LLMTestCase(
        input="Summarize meeting professionally",
        actual_output=summary,
        additional_metadata={"test_type": "tone", "meeting_id": meeting_id}
    ))
    
    # Create dataset
    dataset = EvaluationDataset(test_cases=test_cases)
    
    # Select metrics for evaluation (excluding manual coverage and consistency)
    eval_metrics = [
        metrics["faithfulness"],
        metrics["summarization"],
        metrics["financial_accuracy"],
        metrics["tone"]
    ]
    
    print(f"\nRunning evaluation with {len(eval_metrics)} metrics on {len(test_cases)} test cases...")
    print("This will push results to Confident AI dashboard.\n")
    
    # Run evaluation
    results = evaluate(
        test_cases=dataset,
        metrics=eval_metrics
    )
    
    return results


# ==================== STANDALONE TEST SUITE CLASS ====================

class SummaryTestSuite:
    """
    Full test suite for standalone execution with detailed logging.
    Use this when running: python test_summary_eval_v2.py
    
    Runs 6 essential tests:
    1. Faithfulness
    2. Summarization Quality
    3. Manual Coverage
    4. Financial Accuracy
    5. Professional Tone
    6. Consistency
    """
    
    def __init__(self, conn=None):
        self.summary_service = SummaryService()
        self.conn = conn
        
        # Initialize Azure OpenAI model
        self.eval_model = create_azure_model()
        print(f"✓ Using Azure OpenAI model: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')}")
        
        # Initialize all metrics
        self.metrics = create_all_metrics(self.eval_model)
        print(f"✓ Initialized {len(self.metrics)} evaluation metrics")
        
        self.results = {
            "test_runs": [],
            "summary": {}
        }
    
    def create_db_connection(self):
        """Create PostgreSQL database connection"""
        try:
            connection = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                port=os.getenv("DB_PORT", "5432"),
                sslmode="require"
            )
            print("✓ Successfully connected to PostgreSQL database")
            return connection
        except Exception as e:
            print(f"✗ Error connecting to PostgreSQL: {e}")
            return None
    
    def run_single_metric_test(
        self,
        metric_name: str,
        test_case: LLMTestCase,
        description: str = ""
    ) -> Dict[str, Any]:
        """Run a single metric test with error handling and debug logging"""
        
        metric = self.metrics.get(metric_name)
        if not metric:
            return {"success": False, "error": f"Metric '{metric_name}' not found"}
        
        print(f"  Testing {metric_name}... ", end="", flush=True)
        
        try:
            metric.measure(test_case)
            score = metric.score
            passed = score >= THRESHOLDS.get(metric_name, 0.7) if score is not None else False
            
            if score is None:
                print(f"Score: None (ISSUE!)")
                return {
                    "success": False,
                    "metric": metric_name,
                    "score": None,
                    "error": "Metric returned None score",
                    "reason": getattr(metric, 'reason', None)
                }
            
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"Score: {score:.3f} {status}")
            
            return {
                "success": True,
                "metric": metric_name,
                "score": score,
                "threshold": THRESHOLDS.get(metric_name),
                "passed": passed,
                "reason": getattr(metric, 'reason', None)
            }
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "metric": metric_name,
                "error": str(e)
            }
    
    def run_all_tests(
        self,
        transcript: str = SAMPLE_TRANSCRIPT,
        meeting_id: str = "standalone-eval"
    ) -> Dict[str, Any]:
        """Run all 6 tests on a single transcript"""
        
        print("\n" + "="*60)
        print("RUNNING ALL 6 METRICS")
        print("="*60)
        
        # Generate summary
        print("\n📝 Generating summary...")
        start_time = time.time()
        summary = generate_summary(
            self.summary_service, transcript, meeting_id, self.conn
        )
        generation_time = time.time() - start_time
        print(f"  ✓ Summary generated ({generation_time:.2f}s, {len(summary)} chars)")
        
        results = {
            "meeting_id": meeting_id,
            "summary": summary,
            "generation_time": generation_time,
            "metrics": {}
        }
        
        # Test each metric
        print("\n🔍 Running metric evaluations...")
        
        # Initial delay to avoid rate limiting on first call
        print("[INFO] Initial delay before API calls...")
        time.sleep(RATE_LIMIT_DELAY)
        
        # 1. Faithfulness
        print("\n[1/6] Faithfulness")
        print(f"[DEBUG] Summary length for faithfulness test: {len(summary)} chars")
        print(f"[DEBUG] Transcript length: {len(transcript)} chars")
        tc = LLMTestCase(
            input="Summarize meeting",
            actual_output=summary,
            retrieval_context=[transcript]
        )
        print(f"[DEBUG] Test case created - actual_output present: {bool(tc.actual_output)}")
        print(f"[DEBUG] Test case created - retrieval_context count: {len(tc.retrieval_context)}")
        faithfulness_result = self.run_single_metric_test("faithfulness", tc)
        results["metrics"]["faithfulness"] = faithfulness_result
        
        # Extra debug for faithfulness issues
        if not faithfulness_result.get("success") or faithfulness_result.get("score") is None:
            print(f"[DEBUG] ⚠️ Faithfulness test issue detected!")
            print(f"[DEBUG]   success: {faithfulness_result.get('success')}")
            print(f"[DEBUG]   score: {faithfulness_result.get('score')}")
            print(f"[DEBUG]   error: {faithfulness_result.get('error')}")
            print(f"[DEBUG]   reason: {faithfulness_result.get('reason')}")
        
        time.sleep(RATE_LIMIT_DELAY)
        
        # 2. Summarization Completeness
        print("\n[2/6] Summarization Completeness")
        time.sleep(RATE_LIMIT_DELAY)
        tc = LLMTestCase(
            input="Check if summary contains all key information from the transcript",
            actual_output=summary,
            retrieval_context=[transcript]
        )
        results["metrics"]["summarization"] = self.run_single_metric_test("summarization", tc)
        
        # 3. Manual Coverage (no API call needed)
        print("\n[3/6] Manual Coverage")
        coverage = check_key_info_coverage(summary, SAMPLE_KEY_INFO)
        results["metrics"]["manual_coverage"] = {
            "success": True,
            "score": coverage["coverage_score"],
            "threshold": THRESHOLDS["coverage"],
            "passed": coverage["coverage_score"] >= THRESHOLDS["coverage"],
            "details": coverage
        }
        status = "✓ PASS" if coverage["coverage_score"] >= THRESHOLDS["coverage"] else "✗ FAIL"
        print(f"  Testing manual_coverage... Score: {coverage['coverage_score']:.3f} {status}")
        
        # 4. Financial Accuracy
        print("\n[4/6] Financial Accuracy")
        time.sleep(RATE_LIMIT_DELAY)
        tc = LLMTestCase(
            input="Summarize financial details",
            actual_output=summary,
            retrieval_context=[transcript]
        )
        results["metrics"]["financial_accuracy"] = self.run_single_metric_test("financial_accuracy", tc)
        
        # 5. Professional Tone
        print("\n[5/6] Professional Tone")
        time.sleep(RATE_LIMIT_DELAY)
        tc = LLMTestCase(
            input="Summarize professionally",
            actual_output=summary
        )
        results["metrics"]["tone"] = self.run_single_metric_test("tone", tc)
        
        # 6. Consistency (requires second summary)
        print("\n[6/6] Consistency")
        time.sleep(RATE_LIMIT_DELAY)
        summary2 = generate_summary(
            self.summary_service, transcript, f"{meeting_id}-run2", self.conn
        )
        time.sleep(RATE_LIMIT_DELAY)
        tc = LLMTestCase(
            input="Compare summaries",
            actual_output=summary2,
            expected_output=summary
        )
        results["metrics"]["consistency"] = self.run_single_metric_test("consistency", tc)
        
        self.results["test_runs"].append(results)
        
        return results
    
    def save_results(self, output_file: str = "summary_test_results.json"):
        """Save all test results to JSON file"""
        
        # Calculate summary statistics
        all_metrics = []
        for run in self.results["test_runs"]:
            for metric_name, metric_result in run.get("metrics", {}).items():
                if metric_result.get("success") and "score" in metric_result:
                    all_metrics.append({
                        "name": metric_name,
                        "score": metric_result["score"],
                        "passed": metric_result.get("passed", False)
                    })
        
        passed_count = sum(1 for m in all_metrics if m["passed"])
        
        self.results["summary"] = {
            "timestamp": datetime.now().isoformat(),
            "eval_model": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1"),
            "thresholds": THRESHOLDS,
            "total_metrics_run": len(all_metrics),
            "metrics_passed": passed_count,
            "metrics_failed": len(all_metrics) - passed_count,
            "pass_rate": passed_count / len(all_metrics) if all_metrics else 0
        }
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n✓ Results saved to {output_file}")
    
    def print_summary(self):
        """Print final test summary"""
        
        print("\n" + "="*60)
        print("FINAL TEST SUMMARY")
        print("="*60)
        
        if not self.results["test_runs"]:
            print("No test runs completed.")
            return
        
        # Collect ALL metrics (including failed ones)
        all_metrics = {}
        failed_metrics = {}
        
        for run in self.results["test_runs"]:
            for metric_name, result in run.get("metrics", {}).items():
                if result.get("success") and result.get("score") is not None:
                    if metric_name not in all_metrics:
                        all_metrics[metric_name] = []
                    all_metrics[metric_name].append(result)
                else:
                    # Track failed metrics
                    failed_metrics[metric_name] = result
        
        print(f"\n{'#':<3} {'Metric':<22} {'Score':<10} {'Threshold':<12} {'Status'}")
        print("-" * 60)
        
        test_num = 1
        for metric_name, results in all_metrics.items():
            avg_score = sum(r["score"] for r in results) / len(results)
            threshold = results[0].get("threshold", "N/A")
            passed = all(r.get("passed", False) for r in results)
            status = "✓ PASS" if passed else "✗ FAIL"
            
            threshold_str = f"{threshold:.2f}" if isinstance(threshold, float) else str(threshold)
            print(f"{test_num:<3} {metric_name:<22} {avg_score:<10.3f} {threshold_str:<12} {status}")
            test_num += 1
        
        # Show failed/errored metrics
        if failed_metrics:
            print("-" * 60)
            print("⚠️  FAILED/ERRORED METRICS:")
            for metric_name, result in failed_metrics.items():
                error = result.get("error", "Unknown error")
                reason = result.get("reason", "")
                print(f"    {metric_name}: {error}")
                if reason:
                    print(f"      Reason: {reason}")
        
        print("-" * 60)
        
        total_expected = 6  # We expect 6 tests
        total_run = len(all_metrics)
        passed = sum(1 for results in all_metrics.values() 
                    if all(r.get("passed", False) for r in results))
        
        print(f"\nTotal: {passed}/{total_run} metrics passed")
        
        if total_run < total_expected:
            print(f"⚠️  WARNING: Only {total_run}/{total_expected} tests completed successfully!")
            print(f"   Missing/failed tests: {total_expected - total_run}")
        
        print("="*60)


# ==================== MAIN EXECUTION ====================

def main():
    """Standalone execution with full detailed output"""
    
    # Verify configuration
    required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"✗ Missing environment variables: {', '.join(missing)}")
        print("\nRequired:")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_DEPLOYMENT_NAME (default: gpt-4.1)")
        return
    
    print("="*60)
    print("SUMMARY EVALUATION TEST SUITE (STREAMLINED)")
    print("DeepEval + Azure OpenAI")
    print("="*60)
    print(f"\nEndpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"Model: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')}")
    print(f"\nTests: 6 essential metrics")
    print(f"Thresholds: {json.dumps(THRESHOLDS, indent=2)}")
    
    print("\n📋 Test Suite:")
    print("  1. Faithfulness           - Claims grounded in transcript")
    print("  2. Summarization Complete - Key facts presence (no penalty for extra context)")
    print("  3. Manual Coverage        - Deterministic key info check")
    print("  4. Financial Accuracy     - Monetary data exactness")
    print("  5. Professional Tone      - Language appropriateness")
    print("  6. Consistency            - Cross-run stability")
    
    # Initialize test suite
    suite = SummaryTestSuite()
    suite.conn = suite.create_db_connection()
    
    # Run all metric tests
    suite.run_all_tests()
    
    # Save and print results
    suite.save_results()
    suite.print_summary()
    
    print("\n📊 View dashboard at: https://app.confident-ai.com")
    print("📊 View detailed results in: summary_test_results.json")
    
    if suite.conn:
        suite.conn.close()
        print("✓ Database connection closed")


if __name__ == "__main__":
    main()