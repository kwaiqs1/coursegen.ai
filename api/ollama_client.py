import os
import re
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

def call_ollama(prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
    """
    Вызывает локальный Ollama /api/generate и возвращает raw-текст ответа модели.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": 8192},
    }
    r = requests.post(url, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")

def parse_json_loose(text: str) -> dict:
    """
    Аккуратно выдираем JSON даже если модель добавит лишний текст/бэктики.
    """
    s = text.strip()

    # убрать кодовые блоки ```json ... ```
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)

    # пробуем как есть
    try:
        return json.loads(s)
    except Exception:
        pass

    # ищем первую { и последнюю }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start : end + 1]
        return json.loads(candidate)

    raise ValueError("Не удалось распарсить JSON из ответа модели.")
