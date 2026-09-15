# =============================================================================
#  jarvis.py — 100% Standalone, Self-Hosted, Private AI Voice Agent
#  Powered by Local Google Gemma Models | $0 API Costs | 0 Token Limits
#  Real-Time Live Web Intelligence & Full PC Hardware Control
# =============================================================================

import os
import sys
import time
import datetime
import threading

import config
import voice
import brain
import pc_control

try:
    from backend.gemma_engine import gemma_engine
except ImportError:
    try:
        # pyrefly: ignore [missing-import]
        from gemma_engine import gemma_engine
    except ImportError:
        gemma_engine = None

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import memory
    memory.load()
    brain.set_history(memory.get_history())
except Exception:
    pass


def print_banner():
    """Display modern system HUD in terminal."""
    info = gemma_engine.get_info() if gemma_engine else {}
    model_name = info.get("model_name", "Gemma-Local")
    device_name = info.get("gpu_name", "RTX 3050 GPU")
    vram = info.get("vram_gb", "6.4 GB")

    banner = f"""
================================================================================
   _  _   _   ___ __   __ ___  ___        [100% STANDALONE AI VOICE AGENT]
  | || | /_\\ | _ \\\\ \\ / /|_ _|/ __|       $0 API Costs | 0 Token Limits
 _| || |/ _ \\|   / \\ V /  | | \\__ \\       100% Private On-Device System
 \\__/ /_/ \\_\\_|_\\  \\_/  |___||___/       Powered by Google Gemma Core
                                          Real-Time Live Web Intelligence
================================================================================
  [AI Engine]       : Local Gemma Core ({model_name})
  [Hardware Target] : {device_name} ({vram} VRAM)
  [Web Intelligence]: Active ($0 Real-Time Clock + News RSS + Deep Web RAG)
  [Voice Engine]    : Offline SAPI5 Speech Synthesizer + Local Interrupt Listener
  [Speech Input]    : {"Local Whisper STT (100% On-Device)" if getattr(config, "USE_LOCAL_WHISPER", True) else "Microphone STT"}
  [Active Persona]  : {getattr(config, "DEFAULT_PERSONA", "jarvis").upper()}
  [Language]        : {brain.get_active_language().upper()}
================================================================================
  Commands: Speak naturally or type commands.
  Interrupt: Say 'stop', 'ruko', 'chup', or press Spacebar / Esc to halt speech.
  Exit: Say or type 'exit', 'quit', or 'shutdown'.
================================================================================
"""
    print(banner)


def speak(text: str, language: str = "") -> bool:
    """Convert text to speech using the interruptible local voice engine."""
    lang = language or brain.get_active_language()
    return voice.speak(text, language=lang)


def listen() -> str:
    """Capture spoken audio or text input."""
    return voice.listen(prompt="Listening... (Speak now or press Enter to type)")


def run_agent():
    """Main voice interaction loop."""
    print_banner()

    # Pre-warm local Gemma model into GPU memory
    if gemma_engine:
        print("  [System] Initializing local Gemma model into GPU memory...")
        try:
            gemma_engine.load()
            print("  [System] Local Gemma engine initialized and ready.\n")
        except Exception as e:
            print(f"  [System] Note on model pre-load: {e}\n")

    # Calibrate microphone
    voice.calibrate_microphone()

    initial_greeting = "All local systems are online, sir. Running 100% on your PC with zero cloud dependence. How may I assist you?"
    speak(initial_greeting)

    while True:
        try:
            command = listen()

            if not command:
                continue

            cmd_lower = command.lower().strip()

            # Check shutdown / exit triggers
            if any(term in cmd_lower for term in ["exit", "quit", "shutdown jarvis", "close jarvis", "bye jarvis"]):
                speak("Shutting down local systems. Goodbye, sir.")
                break

            # Check standalone stop / pause triggers
            if cmd_lower in ["stop", "ruko", "roko", "bas", "chup", "quiet", "cancel", "pause", "shh", "wait", "hold on"]:
                speak("Standing by, sir.")
                continue

            # Check PC Hardware & Automation Commands
            pc_response = pc_control.handle(command)
            if pc_response:
                stopped = speak(pc_response)
                if stopped:
                    speak("Action stopped, sir.")
                continue

            # Query Local Gemma AI Brain with Live Web Intelligence & Neural Memory
            print("  [Brain] Processing with Local Gemma AI & Real-time Web Intelligence...")
            answer = brain.ask(
                command,
                persona=getattr(config, "DEFAULT_PERSONA", "jarvis"),
                language=brain.get_active_language()
            )

            stopped = speak(answer)
            if stopped:
                speak("Standing by. What would you like to explore next, sir?")

        except KeyboardInterrupt:
            print("\n[System] Interrupted by keyboard. Exiting...")
            break
        except Exception as e:
            print(f"[Jarvis Runtime Error] {e}")
            time.sleep(0.5)


if __name__ == "__main__":
    run_agent()