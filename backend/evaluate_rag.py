"""
evaluate_rag.py
---------------
Automated RAG evaluation suite. Evaluates the retriever accuracy across typical
VIT-AP queries. Can be executed locally or inside CI pipelines to verify updates
don't introduce regressions or hallucinations.

Usage:
    python evaluate_rag.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag.retriever import QdrantRetriever

# Simple evaluation dataset: typical queries & their expected target words/sources
EVAL_DATASET = [
    {
        "query": "who is dean of SCOPE?",
        "expected_keywords": ["sudhakar", "ilango", "school of computer science"],
        "min_score": 0.60
    },
    {
        "query": "how do I schedule my OS classes?",
        "expected_keywords": ["ffcs", "v-top", "faculty", "slot"],
        "min_score": 0.50
    },
    {
        "query": "what is the highest package offered at placements?",
        "expected_keywords": ["93", "lpa", "highest", "package"],
        "min_score": 0.65
    },
    {
        "query": "what is the library opening time?",
        "expected_keywords": ["library", "8 am", "10 pm"],
        "min_score": 0.45
    },
    {
        "query": "is there any ATM or bank on campus?",
        "expected_keywords": ["sbi", "atm", "bank"],
        "min_score": 0.60
    },
    {
        "query": "what is the hostel fee structure?",
        "expected_keywords": ["hostel", "mess", "fees", "1,08,000"],
        "min_score": 0.60
    },
    {
        "query": "who is SENSE dean?",
        "expected_keywords": ["pavan", "kumar", "electronics"],
        "min_score": 0.50
    }
]

def main():
    print("=" * 60)
    print("      vitap-UniOs RAG Ingestion & Query Evaluator")
    print("=" * 60)

    try:
        retriever = QdrantRetriever()
    except Exception as e:
        print(f"❌ Failed to initialize QdrantRetriever: {e}")
        sys.exit(1)

    passed_count = 0
    total_count = len(EVAL_DATASET)

    for i, test in enumerate(EVAL_DATASET):
        q = test["query"]
        expected = test["expected_keywords"]
        min_s = test["min_score"]

        print(f"\n🔍 Test {i+1}/{total_count}: '{q}'")
        
        # Retrieve top 1
        results = retriever.retrieve(q, top_k=1)
        if not results:
            print("  ❌ FAIL: No chunk retrieved")
            continue
            
        hit = results[0]
        title = hit.get("title", "")
        content = hit.get("content", "").lower()
        score = hit.get("score", 0.0)

        # 1. Match score check
        score_ok = score >= min_s
        # 2. Keywords presence check
        keywords_matched = [k for k in expected if k in content or k in title.lower()]
        keywords_ok = len(keywords_matched) > 0

        print(f"  Retrieved Title: '{title}'")
        print(f"  Score: {score:.2f} (Required: >= {min_s:.2f})")
        print(f"  Keywords Matched: {keywords_matched} / {expected}")

        if score_ok and keywords_ok:
            print("  ✅ PASS")
            passed_count += 1
        else:
            reasons = []
            if not score_ok:
                reasons.append(f"Score too low ({score:.2f} < {min_s:.2f})")
            if not keywords_ok:
                reasons.append(f"No expected keywords matched (expected one of: {expected})")
            print(f"  ❌ FAIL: {', '.join(reasons)}")

    print("\n" + "=" * 60)
    print(f"Evaluation Complete: {passed_count}/{total_count} Passed ({passed_count/total_count*100:.1f}%)")
    print("=" * 60)

    if passed_count < total_count:
        print("⚠️ Some evaluation tests failed. Check retrieval parameters.")
        sys.exit(1)
    else:
        print("🎉 All evaluation tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
