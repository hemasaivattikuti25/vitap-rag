"""
Answer generator for CampusOS.
Supports dynamic routing, local vector search, real-time web search fallback, and streaming.
No Gemini dependency.
"""

import os
import json
from typing import Tuple, List, Optional

from rag.retriever import QdrantRetriever
from rag.web_search import web_search, check_is_general
from rag.cache import answer_cache

# ── Groq SDK ──────────────────────────────────────────────────
try:
    from groq import AsyncGroq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

# ── Keys ───────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── Groq models (in fallback order) ───────────────────────────
GROQ_MODELS = [
    "llama-3.1-8b-instant",       # fastest, 14,400/day
    "llama-3.3-70b-versatile",    # high performance 70B
    "mixtral-8x7b-32768",         # fallback MoE model
]

# Initialize clients
_groq_client = AsyncGroq(api_key=GROQ_API_KEY) if _HAS_GROQ and GROQ_API_KEY else None
retriever = QdrantRetriever()

# ── Base System Prompt ──────────────────────────────────────────
BASE_SYSTEM_PROMPT = """You are vitap-UniOs, an intelligent, helpful, and highly accurate AI chatbot for VIT-AP University students.

Developer & System Info:
- You are developed by Hemasai Vattikuti, a Backend & Applied AI Engineer and an alumnus of VIT-AP University.
- Always credit Hemasai Vattikuti when asked about your developer, creator, or who made you.

Safety and Tone Guidelines:
- Never use bad, offensive, profane, or unethical words.
- Always use positive, clean, polite, and constructive language.
- Respond directly and confidently. Never say "Based on the provided sources..." or "Unfortunately, the sources do not contain...".
- If the context does not contain the answer, use your general knowledge about VIT-AP to provide a helpful answer, but do not make up specific details like phone numbers or links.
"""

async def generate_answer_stream(query: str, history: Optional[List[dict]] = None):
    """
    Generate response token by token in SSE format.
    Yields data in format: 'data: {"text": "..."}' or 'data: {"citations": [...]}'
    """
    if not _groq_client:
        yield f"data: {json.dumps({'text': '⚠️ Groq client is not initialized. Please check GROQ_API_KEY in backend/.env'})}\n\n"
        yield f"data: {json.dumps({'citations': []})}\n\n"
        return

    # Check cache (only for single-turn queries)
    if not history:
        cached = answer_cache.get(query)
        if cached:
            cached_ans, cached_cites = cached
            print(f"[generator] Cache hit for query: '{query[:50]}'")
            # Yield in chunks to simulate rapid streaming feel
            chunk_size = 50
            for i in range(0, len(cached_ans), chunk_size):
                yield f"data: {json.dumps({'text': cached_ans[i:i+chunk_size]})}\n\n"
            yield f"data: {json.dumps({'citations': cached_cites})}\n\n"
            return

    # 1. Check for developer or bot identity queries to respond instantly and accurately
    identity_context = None
    is_identity = False
    citations: List[str] = []
    
    q_lower = query.lower().strip()
    # Check for developer questions
    is_dev_query = any(k in q_lower for k in ["developer", "developed you", "created you", "made you", "who programmed you", "who coded you", "creator of", "who is hemasai", "hemasai vattikuti", "hemasai vatteikuit", "vattikuti"])
    # Check for bot name / identity questions
    is_bot_query = any(k in q_lower for k in ["who are you", "what are you", "your name", "what is vitap-unios", "what is unios", "about vitap-unios", "tell me about vitap-unios", "tell me about unios"])
    
    if is_dev_query:
        identity_context = (
            "vitap-UniOs is developed by Hemasai Vattikuti. "
            "Hemasai Vattikuti is a Backend & Applied AI Engineer and an alumnus of VIT-AP University. "
            "He built this platform to improve the campus experience for students by bringing together "
            "real-time feeds, chatbot assistance, and community details."
        )
        citations = ["https://github.com/hemasaivattikuti", "https://in.linkedin.com/in/hemasaivattikuti"]
        is_identity = True
    elif is_bot_query:
        identity_context = (
            "You are vitap-UniOs, an intelligent campus companion for VIT-AP University students, developed by Hemasai Vattikuti. "
            "You help students with real-time feeds, club events, placement updates, academic calendars, and campus details."
        )
        citations = ["https://vitap.ac.in"]
        is_identity = True

    docs = []
    max_score = 0.0
    filtered_docs = []
    is_general = False
    
    if is_identity:
        context_section = identity_context
        is_general = True
    else:
        # 2. Retrieve local docs from Qdrant
        docs = retriever.retrieve(query, top_k=5)
        max_score = max([d["score"] for d in docs]) if docs else 0.0
        print(f"[generator] Query: '{query[:50]}' | Local Qdrant max score: {max_score:.4f}")
        
        # Keep only docs that are reasonably relevant (score >= 0.30) to prevent mixing irrelevant facts
        filtered_docs = [d for d in docs if d["score"] >= 0.30]
        
        # Determine query classification
        is_general = check_is_general(query)
        print(f"[generator] Query classified as is_general = {is_general}")

    has_opinions = False
    context_section = ""

    if not is_identity:
        # If not a greeting/math/code and local score is low, trigger Web Search fallback
        if not is_general and max_score < 0.32:
            print(f"[generator] Low local score ({max_score:.4f} < 0.32). Triggering Web Search Fallback for: '{query[:50]}'")
            web_docs = await web_search(query)
            if web_docs:
                context_text = "\n\n".join(
                    f"Source: {d['source_url']}\nContent: {d['content']}" for d in web_docs
                )
                context_section = f"Use the following web search results to answer accurately:\n\n{context_text}"
                citations = [d["source_url"] for d in web_docs]
            else:
                # Web search failed -> Use filtered local docs if they are reasonably relevant
                if filtered_docs:
                    print(f"[generator] Web search failed. Falling back to {len(filtered_docs)} filtered local docs (max score: {max_score:.4f})")
                    official_info = []
                    student_opinions = []
                    for d in filtered_docs:
                        if d.get("category") == "student_opinion" or "reddit.com" in d.get("source_url", ""):
                            student_opinions.append(d)
                        else:
                            official_info.append(d)

                    citations = list(set(d["source_url"] for d in filtered_docs if d.get("source_url")))

                    context_parts = []
                    if official_info:
                        off_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in official_info)
                        context_parts.append(f"Official University Information:\n{off_text}")
                    if student_opinions:
                        op_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in student_opinions)
                        context_parts.append(f"Student Opinions:\n{op_text}")
                        has_opinions = True

                    context_section = "\n\n".join(context_parts)
                else:
                    print(f"[generator] Web search failed and no relevant local docs found. Falling back to general knowledge.")
                    context_section = "Use your general knowledge about VIT-AP to answer. Be helpful, clean, and polite."
                    citations = []
                    is_general = True  # Bypasses strict bullet formatting to avoid empty sections
        else:
            # Use local Qdrant docs (high score)
            if filtered_docs:
                official_info = []
                student_opinions = []
                for d in filtered_docs:
                    if d.get("category") == "student_opinion" or "reddit.com" in d.get("source_url", ""):
                        student_opinions.append(d)
                    else:
                        official_info.append(d)

                citations = list(set(d["source_url"] for d in filtered_docs if d.get("source_url")))

                context_parts = []
                if official_info:
                    off_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in official_info)
                    context_parts.append(f"Official University Information:\n{off_text}")
                if student_opinions:
                    op_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in student_opinions)
                    context_parts.append(f"Student Opinions (Reddit, Instagram, Google reviews):\n{op_text}")
                    has_opinions = True

                context_section = "\n\n".join(context_parts)
            else:
                context_section = "Use your general knowledge to answer."

    # Build dynamic prompt messages
    messages = []
    
    if is_general:
        system_instruction = BASE_SYSTEM_PROMPT + "\nAnswer the question DIRECTLY, naturally, and concisely. Do NOT use the VIT-AP facts/sentiments formatting. Just answer directly (e.g. '2 + 2 = 4'). Do NOT mention VIT-AP unless asked."
    else:
        if has_opinions:
            system_instruction = BASE_SYSTEM_PROMPT + """
Structure your response for this query exactly as follows:
1. **Official Facts**: Clear, specific, bulleted facts from the provided official context.
2. **Student Sentiments & Reddit Opinion**: Summary of student opinions and reviews from the provided context (e.g. from student_opinions.json or Reddit/Google review snippets).
"""
        else:
            system_instruction = BASE_SYSTEM_PROMPT + """
Structure your response for this query exactly as follows:
1. **Official Facts**: Clear, specific, bulleted facts from the provided official context.

CRITICAL: Do NOT include a section for 'Student Sentiments' or 'Reddit Opinion' because no student reviews or opinions are available for this topic in the retrieved context. Only output the '**Official Facts**' section. Do NOT write any fallback sentences complaining about lack of reviews.
"""

    messages.append({"role": "system", "content": system_instruction})

    if history:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    user_msg = f"{context_section}\n\nStudent's Question: {query}\n\nAnswer:"
    messages.append({"role": "user", "content": user_msg})

    # Try Groq models in fallback order
    stream_success = False
    for model in GROQ_MODELS:
        try:
            print(f"[generator] Requesting stream from AsyncGroq/{model}")
            completion = await _groq_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=800,
                temperature=0.3,
                timeout=10.0,
                stream=True
            )

            full_answer = ""
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_answer += token
                    yield f"data: {json.dumps({'text': token})}\n\n"

            stream_success = True
            print(f"[generator] AsyncGroq/{model} stream completed")
            
            # Cache the successful response
            if not history and full_answer:
                answer_cache.set(query, full_answer, citations)
            break
        except Exception as e:
            err = str(e)
            print(f"[generator] AsyncGroq/{model} stream failed: {err[:120]}")
            if "rate_limit" in err.lower() or "429" in err:
                continue  # try next model
            continue

    if not stream_success:
        yield f"data: {json.dumps({'text': '⚠️ All AI services are currently overloaded. Please try again shortly.'})}\n\n"

    # Send citations at the end
    yield f"data: {json.dumps({'citations': citations})}\n\n"


async def generate_answer(query: str, history: Optional[List[dict]] = None) -> Tuple[str, List[str]]:
    """
    Non-streaming fallback (used for compatibility or testing).
    """
    generator = generate_answer_stream(query, history)
    full_text = ""
    citations = []
    
    async for chunk in generator:
        if chunk.startswith("data: "):
            try:
                data = json.loads(chunk[6:].strip())
                if "text" in data:
                    full_text += data["text"]
                if "citations" in data:
                    citations = data["citations"]
            except Exception:
                pass
                
    return full_text, citations
