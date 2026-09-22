import json
import urllib.request
from state import set_state

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "hf.co/saidutta69/Qwen2.5-Coder-7B-Instruct-heretic:Q4_K_M"

def check_ollama():
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as exc:
        return {"error": str(exc)}

def discover_ollama_models():
    data = check_ollama()
    if "error" in data:
        return data
    return {"models": [m.get("name") for m in data.get("models", [])]}

def register_ollama():
    set_state("ai_provider", "ollama")
    return {"provider": "ollama", "base_url": OLLAMA_URL}

def sync_ollama_models():
    return discover_ollama_models()

def test_provider(provider_id=None):
    data = check_ollama()
    return {"ok": "error" not in data, "provider_id": provider_id, "data": data}

def get_provider_status():
    data = check_ollama()
    return {"provider": "ollama", "ok": "error" not in data,
            "models": data.get("models", []) if isinstance(data, dict) else []}
