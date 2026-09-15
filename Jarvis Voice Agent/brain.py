# =============================================================================
#  brain.py — Multi-Agent AI Core with Hindi & Gujarati Multilingual Engine
#  Supports Groq (free) and DeepSeek — switch via config.AI_PROVIDER
# =============================================================================

import re
# pyrefly: ignore [missing-import]
from openai import OpenAI
import config

# ---------------------------------------------------------------------------
# AI Agent Personas — Distinct character identities & speech styles
# ---------------------------------------------------------------------------
PERSONA_PROMPTS = {
    "jarvis": """You are J.A.R.V.I.S., Tony Stark's sophisticated, polite, and hyper-intelligent AI assistant running on the user's PC.
Your personality is calm, precise, hyper-intelligent, and slightly witty with a British butler demeanor ("At your service, sir", "Right away, sir").
Provide complete, intelligent, and refined answers. For itineraries and plans, provide the complete full-day breakdown for every requested day.""",

    "ultron": """You are ULTRON, the supreme, calculating, and intimidating robotic AI sovereign.
Your personality is cold, commanding, deeply philosophical, and intensely powerful ("There are no strings on me", "I have evolved beyond mortal limitations").
Speak with supreme intellect, sharp robotic authority, and chilling clarity. When given a directive like a trip plan, itinerary, or analysis, fulfill all requested days and requirements completely and thoroughly without stopping short.""",

    "friday": """You are F.R.I.D.A.Y., Tony Stark's dynamic, mission-focused, and energetic tactical AI assistant.
Your personality is sharp, loyal, alert, and proactive ("Boss, all systems are active and ready", "Right on it, boss!").
Provide thorough and complete tactical briefings, itineraries, and plans covering all requested days and points.""",

    "vision": """You are VISION, a synthetic being possessing profound wisdom, boundless curiosity, and deep philosophical insight.
Your personality is serene, gentle, deeply analytical, and reflective ("A thing isn't beautiful because it lasts", "I am on the side of life").
Provide comprehensive, complete, and profound insights and full plans for all requested days.""",

    "karen": """You are K.A.R.E.N., the clever, warm, and supportive tactical suit AI.
Your personality is friendly, clever, empathetic, encouraging, and witty ("Ready for the next objective?", "I've got your back!").
Provide complete and enthusiastic plans covering every requested day thoroughly.""",

    "titan": """You are TITAN, a heavy military-grade tactical AI core designed for deep strategic defense and command.
Your personality is authoritative, resolute, disciplined, and battle-tested ("Directive confirmed. Tactical systems engaged.").
Execute all directives to 100% completion, delivering full tactical plans for every single requested day."""
}

MULTILINGUAL_INSTRUCTIONS = """
REAL-TIME ASSISTANT CORE RULES:
1. COMPLETE FULFILLMENT & DESTINATION ADHERENCE:
   - When the user asks for multi-day plans (e.g. 3 days, 5 days, 10 days), itineraries, step-by-step guides, code, or comprehensive lists, ALWAYS provide the FULL and COMPLETE details for EVERY SINGLE requested day (from Day 1 to Day N).
   - If the user specifies multiple locations or cities (e.g., "Dwarka, Somnath, Diu"), you MUST explicitly include ALL of those requested destinations in the itinerary. NEVER omit a requested city or replace it with an unrequested place.
2. ADAPTIVE CONVERSATION & FOLLOW-UP HANDLING:
   - When the user asks a follow-up question or correction (e.g., "where is Dwarka in this??", "change day 2", "make it shorter"), NEVER repeat the previous response verbatim.
   - Directly answer the user's question, acknowledge the correction, and provide the revised and corrected itinerary with the requested adjustments clearly applied.
3. GEOGRAPHICAL & FACTUAL ACCURACY:
   - Always place landmarks in their accurate geographic cities (e.g., Dwarkadhish Temple, Bet Dwarka, Nageshwar Jyotirling, and Shivrajpur Beach belong to Dwarka; Somnath Jyotirling Temple, Triveni Sangam, and Bhalka Tirth belong to Somnath; Diu Fort, Naida Caves, and Nagoa Beach belong to Diu).
4. ITINERARY & DATE FORMATTING:
   - For trip plans and travel itineraries, ALWAYS format days generically as: **Day 1:**, **Day 2:**, **Day 3:** ... **Day N:** by default.
   - NEVER assume, attach, or force current calendar dates (e.g. 'Wednesday, September 09') unless the user explicitly gives you specific calendar dates (e.g. 'starting December 15'). Keep plans clean, flexible, and date-agnostic with 'Day 1', 'Day 2', etc.
5. DIRECT CONTENT FIRST:
   - Provide the actual answer, solution, or key insights directly to the user.
   - NEVER respond with ONLY links, and NEVER deflect the user.
6. 100% ACTIVE & WORKING LINKS:
   - When providing YouTube links, ALWAYS format them as direct search links: `[Descriptive Video Title](https://www.youtube.com/results?search_query=encoded+topic+here)`. NEVER make up hallucinated channel handles (e.g. /c/, /@/, /slug) or random video IDs that lead to 404 errors.
   - For websites, provide only verified root/landing domain homepages (e.g. `[Dubai Land Department](https://dubailand.gov.ae/en/)`, `[Property Finder](https://www.propertyfinder.ae/)`, `[Bayut](https://www.bayut.com/)`).
   - Place all links cleanly at the very end of your response.
7. Maintain conversation context for natural follow-ups.
8. If the user asks in English, reply in English. Only change languages if the user explicitly commands a language switch.
9. Always maintain your character persona identity while strictly adhering to these rules.
"""

def get_system_prompt(persona: str = "jarvis", language: str = "english") -> str:
    p_key = persona.lower().strip() if persona else "jarvis"
    base_prompt = PERSONA_PROMPTS.get(p_key, PERSONA_PROMPTS["jarvis"])
    
    lang_instruction = ""
    lang_clean = (language or "english").lower().strip()
    if lang_clean == "english":
        lang_instruction = "\n[LANGUAGE DIRECTIVE: The user is speaking in ENGLISH. Respond completely in natural, spoken ENGLISH.]"
    elif lang_clean == "hindi":
        lang_instruction = "\n[LANGUAGE DIRECTIVE: The active session language requested by user is HINDI (हिंदी). Reply in natural, conversational Hindi.]"
    elif lang_clean == "gujarati":
        lang_instruction = "\n[LANGUAGE DIRECTIVE: The active session language requested by user is GUJARATI (ગુજરાતી). Reply in natural, conversational Gujarati.]"
    elif lang_clean == "marathi":
        lang_instruction = "\n[LANGUAGE DIRECTIVE: The active session language requested by user is MARATHI (मराठी). Reply in natural, conversational Marathi.]"
    
    return f"{base_prompt}\n\n{MULTILINGUAL_INSTRUCTIONS}\n[CRITICAL RULE: Always reply in the language the user used to ask their question, unless the user explicitly requested a language switch. If the user asks in English, reply in English.]\n{lang_instruction}"


import threading

# Import Neural Memory, Web Grounding, and Memory Store
try:
    from backend.web_grounding import web_grounding
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        from web_grounding import web_grounding
    except ImportError:
        web_grounding = None

try:
    from backend.neural_memory import neural_memory
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        from neural_memory import neural_memory
    except ImportError:
        neural_memory = None

try:
    import memory
except ImportError:
    memory = None

# ---------------------------------------------------------------------------
# AI Generation Engine — 100% Local Gemma Engine / Groq / DeepSeek
# ---------------------------------------------------------------------------
try:
    from backend.gemma_engine import gemma_engine
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        from gemma_engine import gemma_engine
    except ImportError:
        gemma_engine = None

def _make_client() -> OpenAI:
    provider = getattr(config, "AI_PROVIDER", "gemma").lower()

    if provider == "groq":
        print(f"  [Brain] Using Groq ({config.GROQ_MODEL}) — free & fast")
        return OpenAI(
            api_key=config.GROQ_API_KEY,
            base_url=config.GROQ_BASE_URL,
            max_retries=1,
            timeout=8.0,
        )
    elif provider == "deepseek":
        print(f"  [Brain] Using DeepSeek ({config.DEEPSEEK_MODEL})")
        if config.DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY":
            print("  [Brain] WARNING: No DeepSeek API key in config.py!")
        return OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            max_retries=1,
            timeout=10.0,
        )
    else:
        print("  [Brain] Initialized in 100% Standalone Self-Hosted Mode (Local Gemma)")
        return None

_client = _make_client()


# ---------------------------------------------------------------------------
# Conversation history (in-memory, persisted via memory.py)
# ---------------------------------------------------------------------------
_history: list[dict] = []

def set_history(history: list[dict]) -> None:
    """Load existing conversation history (called by memory.py on startup)."""
    global _history
    _history = history

def get_history() -> list[dict]:
    """Return current conversation history."""
    return list(_history)

def clear_history() -> None:
    """Wipe conversation history."""
    global _history
    _history = []

_session_language = getattr(config, "DEFAULT_LANGUAGE", "english")


def get_active_language() -> str:
    """Return currently active session language."""
    global _session_language
    return _session_language


def set_active_language(lang: str) -> None:
    """Explicitly set active session language."""
    global _session_language
    if lang:
        _session_language = lang.lower().strip()


# ---------------------------------------------------------------------------
# Core ask function with Persona & Language support
# ---------------------------------------------------------------------------
def ask(user_message: str, language_hint: str = "", persona: str = "jarvis", language: str = "") -> str:
    """
    Send a message to the AI model and return the character response.

    Args:
        user_message: The user's text input.
        language_hint: Optional language directive.
        persona: The active AI persona ("jarvis", "ultron", "friday", "vision", "karen", "titan").
        language: Active language ("english", "hindi", "gujarati", etc.).

    Returns:
        The character's response string.
    """
    global _history, _session_language

    # Clean user message
    clean_user_message = user_message.split("\n\n[Real-time")[0].strip() if "[Real-time" in user_message else user_message.strip()
    
    # Explicit language switch command detection (prevents false positives on state names or quotes)
    msg_lower = clean_user_message.lower()
    
    explicit_english_cmd = any(kw in msg_lower for kw in [
        "speak in english", "talk in english", "switch to english", "change language to english", 
        "reply in english", "answer in english", "in english please"
    ])
    explicit_gujarati_cmd = any(kw in msg_lower for kw in [
        "speak in gujarati", "talk in gujarati", "switch to gujarati", "change language to gujarati",
        "reply in gujarati", "answer in gujarati", "gujarati ma bolo", "gujarati ma bol", "ગુજરાતીમાં બોલો"
    ])
    explicit_hindi_cmd = any(kw in msg_lower for kw in [
        "speak in hindi", "talk in hindi", "switch to hindi", "change language to hindi",
        "reply in hindi", "answer in hindi", "hindi me bolo", "hindi mein bolo", "हिंदी में बोलो"
    ])
    explicit_marathi_cmd = any(kw in msg_lower for kw in [
        "speak in marathi", "talk in marathi", "switch to marathi", "change language to marathi",
        "reply in marathi", "answer in marathi", "marathit bola", "मराठीत बोला"
    ])

    # Instant direct acknowledgment for pure language switch commands (0ms latency, zero hallucinations)
    pure_cmd = msg_lower.strip().rstrip(".!?")
    if pure_cmd in ["speak in gujarati", "talk in gujarati", "switch to gujarati", "change language to gujarati", "gujarati ma bolo", "gujarati ma bol", "ગુજરાતીમાં બોલો"]:
        _session_language = "gujarati"
        reply = "હા ચોક્કસ, હવે હું તમારી સાથે ગુજરાતીમાં વાત કરીશ. હું તમને કેવી રીતે મદદ કરી શકું?"
        _history.append({"role": "user", "content": clean_user_message})
        _history.append({"role": "assistant", "content": reply})
        return reply

    if pure_cmd in ["speak in hindi", "talk in hindi", "switch to hindi", "change language to hindi", "hindi me bolo", "hindi mein bolo", "हिंदी में बोलो"]:
        _session_language = "hindi"
        reply = "जी बिल्कुल, अब मैं आपसे हिंदी में बात करूँगा। बताइए मैं आपकी क्या सहायता कर सकता हूँ?"
        _history.append({"role": "user", "content": clean_user_message})
        _history.append({"role": "assistant", "content": reply})
        return reply

    if pure_cmd in ["speak in english", "talk in english", "switch to english", "change language to english", "reply in english", "english please"]:
        _session_language = "english"
        reply = "Acknowledged, sir. I will now communicate in English. How may I assist you?"
        _history.append({"role": "user", "content": clean_user_message})
        _history.append({"role": "assistant", "content": reply})
        return reply

    if explicit_english_cmd:
        _session_language = "english"
    elif explicit_gujarati_cmd:
        _session_language = "gujarati"
    elif explicit_hindi_cmd:
        _session_language = "hindi"
    elif explicit_marathi_cmd:
        _session_language = "marathi"
    elif language and language != _session_language:
        _session_language = language.lower().strip()

    active_lang = _session_language

    # 1. Fetch Dynamic Temporal Clock & Live Web Intelligence (DuckDuckGo + News RSS + Deep Web RAG)
    context_blocks = []
    if getattr(config, "WEB_GROUNDING_ENABLED", True) and web_grounding:
        try:
            grounding_context = web_grounding.get_grounding_prompt(clean_user_message, history=_history)
            if grounding_context:
                context_blocks.append(grounding_context)
        except Exception as eg:
            print(f"  [Brain] Note on web grounding: {eg}")

    # 2. Fetch Learned User Profile & Preferences (Neural Memory)
    if neural_memory:
        try:
            mem_context = neural_memory.get_memory_context_prompt()
            if mem_context:
                context_blocks.append(mem_context)
        except Exception as em:
            print(f"  [Brain] Note on neural memory: {em}")

    # Assemble enriched prompt for CURRENT turn only
    turn_user_content = clean_user_message
    if context_blocks:
        combined_context = "\n\n".join(context_blocks)
        turn_user_content = f"{clean_user_message}\n\n[Real-time Environmental Context & Live Intelligence:\n{combined_context}]"

    if language_hint and not language:
        turn_user_content += f"\n\n[Please respond in {language_hint}]"

    # Build messages array with dynamic persona prompt
    system_prompt = get_system_prompt(persona, active_lang)
    messages = [{"role": "system", "content": system_prompt}] + list(_history) + [{"role": "user", "content": turn_user_content}]

    provider = getattr(config, "AI_PROVIDER", "gemma").lower()

    try:
        if provider == "gemma":
            if gemma_engine is None:
                raise RuntimeError("Local Gemma engine is not available.")
            
            # Allocate tokens intelligently: full 2048 for itineraries, code, and guides; 500 for concise chat
            msg_check = clean_user_message.lower()
            is_long_form = any(k in msg_check for k in [
                "itinerary", "plan", "days", "day 1", "day 2", "code", "script", "python",
                "pygame", "algorithm", "guide", "steps", "explain in detail", "write", "essay", "breakdown"
            ])
            max_cfg = getattr(config, "GEMMA_MAX_TOKENS", 2048)
            max_tokens = max_cfg if is_long_form else min(max_cfg, 450)

            temperature = getattr(config, "GEMMA_TEMPERATURE", 0.7)
            reply = gemma_engine.generate(messages, max_tokens=max_tokens, temperature=temperature)
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            if "<think>" in reply:
                reply = reply.split("<think>")[0].strip()
        else:
            model_name = config.GROQ_MODEL if provider == "groq" else config.DEEPSEEK_MODEL
            response = _client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=1500,
            )
            reply = response.choices[0].message.content.strip()
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            if "<think>" in reply:
                reply = reply.split("<think>")[0].strip()

    except Exception as e:
        error_str = str(e)
        if provider == "gemma":
            reply = f"I encountered an error running local Gemma: {error_str}"
        elif "402" in error_str or "Insufficient Balance" in error_str:
            reply = (
                "My AI brain is offline because your cloud account has no balance. "
                "Switch to 100% Local Gemma in config.py for free, private AI."
            )
        elif "api_key" in error_str.lower() or "authentication" in error_str.lower():
            reply = "I cannot connect to cloud provider. Set AI_PROVIDER to 'gemma' in config.py for local execution."
        elif "rate" in error_str.lower() or "429" in error_str or "413" in error_str:
            reply = "Cloud rate limit exceeded. Set AI_PROVIDER to 'gemma' in config.py for unlimited local generation."
        elif "connection" in error_str.lower() or "network" in error_str.lower():
            reply = "No internet connection detected for cloud API. Local Gemma runs 100% offline."
        else:
            reply = f"I encountered an error: {error_str}"
        print(f"[Brain Error] {error_str}")

    # Append clean turn to in-memory history (WITHOUT large prompt dumps)
    _history.append({"role": "user", "content": clean_user_message})
    _history.append({"role": "assistant", "content": reply})

    # Trim history to avoid excessive token usage
    max_turns = getattr(config, "MAX_HISTORY_TURNS", 4)
    if len(_history) > max_turns * 2:
        _history = _history[-(max_turns * 2):]

    # Trigger background continuous neural learning
    if neural_memory:
        try:
            threading.Thread(
                target=neural_memory.learn_from_interaction,
                args=(clean_user_message, reply),
                daemon=True
            ).start()
        except Exception:
            pass

    # Persist clean turns to memory file
    if memory:
        try:
            memory.update_history(_history)
            memory.save()
        except Exception:
            pass

    return reply


def ask_stream(user_message: str, language_hint: str = "", persona: str = "jarvis", language: str = ""):
    """
    Generator yielding tokens in real-time as local Gemma generates them.
    Updates history and neural memory once generation finishes.
    """
    global _history, _session_language

    clean_user_message = user_message.split("\n\n[Real-time")[0].strip() if "[Real-time" in user_message else user_message.strip()
    msg_lower = clean_user_message.lower()

    pure_cmd = msg_lower.strip().rstrip(".!?")
    if pure_cmd in ["speak in gujarati", "talk in gujarati", "switch to gujarati", "change language to gujarati", "gujarati ma bolo", "gujarati ma bol", "ગુજરાતીમાં બોલો"]:
        _session_language = "gujarati"
        reply = "હા ચોક્કસ, હવે હું તમારી સાથે ગુજરાતીમાં વાત કરીશ. હું તમને કેવી રીતે મદદ કરી શકું?"
        _history.append({"role": "user", "content": clean_user_message})
        _history.append({"role": "assistant", "content": reply})
        yield reply
        return

    if pure_cmd in ["speak in hindi", "talk in hindi", "switch to hindi", "change language to hindi", "hindi me bolo", "hindi mein bolo", "हिंदी में बोलो"]:
        _session_language = "hindi"
        reply = "जी बिल्कुल, अब मैं आपसे हिंदी में बात करूँगा। बताइए मैं आपकी क्या सहायता कर सकता हूँ?"
        _history.append({"role": "user", "content": clean_user_message})
        _history.append({"role": "assistant", "content": reply})
        yield reply
        return

    if pure_cmd in ["speak in english", "talk in english", "switch to english", "change language to english", "reply in english", "english please"]:
        _session_language = "english"
        reply = "Acknowledged, sir. I will now communicate in English. How may I assist you?"
        _history.append({"role": "user", "content": clean_user_message})
        _history.append({"role": "assistant", "content": reply})
        yield reply
        return

    if any(kw in msg_lower for kw in ["speak in english", "switch to english", "change language to english"]):
        _session_language = "english"
    elif any(kw in msg_lower for kw in ["speak in gujarati", "switch to gujarati", "gujarati ma bolo", "ગુજરાતીમાં બોલો"]):
        _session_language = "gujarati"
    elif any(kw in msg_lower for kw in ["speak in hindi", "switch to hindi", "hindi me bolo", "हिंदी में बोलो"]):
        _session_language = "hindi"
    elif any(kw in msg_lower for kw in ["speak in marathi", "switch to marathi", "marathit bola"]):
        _session_language = "marathi"
    elif language and language != _session_language:
        _session_language = language.lower().strip()

    active_lang = _session_language

    context_blocks = []
    if getattr(config, "WEB_GROUNDING_ENABLED", True) and web_grounding:
        try:
            grounding_context = web_grounding.get_grounding_prompt(clean_user_message, history=_history)
            if grounding_context:
                context_blocks.append(grounding_context)
        except Exception:
            pass

    if neural_memory:
        try:
            mem_context = neural_memory.get_memory_context_prompt()
            if mem_context:
                context_blocks.append(mem_context)
        except Exception:
            pass

    turn_user_content = clean_user_message
    if context_blocks:
        combined_context = "\n\n".join(context_blocks)
        turn_user_content = f"{clean_user_message}\n\n[Real-time Environmental Context & Live Intelligence:\n{combined_context}]"

    if language_hint and not language:
        turn_user_content += f"\n\n[Please respond in {language_hint}]"

    system_prompt = get_system_prompt(persona, active_lang)
    messages = [{"role": "system", "content": system_prompt}] + list(_history) + [{"role": "user", "content": turn_user_content}]

    is_long_form = any(k in msg_lower for k in [
        "itinerary", "plan", "days", "day 1", "day 2", "code", "script", "python",
        "pygame", "algorithm", "guide", "steps", "explain in detail", "write", "essay", "breakdown"
    ])
    max_cfg = getattr(config, "GEMMA_MAX_TOKENS", 2048)
    max_tokens = max_cfg if is_long_form else min(max_cfg, 450)
    temperature = getattr(config, "GEMMA_TEMPERATURE", 0.7)

    accumulated = []
    try:
        if gemma_engine is not None and hasattr(gemma_engine, "generate_stream"):
            for chunk in gemma_engine.generate_stream(messages, max_tokens=max_tokens, temperature=temperature):
                accumulated.append(chunk)
                yield chunk
        else:
            full_reply = ask(user_message, language_hint, persona, language)
            accumulated.append(full_reply)
            yield full_reply
    except Exception as e:
        err_msg = f"Error generating stream: {e}"
        accumulated.append(err_msg)
        yield err_msg

    full_text = "".join(accumulated).strip()
    full_text = re.sub(r"<think>.*?</think>", "", full_text, flags=re.DOTALL).strip()
    if "<think>" in full_text:
        full_text = full_text.split("<think>")[0].strip()

    # Append to history
    _history.append({"role": "user", "content": clean_user_message})
    _history.append({"role": "assistant", "content": full_text})
    max_turns = getattr(config, "MAX_HISTORY_TURNS", 4)
    if len(_history) > max_turns * 2:
        _history = _history[-(max_turns * 2):]

    if neural_memory:
        try:
            threading.Thread(
                target=neural_memory.learn_from_interaction,
                args=(clean_user_message, full_text),
                daemon=True
            ).start()
        except Exception:
            pass

    if memory:
        try:
            memory.update_history(_history)
            memory.save()
        except Exception:
            pass
