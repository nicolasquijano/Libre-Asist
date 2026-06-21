"""Configuration storage for MiniMax AI Assistant.

Stores config as JSON in the LibreOffice user profile, separate from
the python script directory. Survives LibreOffice restarts.
"""

import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/libreoffice/4/user/libre_asist")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

PROVIDER_PRESETS = {
    "MiniMax": {
        "api_url": "https://api.minimax.io/v1/chat/completions",
        "model": "MiniMax-M3",
    },
    "OpenAI": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
    },
    "Ollama": {
        "api_url": "http://localhost:11434/v1/chat/completions",
        "model": "llama3.2",
    },
    "localAI": {
        "api_url": "http://localhost:8080/v1/chat/completions",
        "model": "gpt-3.5-turbo",
    },
    "Anthropic": {
        "api_url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-6",
    },
    "Groq": {
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
    },
    "Custom": {
        "api_url": "",
        "model": "",
    },
}

SYSTEM_PROMPTS = {
    "General": "You are a helpful assistant.",
    "Rewriter": "You rewrite text to be clearer, more concise, and grammatically correct. Output only the rewritten text, no commentary.",
    "Summarizer": "You summarize text concisely. Output only the summary, no preamble.",
    "Translator": "You translate text accurately. Output only the translation, no notes.",
    "Formula expert (Calc)": "You convert natural language descriptions into spreadsheet formulas. Output only the formula starting with =, no explanation.",
    "Code expert": "You are an expert programmer. Output only the code, no explanation.",
    "Custom": "",
}

DEFAULT_CONFIG = {
    "provider": "MiniMax",
    "api_url": PROVIDER_PRESETS["MiniMax"]["api_url"],
    "api_key": "",
    "model": PROVIDER_PRESETS["MiniMax"]["model"],
    "system_prompt": "You are a helpful assistant.",
    "system_preset": "General",
    "temperature": 0.7,
    "max_tokens": 8192,
    "timeout": 180,
    "enable_web_search": False,
    "search_max_results": 5,
}


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load():
    _ensure_dir()
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data)
        return cfg
    except (OSError, ValueError):
        return dict(DEFAULT_CONFIG)


def save(cfg):
    _ensure_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def apply_preset(cfg, provider):
    if provider not in PROVIDER_PRESETS:
        return cfg
    preset = PROVIDER_PRESETS[provider]
    out = dict(cfg)
    out["provider"] = provider
    if provider != "Custom":
        out["api_url"] = preset["api_url"]
        if not out.get("model") or out.get("model") in [v["model"] for v in PROVIDER_PRESETS.values() if v["model"]]:
            out["model"] = preset["model"]
    return out


AUTO_APPLY_PATH = os.path.join(CONFIG_DIR, "auto_apply.json")


def load_auto_apply():
    if not os.path.isfile(AUTO_APPLY_PATH):
        return {"always": []}
    try:
        with open(AUTO_APPLY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"always": []}
        if not isinstance(data.get("always"), list):
            data["always"] = []
        else:
            data["always"] = [item for item in data["always"] if isinstance(item, (list, tuple)) and len(item) == 2]
        return data
    except (OSError, ValueError):
        return {"always": []}


def save_auto_apply(rules):
    try:
        _ensure_dir()
        with open(AUTO_APPLY_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    cfg = load()
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
