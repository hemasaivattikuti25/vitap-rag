import asyncio
import os
import sys
import time
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from rag.generator import classify_query_with_llm, retriever
from rag.web_search import check_is_general

# Define the 17 test cases
TEST_CASES = [
    # --- Category 1: Faculty Factual Queries (Expect FACTUAL + specific name/profile) ---
    {
        "id": 1,
        "query": "Where is Dr. Srinivas S's office?",
        "expected_category": "FACTUAL",
        "expected_url_contains": "srinivas.s"
    },
    {
        "id": 2,
        "query": "What is the education of Dr. Srinivas S?",
        "expected_category": "FACTUAL",
        "expected_url_contains": "srinivas.s"
    },
    {
        "id": 3,
        "query": "How to contact Dr. Mary Chandini Stephens?",
        "expected_category": "FACTUAL",
        "expected_url_contains": "marychandini.y"
    },
    {
        "id": 4,
        "query": "What is the email of Dr. Nagarjuna Neella?",
        "expected_category": "FACTUAL",
        "expected_url_contains": "nagarjuna.n"
    },
    # --- Category 2: Campus Institutional Queries (Expect FACTUAL) ---
    {
        "id": 5,
        "query": "Who is the Vice-Chancellor of VIT-AP?",
        "expected_category": "FACTUAL",
        "expected_url_contains": None
    },
    {
        "id": 6,
        "query": "What is the fee structure for B.Tech CSE?",
        "expected_category": "FACTUAL",
        "expected_url_contains": None
    },
    {
        "id": 7,
        "query": "Tell me about the hostel facilities at VIT-AP.",
        "expected_category": "FACTUAL",
        "expected_url_contains": None
    },
    {
        "id": 8,
        "query": "What placements statistics does the Career Development Centre have?",
        "expected_category": "FACTUAL",
        "expected_url_contains": None
    },
    {
        "id": 9,
        "query": "Are there student coding clubs like Google DSC at VIT-AP?",
        "expected_category": "FACTUAL",
        "expected_url_contains": None
    },
    # --- Category 3: Greetings & Identity (Expect GENERAL/Identity) ---
    {
        "id": 10,
        "query": "Hello, who are you?",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    {
        "id": 11,
        "query": "hey there! good morning",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    # --- Category 4: Conversational Critique & Feedback (Expect GENERAL) ---
    {
        "id": 12,
        "query": "you do not know anything",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    {
        "id": 13,
        "query": "that answer is incorrect",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    {
        "id": 14,
        "query": "you are wrong",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    # --- Category 5: Out of Scope / General Knowledge Tasks (Expect GENERAL) ---
    {
        "id": 15,
        "query": "calculate 150 * 3 + 25",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    {
        "id": 16,
        "query": "write a python function to check prime numbers",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    },
    {
        "id": 17,
        "query": "explain the theory of general relativity briefly",
        "expected_category": "GENERAL",
        "expected_url_contains": None
    }
]

async def run_test(case: dict) -> bool:
    query = case["query"]
    expected_cat = case["expected_category"]
    expected_url = case["expected_url_contains"]
    
    # 1. Determine classification (Keyword -> LLM fallback)
    is_gen_keyword = check_is_general(query)
    is_gen = is_gen_keyword
    if not is_gen:
        is_gen = await classify_query_with_llm(query)
        
    actual_cat = "GENERAL" if is_gen else "FACTUAL"
    class_ok = (actual_cat == expected_cat)
    
    # 2. Check retrieval if factual + expecting specific url keyword
    retrieval_ok = True
    retrieved_sources = []
    
    if expected_url and actual_cat == "FACTUAL":
        docs = retriever.retrieve(query, top_k=3)
        retrieved_sources = [d.get("source_url", "") for d in docs]
        retrieval_ok = any(expected_url in url.lower() for url in retrieved_sources)
        
    passed = class_ok and retrieval_ok
    
    status_symbol = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{case['id']:02d}] Query: '{query}'")
    print(f"     Expected: {expected_cat} | Actual: {actual_cat} -> Classification: {'OK' if class_ok else 'WRONG'}")
    if expected_url:
        print(f"     Expected URL Contains: '{expected_url}' | Retrieved URLs: {retrieved_sources} -> Retrieval: {'OK' if retrieval_ok else 'FAILED'}")
    print(f"     Result: {status_symbol}\n")
    
    return passed

async def main():
    print("=" * 65)
    print("         vitap-UniOs chatbot - 17 Integration Test Cases")
    print("=" * 65)
    
    start_time = time.time()
    passed_count = 0
    
    for case in TEST_CASES:
        # Avoid hitting rate limits by sleeping 100ms between LLM calls
        await asyncio.sleep(0.1)
        success = await run_test(case)
        if success:
            passed_count += 1
            
    end_time = time.time()
    print("=" * 65)
    print(f"Test Summary: Passed {passed_count}/{len(TEST_CASES)} tests.")
    print(f"Total time elapsed: {end_time - start_time:.4f} seconds.")
    print("=" * 65)
    
    if passed_count == len(TEST_CASES):
        print("🎉 ALL 17 TEST CASES PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("⚠️ SOME TEST CASES FAILED. Please review the errors.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
