"""
Summary Testing with DeepEval
Tests for grounding, completeness, and consistency of meeting summaries
"""

import os
import sys
import json
import time
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Import existing services
from services.summay_service import SummaryService
from services.meeting_service import MeetingService
from utils.db_utils import DatabaseUtils
import psycopg2
from dotenv import load_dotenv

load_dotenv()


class SummaryTestSuite:
    """Test suite for meeting summary generation"""
    
    def __init__(self, conn=None):
        self.summary_service = SummaryService()
        self.meeting_service = MeetingService()
        self.conn = conn
        
        # Initialize metrics
        self.faithfulness_metric = FaithfulnessMetric(threshold=0.95)
        self.recall_metric = ContextualRecallMetric(threshold=0.9)
        
        # For consistency testing
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.results = {
            "grounding": [],
            "completeness": [],
            "consistency": [],
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
    
    # ==================== TEST 1: GROUNDING/FAITHFULNESS ====================
    
    def test_grounding(self, test_cases: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Test 1: Grounding/Faithfulness
        Verify every claim in summary is supported by transcript
        
        Args:
            test_cases: List of dicts with 'transcript' and optionally 'meeting_id'
        
        Returns:
            Dict with test results and metrics
        """
        print("\n" + "="*60)
        print("TEST 1: GROUNDING/FAITHFULNESS")
        print("="*60)
        print(f"Running grounding tests on {len(test_cases)} transcripts...")
        
        deepeval_test_cases = []
        failed_cases = []
        
        for i, test_data in enumerate(test_cases, 1):
            transcript = test_data.get('transcript')
            meeting_id = test_data.get('meeting_id')
            
            print(f"\n[{i}/{len(test_cases)}] Generating summary...")
            
            try:
                # Generate summary using existing service
                start_time = time.time()
                summary = self.summary_service.generate_summary(
                    transcript=transcript,
                    meeting_id=meeting_id,
                    created_by="TEST_SYSTEM",
                    conn=self.conn
                )
                generation_time = time.time() - start_time
                
                print(f"  ✓ Summary generated ({generation_time:.2f}s)")
                print(f"  - Transcript length: {len(transcript)} chars")
                print(f"  - Summary length: {len(summary)} chars")
                
                # Create DeepEval test case
                test_case = LLMTestCase(
                    input="Summarize this meeting transcript",
                    actual_output=summary,
                    retrieval_context=[transcript]
                )
                
                deepeval_test_cases.append(test_case)
                
                # Store results
                self.results["grounding"].append({
                    "test_id": i,
                    "meeting_id": meeting_id,
                    "transcript_length": len(transcript),
                    "summary_length": len(summary),
                    "generation_time": generation_time,
                    "summary": summary,
                    "transcript": transcript
                })
                
            except Exception as e:
                print(f"  ✗ Failed to generate summary: {e}")
                failed_cases.append({
                    "test_id": i,
                    "meeting_id": meeting_id,
                    "error": str(e)
                })
        
        if not deepeval_test_cases:
            print("\n✗ No summaries generated successfully!")
            return {"success": False, "error": "No valid test cases"}
        
        # Run DeepEval faithfulness metric
        print(f"\n🔍 Running DeepEval FaithfulnessMetric (threshold=0.95)...")
        try:
            results = evaluate(deepeval_test_cases, [self.faithfulness_metric])
            
            # Extract scores
            scores = []
            for i, test_case in enumerate(deepeval_test_cases):
                score = self.faithfulness_metric.measure(test_case)
                scores.append(score)
                self.results["grounding"][i]["faithfulness_score"] = score
                
                status = "✓ PASS" if score >= 0.95 else "✗ FAIL"
                print(f"  [{i+1}] Faithfulness Score: {score:.3f} {status}")
            
            avg_score = sum(scores) / len(scores)
            pass_rate = sum(1 for s in scores if s >= 0.95) / len(scores)
            
            print(f"\n📊 GROUNDING TEST RESULTS:")
            print(f"  - Average Faithfulness Score: {avg_score:.3f}")
            print(f"  - Pass Rate (≥0.95): {pass_rate*100:.1f}%")
            print(f"  - Tests Passed: {sum(1 for s in scores if s >= 0.95)}/{len(scores)}")
            print(f"  - Tests Failed: {sum(1 for s in scores if s < 0.95)}/{len(scores)}")
            
            if failed_cases:
                print(f"  - Generation Failures: {len(failed_cases)}")
            
            return {
                "success": True,
                "avg_score": avg_score,
                "pass_rate": pass_rate,
                "total_tests": len(scores),
                "passed": sum(1 for s in scores if s >= 0.95),
                "failed": sum(1 for s in scores if s < 0.95),
                "scores": scores,
                "generation_failures": failed_cases
            }
            
        except Exception as e:
            print(f"\n✗ DeepEval evaluation failed: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== TEST 2: COMPLETENESS/COVERAGE ====================
    
    def test_completeness(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test 2: Completeness/Coverage
        Verify summary captures all important information
        
        Args:
            test_cases: List of dicts with:
                - 'transcript': meeting transcript
                - 'key_info': dict with critical info to check (optional)
                - 'reference_summary': expected summary (optional)
                - 'meeting_id': meeting ID (optional)
        
        Returns:
            Dict with test results and metrics
        """
        print("\n" + "="*60)
        print("TEST 2: COMPLETENESS/COVERAGE")
        print("="*60)
        print(f"Running completeness tests on {len(test_cases)} transcripts...")
        
        deepeval_test_cases = []
        manual_checks = []
        
        for i, test_data in enumerate(test_cases, 1):
            transcript = test_data.get('transcript')
            meeting_id = test_data.get('meeting_id')
            key_info = test_data.get('key_info', {})
            reference_summary = test_data.get('reference_summary')
            
            print(f"\n[{i}/{len(test_cases)}] Generating summary...")
            
            try:
                # Generate summary
                start_time = time.time()
                summary = self.summary_service.generate_summary(
                    transcript=transcript,
                    meeting_id=meeting_id,
                    created_by="TEST_SYSTEM",
                    conn=self.conn
                )
                generation_time = time.time() - start_time
                
                print(f"  ✓ Summary generated ({generation_time:.2f}s)")
                
                # If reference summary provided, use ContextualRecallMetric
                if reference_summary:
                    test_case = LLMTestCase(
                        input="Summarize meeting",
                        actual_output=summary,
                        expected_output=reference_summary,
                        retrieval_context=[transcript]
                    )
                    deepeval_test_cases.append(test_case)
                
                # Manual key info check
                if key_info:
                    coverage_results = self._check_key_info_coverage(
                        summary, key_info
                    )
                    manual_checks.append({
                        "test_id": i,
                        "meeting_id": meeting_id,
                        "coverage": coverage_results
                    })
                    
                    print(f"  - Key Info Coverage: {coverage_results['coverage_score']:.1%}")
                    print(f"    • Amounts: {coverage_results['amounts_covered']}/{coverage_results['amounts_total']}")
                    print(f"    • Dates: {coverage_results['dates_covered']}/{coverage_results['dates_total']}")
                    print(f"    • Decisions: {coverage_results['decisions_covered']}/{coverage_results['decisions_total']}")
                    print(f"    • Actions: {coverage_results['actions_covered']}/{coverage_results['actions_total']}")
                
                self.results["completeness"].append({
                    "test_id": i,
                    "meeting_id": meeting_id,
                    "summary": summary,
                    "transcript": transcript,
                    "generation_time": generation_time,
                    "key_info": key_info,
                    "manual_coverage": coverage_results if key_info else None
                })
                
            except Exception as e:
                print(f"  ✗ Failed: {e}")
        
        # Run DeepEval ContextualRecallMetric if reference summaries provided
        deepeval_scores = []
        if deepeval_test_cases:
            print(f"\n🔍 Running DeepEval ContextualRecallMetric (threshold=0.9)...")
            try:
                results = evaluate(deepeval_test_cases, [self.recall_metric])
                
                for i, test_case in enumerate(deepeval_test_cases):
                    score = self.recall_metric.measure(test_case)
                    deepeval_scores.append(score)
                    
                    status = "✓ PASS" if score >= 0.9 else "✗ FAIL"
                    print(f"  [{i+1}] Recall Score: {score:.3f} {status}")
                
                avg_recall = sum(deepeval_scores) / len(deepeval_scores)
                print(f"\n  Average Recall Score: {avg_recall:.3f}")
                
            except Exception as e:
                print(f"  ✗ DeepEval evaluation failed: {e}")
        
        # Summarize manual checks
        if manual_checks:
            avg_manual_coverage = sum(
                check['coverage']['coverage_score'] for check in manual_checks
            ) / len(manual_checks)
            
            print(f"\n📊 COMPLETENESS TEST RESULTS:")
            if deepeval_scores:
                print(f"  - DeepEval Recall Score: {sum(deepeval_scores)/len(deepeval_scores):.3f}")
            print(f"  - Manual Coverage Score: {avg_manual_coverage:.1%}")
            print(f"  - Tests with Full Coverage (100%): {sum(1 for c in manual_checks if c['coverage']['coverage_score'] == 1.0)}/{len(manual_checks)}")
            
            return {
                "success": True,
                "avg_recall_score": sum(deepeval_scores)/len(deepeval_scores) if deepeval_scores else None,
                "avg_manual_coverage": avg_manual_coverage,
                "manual_checks": manual_checks,
                "deepeval_scores": deepeval_scores
            }
        
        return {"success": True, "deepeval_scores": deepeval_scores}
    
    def _check_key_info_coverage(self, summary: str, key_info: Dict[str, List[str]]) -> Dict[str, Any]:
        """Check if key information appears in summary"""
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
        
        # Check amounts
        for amount in key_info.get('amounts', []):
            if amount.lower() in summary_lower:
                results['amounts_covered'] += 1
            else:
                results['missed_items'].append(f"Amount: {amount}")
        
        # Check dates
        for date in key_info.get('dates', []):
            if date.lower() in summary_lower:
                results['dates_covered'] += 1
            else:
                results['missed_items'].append(f"Date: {date}")
        
        # Check decisions
        for decision in key_info.get('decisions', []):
            if decision.lower() in summary_lower:
                results['decisions_covered'] += 1
            else:
                results['missed_items'].append(f"Decision: {decision}")
        
        # Check action items
        for action in key_info.get('action_items', []):
            if action.lower() in summary_lower:
                results['actions_covered'] += 1
            else:
                results['missed_items'].append(f"Action: {action}")
        
        # Calculate overall coverage
        total_items = (results['amounts_total'] + results['dates_total'] + 
                      results['decisions_total'] + results['actions_total'])
        covered_items = (results['amounts_covered'] + results['dates_covered'] + 
                        results['decisions_covered'] + results['actions_covered'])
        
        results['coverage_score'] = covered_items / total_items if total_items > 0 else 0
        
        return results
    
    # ==================== TEST 3: CONSISTENCY ====================
    
    def test_consistency(self, transcript: str, runs: int = 5, 
                        meeting_id: str = None) -> Dict[str, Any]:
        """
        Test 3: Consistency Across Runs
        Verify same transcript produces consistent summaries
        
        Args:
            transcript: Meeting transcript
            runs: Number of times to generate summary (default: 5)
            meeting_id: Optional meeting ID
        
        Returns:
            Dict with consistency metrics
        """
        print("\n" + "="*60)
        print("TEST 3: CONSISTENCY ACROSS RUNS")
        print("="*60)
        print(f"Generating {runs} summaries for consistency check...")
        
        summaries = []
        generation_times = []
        
        for i in range(1, runs + 1):
            print(f"\n[{i}/{runs}] Generating summary...")
            try:
                start_time = time.time()
                summary = self.summary_service.generate_summary(
                    transcript=transcript,
                    meeting_id=f"{meeting_id}_run{i}" if meeting_id else None,
                    created_by="TEST_SYSTEM",
                    conn=self.conn
                )
                generation_time = time.time() - start_time
                
                summaries.append(summary)
                generation_times.append(generation_time)
                
                print(f"  ✓ Summary generated ({generation_time:.2f}s, {len(summary)} chars)")
                
            except Exception as e:
                print(f"  ✗ Failed: {e}")
                return {"success": False, "error": str(e)}
        
        # Test 1: All summaries should have high faithfulness
        print(f"\n🔍 Testing faithfulness for all {runs} runs...")
        faithfulness_scores = []
        
        for i, summary in enumerate(summaries, 1):
            test_case = LLMTestCase(
                input="Summarize",
                actual_output=summary,
                retrieval_context=[transcript]
            )
            
            score = self.faithfulness_metric.measure(test_case)
            faithfulness_scores.append(score)
            
            status = "✓ PASS" if score >= 0.95 else "✗ FAIL"
            print(f"  [{i}] Faithfulness: {score:.3f} {status}")
        
        # Test 2: Check similarity between summaries
        print(f"\n🔍 Calculating similarity between summaries...")
        embeddings = self.embedding_model.encode(summaries)
        similarity_matrix = cosine_similarity(embeddings)
        
        # Get average similarity (excluding diagonal)
        n = len(summaries)
        avg_similarity = (similarity_matrix.sum() - n) / (n * (n - 1))
        
        print(f"\n📊 CONSISTENCY TEST RESULTS:")
        print(f"  - Average Faithfulness: {sum(faithfulness_scores)/len(faithfulness_scores):.3f}")
        print(f"  - All Runs Pass Faithfulness (≥0.95): {all(s >= 0.95 for s in faithfulness_scores)}")
        print(f"  - Average Cosine Similarity: {avg_similarity:.3f}")
        print(f"  - Consistency Pass (≥0.85 similarity): {avg_similarity >= 0.85}")
        print(f"  - Average Generation Time: {sum(generation_times)/len(generation_times):.2f}s")
        
        # Show pairwise similarities
        print(f"\n  Pairwise Similarity Matrix:")
        for i in range(n):
            print(f"    Run {i+1}:", end="")
            for j in range(n):
                print(f" {similarity_matrix[i][j]:.3f}", end="")
            print()
        
        self.results["consistency"] = {
            "transcript": transcript,
            "summaries": summaries,
            "faithfulness_scores": faithfulness_scores,
            "similarity_matrix": similarity_matrix.tolist(),
            "avg_similarity": avg_similarity,
            "generation_times": generation_times
        }
        
        return {
            "success": True,
            "avg_faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
            "all_pass_faithfulness": all(s >= 0.95 for s in faithfulness_scores),
            "avg_similarity": avg_similarity,
            "consistency_pass": avg_similarity >= 0.85,
            "num_runs": runs,
            "faithfulness_scores": faithfulness_scores,
            "similarity_matrix": similarity_matrix.tolist()
        }
    
    # ==================== SAVE RESULTS ====================
    
    def save_results(self, output_file: str = "summary_test_results.json"):
        """Save all test results to JSON file"""
        self.results["summary"] = {
            "timestamp": datetime.now().isoformat(),
            "total_grounding_tests": len(self.results["grounding"]),
            "total_completeness_tests": len(self.results["completeness"]),
            "consistency_tested": bool(self.results["consistency"])
        }
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n✓ Results saved to {output_file}")


# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage of test suite"""
    
    # Initialize test suite
    suite = SummaryTestSuite()
    suite.conn = suite.create_db_connection()
    
    # ==================== PREPARE TEST DATA ====================
    
    # Example 1: Test with sample transcript
    sample_transcript = """
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
    
    # ==================== TEST 1: GROUNDING ====================
    
    grounding_test_cases = [
        {"transcript": sample_transcript, "meeting_id": "TEST_001"}
    ]
    
    grounding_results = suite.test_grounding(grounding_test_cases)
    
    # ==================== TEST 2: COMPLETENESS ====================
    
    completeness_test_cases = [
        {
            "transcript": sample_transcript,
            "meeting_id": "TEST_002",
            "key_info": {
                "amounts": ["$500,000", "$300,000", "$200,000", "$2 million", "$500/month", "$600,000"],
                "dates": ["age 60", "15 years", "next week"],
                "decisions": ["increase CPF contributions", "term life insurance"],
                "action_items": ["send detailed proposal", "schedule follow-up meeting"]
            }
        }
    ]
    
    completeness_results = suite.test_completeness(completeness_test_cases)
    
    # ==================== TEST 3: CONSISTENCY ====================
    
    consistency_results = suite.test_consistency(
        transcript=sample_transcript,
        runs=5,
        meeting_id="TEST_003"
    )
    
    # ==================== SAVE RESULTS ====================
    
    suite.save_results("summary_test_results.json")
    
    # ==================== PRINT FINAL SUMMARY ====================
    
    print("\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60)
    
    if grounding_results.get("success"):
        print(f"✓ GROUNDING: {grounding_results['pass_rate']*100:.1f}% pass rate")
    
    if completeness_results.get("success"):
        if completeness_results.get("avg_manual_coverage"):
            print(f"✓ COMPLETENESS: {completeness_results['avg_manual_coverage']*100:.1f}% coverage")
    
    if consistency_results.get("success"):
        print(f"✓ CONSISTENCY: {consistency_results['avg_similarity']*100:.1f}% similarity")
    
    print("="*60)
    
    if suite.conn:
        suite.conn.close()
        print("✓ Database connection closed")


if __name__ == "__main__":
    main()