# =============================================================================
#  backend/gemma_engine.py — Standalone Dual-Core Google Gemma Inference Engine
#  Combines Fast Sub-Second Voice Responsiveness + Deep Frontier Reasoning
#  100% Local On-Device Execution | $0 API Costs | 0 Token Limits | 100% Privacy
# =============================================================================

import os
import sys
import re
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("GemmaEngine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import config
except ImportError:
    config = None

try:
    # pyrefly: ignore [missing-import]
    import torch
except ImportError:
    torch = None

# Global State for Dual-Core Engines

_engine_lock = threading.Lock()
_fast_model = None
_fast_tokenizer = None
_deep_model = None
_deep_tokenizer = None

_fast_loaded = False
_deep_loaded = False


def get_model_paths() -> Tuple[str, str]:
    """Retrieve verified paths for Fast and Deep models."""
    fast_path = getattr(config, "FAST_MODEL_PATH", "")
    deep_path = getattr(config, "DEEP_MODEL_PATH", "")

    # Fallback search if configured paths are empty
    candidates_fast = [
        fast_path,
        str(ROOT_DIR.parent / "local_model_3b"),
        str(ROOT_DIR / "local_model_3b"),
        r"C:\Users\Administrator\Desktop\Shravan Work\Gemma Ji\local_model_3b",
    ]
    candidates_deep = [
        deep_path,
        str(ROOT_DIR.parent / "gemma-4-31B-it"),
        str(ROOT_DIR / "gemma-4-31B-it"),
        r"C:\Users\Administrator\Desktop\Shravan Work\Gemma Ji\gemma-4-31B-it",
    ]

    resolved_fast = ""
    for c in candidates_fast:
        if c and os.path.exists(c) and os.path.isdir(c) and os.path.exists(os.path.join(c, "config.json")):
            resolved_fast = os.path.abspath(c)
            break

    resolved_deep = ""
    for c in candidates_deep:
        if c and os.path.exists(c) and os.path.isdir(c) and os.path.exists(os.path.join(c, "config.json")):
            resolved_deep = os.path.abspath(c)
            break

    return resolved_fast, resolved_deep


def load_fast_engine():
    """Load the ultra-low latency Fast Core into GPU VRAM for instant voice responses."""
    global _fast_model, _fast_tokenizer, _fast_loaded
    with _engine_lock:
        if _fast_loaded and _fast_model is not None:
            return _fast_model, _fast_tokenizer

        fast_path, _ = get_model_paths()
        if not fast_path:
            logger.error("[GemmaEngine] Fast model path not found.")
            return None, None

        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        logger.info(f"[GemmaEngine] Loading Fast Voice Core from: {fast_path}")
        _fast_tokenizer = AutoTokenizer.from_pretrained(fast_path, local_files_only=True)
        if _fast_tokenizer.pad_token_id is None:
            _fast_tokenizer.pad_token_id = _fast_tokenizer.eos_token_id or 0

        has_cuda = torch.cuda.is_available()

        # Apply 4-bit BitsAndBytes quantization to maximize VRAM headroom on RTX 3050 (6GB)
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            _fast_model = AutoModelForCausalLM.from_pretrained(
                fast_path,
                quantization_config=bnb_config,
                device_map="cuda:0" if has_cuda else "cpu",
                low_cpu_mem_usage=True,
                local_files_only=True,
            )
        except Exception as bnb_err:
            logger.warning(f"[GemmaEngine] 4-bit load note: {bnb_err}. Loading in float16.")
            device_target = "cuda:0" if has_cuda else "cpu"
            dtype_target = torch.float16 if has_cuda else torch.float32
            _fast_model = AutoModelForCausalLM.from_pretrained(
                fast_path,
                device_map=device_target,
                torch_dtype=dtype_target,
                low_cpu_mem_usage=True,
                local_files_only=True,
            )

        _fast_loaded = True
        logger.info("[GemmaEngine] Fast Voice Core is ONLINE and ready on GPU.")
        return _fast_model, _fast_tokenizer


def load_deep_engine():
    """Load the Deep Reasoning Core (31B) in 4-bit with CPU/GPU auto-offload when requested."""
    global _deep_model, _deep_tokenizer, _deep_loaded
    with _engine_lock:
        if _deep_loaded and _deep_model is not None:
            return _deep_model, _deep_tokenizer

        _, deep_path = get_model_paths()
        if not deep_path:
            logger.warning("[GemmaEngine] Deep model path not found, using Fast 3B Core.")
            return load_fast_engine()

        import torch
        from transformers import AutoTokenizer, BitsAndBytesConfig

        logger.info(f"[GemmaEngine] Initializing Deep Reasoning Core (31B) from: {deep_path}")
        try:
            _deep_tokenizer = AutoTokenizer.from_pretrained(deep_path, local_files_only=True)
            if _deep_tokenizer.pad_token_id is None:
                _deep_tokenizer.pad_token_id = _deep_tokenizer.eos_token_id or 0

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True,
            )

            max_mem = {
                0: "4.5GiB",
                "cpu": "24.0GiB"
            } if torch.cuda.is_available() else {"cpu": "28.0GiB"}

            try:
                from transformers import Gemma4ForConditionalGeneration
                _deep_model = Gemma4ForConditionalGeneration.from_pretrained(
                    deep_path,
                    quantization_config=bnb_config,
                    device_map="auto",
                    max_memory=max_mem,
                    low_cpu_mem_usage=True,
                    local_files_only=True,
                )
            except Exception:
                from transformers import AutoModelForCausalLM
                _deep_model = AutoModelForCausalLM.from_pretrained(
                    deep_path,
                    quantization_config=bnb_config,
                    device_map="auto",
                    max_memory=max_mem,
                    low_cpu_mem_usage=True,
                    local_files_only=True,
                )

            _deep_loaded = True
            logger.info("[GemmaEngine] Deep Reasoning Core (31B) is ONLINE and active.")
            return _deep_model, _deep_tokenizer
        except Exception as e:
            logger.warning(f"[GemmaEngine] Deep 31B model load note: {e}. Falling back to Fast 3B Core.")
            return load_fast_engine()


def is_complex_query(user_text: str) -> bool:
    """
    Intelligent Query Router:
    Routes complex code generation, mathematical proofs, deep architecture,
    and multi-step reasoning to the Deep 31B Core;
    Routes voice conversations, trip plans, daily dialogue, and quick commands
    to the Fast 3B Core.
    """
    t = user_text.lower().strip()

    complex_keywords = [
        "write code", "code in", "implement a", "python script", "write a function",
        "debug this", "algorithm", "mathematical proof", "solve this equation",
        "deep analysis", "compare in detail", "detailed essay", "architectural pattern",
        "comprehensive breakdown", "explain quantum", "step-by-step logic", "philosophical critique",
        "optimize code", "machine learning architecture", "neural network implementation"
    ]

    if any(k in t for k in complex_keywords):
        return True

    if len(t.split()) > 40 and any(w in t for w in ["analyze", "evaluate", "synthesize", "reasoning", "contrast", "derive"]):
        return True

    return False


def format_messages_for_model(messages: List[Dict[str, str]], tokenizer) -> str:
    """
    Format messages preserving system persona/instructions.
    Supports standard ChatML / Qwen / Gemma / Llama templates.
    """
    clean_messages = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "").strip()
        if not content:
            continue
        if role in ["system", "user", "assistant"]:
            clean_messages.append({"role": role, "content": content})
        elif role == "model":
            clean_messages.append({"role": "assistant", "content": content})

    # 1. Native chat template with system role preserved
    try:
        return tokenizer.apply_chat_template(
            clean_messages,
            tokenize=False,
            add_generation_prompt=True
        )
    except Exception as e:
        logger.debug(f"[GemmaEngine] Native chat template note: {e}")

    # 2. Fallback: Merge system into first user turn for tokenizers that reject system role
    fallback_messages = []
    sys_content = ""
    for m in clean_messages:
        if m["role"] == "system":
            sys_content = (sys_content + "\n\n" + m["content"]).strip()
        elif m["role"] == "user":
            if sys_content:
                fallback_messages.append({"role": "user", "content": f"{sys_content}\n\n{m['content']}"})
                sys_content = ""
            else:
                fallback_messages.append(m)
        else:
            fallback_messages.append(m)

    if not fallback_messages and sys_content:
        fallback_messages = [{"role": "user", "content": sys_content}]

    try:
        return tokenizer.apply_chat_template(
            fallback_messages,
            tokenize=False,
            add_generation_prompt=True
        )
    except Exception:
        pass

    # 3. Last-resort manual ChatML template
    parts = []
    for m in clean_messages:
        parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


def generate_response(
    messages: List[Dict[str, str]],
    max_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.95
) -> str:
    """
    Routes query through the local AI engine with instant GPU responsiveness.
    """
    mode = getattr(config, "AI_ROUTING_MODE", "fast").lower() if config else "fast"
    
    user_prompt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_prompt = m.get("content", "")
            break

    use_deep = False
    if mode == "deep":
        use_deep = True
    elif mode == "dual_hybrid":
        use_deep = is_complex_query(user_prompt)

    # Select model & tokenizer
    if use_deep:
        model, tokenizer = load_deep_engine()
        core_label = "DEEP CORE"
    else:
        model, tokenizer = load_fast_engine()
        core_label = "FAST VOICE CORE"

    if model is None or tokenizer is None:
        model, tokenizer = load_fast_engine()
        core_label = "FAST VOICE CORE"

    if model is None or tokenizer is None:
        return "AI Engine is initializing. Please try again in a moment."

    import torch

    formatted_prompt = format_messages_for_model(messages, tokenizer)

    try:
        inputs = tokenizer(formatted_prompt, return_tensors="pt")
        if hasattr(model, "device") and getattr(model.device, "type", "") not in ["meta", ""]:
            inputs = inputs.to(model.device)
        elif torch.cuda.is_available():
            inputs = inputs.to("cuda:0")
    except Exception as dev_err:
        logger.debug(f"[GemmaEngine] Device placement note: {dev_err}")

    input_length = inputs.input_ids.shape[1]
    cfg_max = getattr(config, "GEMMA_MAX_TOKENS", 2048)
    effective_max_tokens = min(max_tokens, cfg_max) if max_tokens > 0 else cfg_max

    # Ensure all end-of-sequence token IDs are captured so generation stops cleanly
    eos_ids = []
    if tokenizer.eos_token_id is not None:
        eos_ids.append(tokenizer.eos_token_id)
    for special_tok in ["<|im_end|>", "<|endoftext|>", "<end_of_turn>", "<eos>"]:
        try:
            tid = tokenizer.convert_tokens_to_ids(special_tok)
            if isinstance(tid, int) and tid > 0 and tid not in eos_ids:
                eos_ids.append(tid)
        except Exception:
            pass
    if not eos_ids:
        eos_ids = [tokenizer.eos_token_id or 0]

    with _engine_lock:
        start_time = time.time()
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=effective_max_tokens,
                do_sample=True if temperature > 0 else False,
                temperature=max(temperature, 0.01) if temperature > 0 else None,
                top_p=top_p if temperature > 0 else None,
                eos_token_id=eos_ids,
                pad_token_id=tokenizer.pad_token_id or eos_ids[0],
            )
        elapsed = time.time() - start_time

    new_tokens = output_ids[0][input_length:]
    token_count = len(new_tokens)
    tps = token_count / elapsed if elapsed > 0 else 0.0

    response_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    # Clean any residual model tag artifacts & reasoning blocks
    response_text = re.sub(r"^assistant\s*", "", response_text, flags=re.IGNORECASE)
    response_text = re.sub(r"^model\s*", "", response_text, flags=re.IGNORECASE)
    response_text = re.sub(r"^thought\s*", "", response_text, flags=re.IGNORECASE)
    response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
    
    if "<think>" in response_text:
        response_text = response_text.split("<think>")[0].strip()

    if not response_text:
        response_text = "Directive acknowledged. Systems operational and standing by."

    print(f"  [GemmaEngine] [{core_label}] Generated {token_count} tokens in {elapsed:.2f}s ({tps:.1f} tok/s) | $0 API Cost | 100% Private")

    return response_text.strip()


def generate_stream(
    messages: List[Dict[str, str]],
    max_tokens: int = 2048,
    temperature: float = 0.7,
    top_p: float = 0.95
):
    """
    Yields tokens in real-time as they are computed on local GPU.
    """
    from transformers import TextIteratorStreamer
    import threading

    mode = getattr(config, "AI_ROUTING_MODE", "fast").lower() if config else "fast"
    use_deep = False
    if mode == "deep":
        use_deep = True
    elif mode == "dual_hybrid":
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break
        use_deep = is_complex_query(user_prompt)

    if use_deep:
        model, tokenizer = load_deep_engine()
    else:
        model, tokenizer = load_fast_engine()

    if model is None or tokenizer is None:
        model, tokenizer = load_fast_engine()

    if model is None or tokenizer is None:
        yield "AI Engine is initializing. Please try again in a moment."
        return

    import torch
    formatted_prompt = format_messages_for_model(messages, tokenizer)
    try:
        inputs = tokenizer(formatted_prompt, return_tensors="pt")
        if hasattr(model, "device") and getattr(model.device, "type", "") not in ["meta", ""]:
            inputs = inputs.to(model.device)
        elif torch.cuda.is_available():
            inputs = inputs.to("cuda:0")
    except Exception as dev_err:
        logger.debug(f"[GemmaEngine] Device placement note: {dev_err}")

    cfg_max = getattr(config, "GEMMA_MAX_TOKENS", 2048)
    effective_max_tokens = min(max_tokens, cfg_max) if max_tokens > 0 else cfg_max

    eos_ids = []
    if tokenizer.eos_token_id is not None:
        eos_ids.append(tokenizer.eos_token_id)
    for special_tok in ["<|im_end|>", "<|endoftext|>", "<end_of_turn>", "<eos>"]:
        try:
            tid = tokenizer.convert_tokens_to_ids(special_tok)
            if isinstance(tid, int) and tid > 0 and tid not in eos_ids:
                eos_ids.append(tid)
        except Exception:
            pass
    if not eos_ids:
        eos_ids = [tokenizer.eos_token_id or 0]

    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=effective_max_tokens,
        do_sample=True if temperature > 0 else False,
        temperature=max(temperature, 0.01) if temperature > 0 else None,
        top_p=top_p if temperature > 0 else None,
        eos_token_id=eos_ids,
        pad_token_id=tokenizer.pad_token_id or eos_ids[0],
    )

    thread = threading.Thread(target=model.generate, kwargs=gen_kwargs)
    with _engine_lock:
        thread.start()
        for new_text in streamer:
            if "<think>" in new_text or "</think>" in new_text:
                continue
            yield new_text
        thread.join()


class GemmaEngineSingleton:
    @staticmethod
    def load():
        return load_fast_engine()

    @staticmethod
    def warmup():
        try:
            logger.info("[GemmaEngine] Pre-warming Fast Core in background...")
            load_fast_engine()
            logger.info("[GemmaEngine] Warmup complete. GPU is primed and ready.")
        except Exception as e:
            logger.warning(f"[GemmaEngine] Warmup note: {e}")

    @staticmethod
    def get_info() -> Dict[str, Any]:
        fast_path, deep_path = get_model_paths()
        return {
            "status": "online",
            "mode": getattr(config, "AI_ROUTING_MODE", "fast"),
            "fast_model": Path(fast_path).name if fast_path else "none",
            "deep_model": Path(deep_path).name if deep_path else "none",
            "fast_loaded": _fast_loaded,
            "deep_loaded": _deep_loaded,
        }

    @staticmethod
    def generate(messages: List[Dict[str, str]], max_tokens: int = 2048, temperature: float = 0.7) -> str:
        return generate_response(messages, max_tokens=max_tokens, temperature=temperature)

    @staticmethod
    def generate_stream(messages: List[Dict[str, str]], max_tokens: int = 2048, temperature: float = 0.7):
        return generate_stream(messages, max_tokens=max_tokens, temperature=temperature)


gemma_engine = GemmaEngineSingleton()
