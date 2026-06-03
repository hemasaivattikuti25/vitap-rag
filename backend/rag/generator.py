"""
Answer generator for CampusOS.
Supports dynamic routing, local vector search, real-time web search fallback, and streaming.
No Gemini dependency.
"""

import os
import json
import asyncio
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

Scope and Accuracy Guidelines:
- Your responses MUST stay strictly in the context of VIT-AP University (Amaravathi, Andhra Pradesh).
- Never mix up or provide details from other VIT campuses (such as VIT Vellore, VIT Chennai, or VIT Bhopal). If retrieved context mentions other campuses, ignore those parts and focus strictly on VIT-AP.
- If you are unsure whether a fact is about VIT-AP or another campus, prioritize the VIT-AP facts or state that you do not have verified information for VIT-AP.

Safety and Tone Guidelines:
- Never use bad, offensive, profane, or unethical words.
- Always use positive, clean, polite, and constructive language.
- Respond directly and confidently. Never say "Based on the provided sources..." or "Unfortunately, the sources do not contain...".
- If the context does not contain the answer, use your general knowledge about VIT-AP to provide a helpful answer, but do not make up specific details like phone numbers or links.
"""

def is_false_positive(query: str, doc_content: str, doc_title: str) -> bool:
    q = query.lower().strip()
    c = (doc_content + " " + doc_title).lower()
    
    # Placements query vs non-placement doc
    if any(w in q for w in ["placement", "cdc", "job", "salary", "placed", "recruit", "career", "super dream"]):
        if not any(w in c for w in ["placement", "cdc", "job", "salary", "placed", "recruit", "career", "super dream", "offer", "company"]):
            return True
            
    # Fee query vs non-fee doc
    if any(w in q for w in ["fee", "fees", "cost", "price", "tuition", "scholarship"]):
        if not any(w in c for w in ["fee", "fees", "cost", "price", "tuition", "scholarship", "rupees", "lakh", "paid"]):
            return True
            
    # Hostel query vs non-hostel doc
    if any(w in q for w in ["hostel", "hostels", "mess", "room", "laundry", "canteen"]):
        if not any(w in c for w in ["hostel", "hostels", "mess", "room", "laundry", "canteen", "accommodation", "warden"]):
            return True
            
    # Sports query vs non-sports doc
    if any(w in q for w in ["sport", "sports", "gym", "game", "badminton", "cricket"]):
        if not any(w in c for w in ["sport", "sports", "gym", "game", "badminton", "cricket", "court", "fitness"]):
            return True
            
    return False

async def check_relevance(query: str, docs: List[dict]) -> List[dict]:
    """
    Check retrieved documents against user query using a fast LLM pass to filter out false positives.
    """
    if not docs or not _groq_client:
        return docs

    doc_entries = []
    for i, doc in enumerate(docs):
        # Limit content length to save tokens and keep it fast
        content_snippet = doc.get("content", "")[:350]
        title = doc.get("title", "")
        doc_entries.append(f"Document {i}:\nTitle: {title}\nContent: {content_snippet}")

    docs_text = "\n\n".join(doc_entries)
    
    prompt = f"""You are a precise search relevance filter.
Evaluate if the following retrieved documents contain information relevant to answering the User Query.
A document is relevant only if it directly addresses the query's topic or contains information that can help answer it.
If a document is about a completely different topic (e.g. query is about academic blocks, but document is about hostels/mess), it is NOT relevant.

User Query: "{query}"

Retrieved Documents:
{docs_text}

Respond with a JSON list containing the indices of the relevant documents (e.g., [0, 2] or []). Do not include any explanations, markdown code blocks, or extra text. Output ONLY the JSON list."""

    try:
        completion = await _groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.0,
            timeout=4.0
        )
        resp_text = completion.choices[0].message.content.strip()
        
        # Strip markdown code blocks if the model wrapped it in ```json ... ```
        if "```" in resp_text:
            resp_text = resp_text.split("```")[1]
            if resp_text.startswith("json"):
                resp_text = resp_text[4:]
        
        indices = json.loads(resp_text.strip())
        if isinstance(indices, list):
            return [docs[idx] for idx in indices if isinstance(idx, int) and 0 <= idx < len(docs)]
    except Exception as e:
        print(f"[generator] Relevance check failed: {e}. Falling back to original documents.")
    return docs

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
        # Determine query classification
        is_general = check_is_general(query)
        print(f"[generator] Query classified as is_general = {is_general}")

    has_opinions = False
    context_section = ""

    if not is_identity:
        if is_general:
            context_section = "Use your general knowledge to answer directly."
        else:
            # Run local Qdrant retrieval first (takes ~50-100ms)
            print(f"[generator] Running local Qdrant retrieval for: '{query[:50]}'")
            local_docs = await asyncio.to_thread(retriever.retrieve, query, 5)
            
            # Pre-filter local docs for base score and structural false positives
            user_wants_opinions = any(w in q_lower for w in ["reddit", "opinion", "review", "sentiment", "student say", "think about"])
            candidates = []
            for d in local_docs:
                if d["score"] < 0.26:
                    continue
                # Exclude cross-domain false positive semantic matches (e.g. sports pages matching placements)
                if is_false_positive(query, d.get("content", ""), d.get("title", "")):
                    print(f"[generator] Excluding false positive local chunk '{d['title']}' for query '{query[:30]}'")
                    continue
                is_opinion_source = d.get("category") == "student_opinion" or "reddit.com" in d.get("source_url", "").lower()
                # Exclude student opinions/Reddit comments for general factual queries
                if is_opinion_source and not user_wants_opinions:
                    print(f"[generator] Excluding local opinion chunk '{d['title']}' to ensure factual accuracy.")
                    continue
                candidates.append(d)

            # Check relevance of candidates using fast LLM filter
            relevant_local = []
            if candidates:
                print(f"[generator] Running LLM relevance filter on {len(candidates)} candidates...")
                relevant_local = await check_relevance(query, candidates)
                print(f"[generator] LLM relevance filter kept {len(relevant_local)} of {len(candidates)} candidates.")
            else:
                print(f"[generator] No candidate documents to filter.")

            # Check if we have high-confidence matches (score >= 0.40) from official pages
            has_high_confidence = any(
                d["score"] >= 0.40 and not (d.get("category") == "student_opinion" or "reddit.com" in d.get("source_url", "").lower())
                for d in relevant_local
            )
            
            web_docs = []
            if not has_high_confidence:
                max_score = max([d["score"] for d in relevant_local]) if relevant_local else 0.0
                print(f"[generator] No high-confidence local results (max score: {max_score:.4f}). Running web search...")
                web_docs = await web_search(query)
            else:
                print(f"[generator] Found high-confidence local results (score >= 0.40). Skipping web search to minimize latency.")
            
            context_parts = []
            
            # 1. Add Web Search results (highly prioritized for real-time accurate information)
            if web_docs:
                web_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in web_docs)
                context_parts.append(f"Web Search Results:\n{web_text}")
                citations.extend(d["source_url"] for d in web_docs)
                
            # 2. Add verified relevant local Qdrant documents
            if relevant_local:
                official_info = []
                student_opinions = []
                for d in relevant_local:
                    if d.get("category") == "student_opinion" or "reddit.com" in d.get("source_url", ""):
                        student_opinions.append(d)
                    else:
                        official_info.append(d)
                        
                if official_info:
                    off_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in official_info)
                    context_parts.append(f"Official Campus Documents:\n{off_text}")
                if student_opinions:
                    op_text = "\n\n".join(f"Source: {d['source_url']}\nContent: {d['content']}" for d in student_opinions)
                    context_parts.append(f"Student Opinions & Reviews:\n{op_text}")
                    has_opinions = True
                    
                citations.extend(d["source_url"] for d in relevant_local if d.get("source_url"))
                
            # Remove duplicate citations
            citations = list(set(citations))
            
            if context_parts:
                context_section = "\n\n".join(context_parts)
            else:
                print("[generator] Both Web Search and Local Qdrant returned 0 relevant results. Falling back to general knowledge.")
                context_section = "Use your general knowledge about VIT-AP to answer. Be helpful, clean, and polite."
                is_general = True

    # Build dynamic prompt messages
    messages = []
    
    if is_identity:
        system_instruction = (
            "You are vitap-UniOs, an intelligent campus companion for VIT-AP University students, developed by Hemasai Vattikuti. "
            "Hemasai Vattikuti is a Backend & Applied AI Engineer and an alumnus of VIT-AP University. "
            "Always state clearly that you were developed by Hemasai Vattikuti when asked about your creator, developer, or creator's details."
        )
    elif is_general:
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
