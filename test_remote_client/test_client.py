import requests
import json
import time
import sys

# Set stdout encoding to utf-8 safely
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# =============================================================================
#  Jarvis Remote Live Conversation Client
#  Runs with 0 GB model weights using API Key authentication
# =============================================================================

HOST_URL = "http://127.0.0.1:8000"  # Set to "http://192.168.1.14:8000" on other PCs
API_KEY = "sk-jarvis-shravan-2026-secure"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def check_server():
    """Checks if the host backend is online."""
    try:
        res = requests.get(f"{HOST_URL}/api/status", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            model = data.get("model_name", "Gemma Engine")
            provider = data.get("ai_provider", "Local GPU")
            return True, f"{provider} | Model: {model}"
        return False, f"HTTP {res.status_code}"
    except Exception as e:
        return False, str(e)

def send_chat_message(prompt: str, persona: str = "jarvis", language: str = "en"):
    """Sends a message to the Jarvis backend and returns the response."""
    url = f"{HOST_URL}/api/message"
    payload = {
        "text": prompt,
        "persona": persona,
        "language": language
    }
    
    t0 = time.time()
    try:
        res = requests.post(url, headers=HEADERS, json=payload, timeout=60)
        elapsed = time.time() - t0
        
        if res.status_code == 200:
            data = res.json()
            reply = data.get("response") or data.get("reply", "")
            return reply, elapsed
        else:
            return f"Error (HTTP {res.status_code}): {res.text}", 0.0
    except Exception as e:
        return f"Error connecting to host: {e}", 0.0

def main():
    print("=" * 70)
    print("🤖  JARVIS LIVE REMOTE TERMINAL CLIENT")
    print(f"    Host Endpoint: {HOST_URL}")
    print(f"    API Key: {API_KEY[:10]}...{API_KEY[-6:]}")
    print("=" * 70)
    print("Checking connection to host server...")
    
    online, info = check_server()
    if not online:
        print(f"❌ Could not reach host server at {HOST_URL}")
        print(f"   Reason: {info}")
        print("\n💡 Make sure the host backend server is running.")
        return

    print(f"✅ Connected to Host! ({info})\n")
    print("Commands:")
    print("  • Type any message to chat with Jarvis in real-time.")
    print("  • Type 'clear' to reset conversation memory.")
    print("  • Type 'exit' or 'quit' to close.\n")
    print("-" * 70)

    current_persona = "jarvis"
    turn = 1

    while True:
        try:
            user_input = input(f"\n[Turn {turn}] You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "q"]:
            print("\nGoodbye! Client closed.")
            break

        if user_input.lower() == "clear":
            try:
                requests.post(f"{HOST_URL}/api/clear", headers=HEADERS, timeout=5)
                print("🧹 Conversation memory cleared.")
                turn = 1
            except Exception as e:
                print(f"Failed to clear history: {e}")
            continue

        print("Jarvis is thinking...", end="\r", flush=True)
        reply, elapsed = send_chat_message(user_input, persona=current_persona)
        
        # Clear thinking line and display formatted response
        print(" " * 30, end="\r", flush=True)
        print(f"🤖 Jarvis ({elapsed:.2f}s): {reply}")
        turn += 1

if __name__ == "__main__":
    main()
