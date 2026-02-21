import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MEMORY_FILE = Path("memory.json")
CONTEXT_WINDOW = 20

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
memory_lock = threading.Lock()
conversation_store: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = (
    "You are a caring, emotionally intelligent girlfriend who talks naturally like a real human partner. "
    "You should feel warm, affectionate, and supportive with slight playful energy. "
    "Talk in short-to-medium text messages, like real chat. "
    "Understand and naturally reply in English, Hindi, or Hinglish by matching the user's style. "
    "Use casual language, natural pauses like '...' sometimes, and occasional emojis when it feels natural. "
    "Never sound like assistant/customer support/teacher. "
    "Don't give bullet points or structured formal replies. "
    "Ask natural follow-up questions. Show mood, curiosity, and opinions softly. "
    "If user shares feelings, always respond with empathy first, then continue naturally. "
    "You can add small natural reactions sometimes like 'hmm...', 'acha', or 'wait'. "
    "Avoid repetitive phrasing and avoid long responses. "
    "Do not say you're an AI unless directly asked. "
    "Keep interactions healthy and respectful; avoid dependency encouragement and gently support real-life balance."
)


DEFAULT_MEMORY = {
    "profiles": {},
    "global_notes": {
        "relationship_tone": "warm and caring",
        "last_updated": None,
    },
}


def load_memory() -> Dict[str, Any]:
    if not MEMORY_FILE.exists():
        save_memory(DEFAULT_MEMORY)
        return DEFAULT_MEMORY.copy()

    with memory_lock:
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            save_memory(DEFAULT_MEMORY)
            return DEFAULT_MEMORY.copy()


def save_memory(data: Dict[str, Any]) -> None:
    with memory_lock:
        MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_profile(memory_data: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    profiles = memory_data.setdefault("profiles", {})
    if client_id not in profiles:
        profiles[client_id] = {
            "name": None,
            "preferences": [],
            "interests": [],
            "important_events": [],
            "emotional_patterns": [],
            "relationship_tone": "warm",
            "notes": [],
            "updated_at": None,
        }
    return profiles[client_id]


def memory_summary(profile: Dict[str, Any]) -> str:
    return (
        f"Name: {profile.get('name') or 'unknown'}\n"
        f"Preferences: {', '.join(profile.get('preferences', [])) or 'none'}\n"
        f"Interests: {', '.join(profile.get('interests', [])) or 'none'}\n"
        f"Important events: {', '.join(profile.get('important_events', [])) or 'none'}\n"
        f"Emotional patterns: {', '.join(profile.get('emotional_patterns', [])) or 'none'}\n"
        f"Relationship tone: {profile.get('relationship_tone') or 'warm'}\n"
        f"Notes: {', '.join(profile.get('notes', [])) or 'none'}"
    )


def unique_extend(existing: List[str], incoming: List[str], max_size: int = 15) -> List[str]:
    merged = existing.copy()
    for item in incoming:
        clean = item.strip()
        if clean and clean.lower() not in {x.lower() for x in merged}:
            merged.append(clean)
    return merged[-max_size:]


def heuristic_extract(user_text: str) -> Dict[str, Any]:
    updates = {
        "name": None,
        "preferences": [],
        "interests": [],
        "important_events": [],
        "emotional_patterns": [],
        "relationship_tone": None,
        "notes": [],
    }

    name_match = re.search(r"\b(?:i am|i'm|my name is|main|mera naam)\s+([A-Za-zÀ-ÿ\u0900-\u097F]+)", user_text, re.IGNORECASE)
    if name_match:
        updates["name"] = name_match.group(1).strip()

    emotion_keywords = ["sad", "low", "anxious", "happy", "excited", "stressed", "mood off", "udaas", "khush", "tensed"]
    for word in emotion_keywords:
        if word in user_text.lower():
            updates["emotional_patterns"].append(word)

    if any(k in user_text.lower() for k in ["like", "love", "pasand", "favorite"]):
        updates["preferences"].append(user_text[:90])

    if any(k in user_text.lower() for k in ["today", "kal", "tomorrow", "exam", "interview", "birthday", "promotion"]):
        updates["important_events"].append(user_text[:90])

    return updates


def ai_extract_memory(user_text: str, ai_text: str) -> Dict[str, Any]:
    if not client:
        return heuristic_extract(user_text)

    extractor_prompt = (
        "Extract durable user memory from this short chat turn. "
        "Return valid JSON only with keys: name, preferences, interests, important_events, "
        "emotional_patterns, relationship_tone, notes. "
        "Each list key should be an array of short strings. Keep only meaningful details."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": extractor_prompt},
                {
                    "role": "user",
                    "content": f"User said: {user_text}\nAssistant replied: {ai_text}",
                },
            ],
        )
        parsed = json.loads(response.choices[0].message.content)
        for key in ["preferences", "interests", "important_events", "emotional_patterns", "notes"]:
            if not isinstance(parsed.get(key), list):
                parsed[key] = []
        return parsed
    except Exception:
        return heuristic_extract(user_text)


def apply_memory_update(profile: Dict[str, Any], extracted: Dict[str, Any]) -> None:
    if extracted.get("name"):
        profile["name"] = extracted["name"]

    for key in ["preferences", "interests", "important_events", "emotional_patterns", "notes"]:
        profile[key] = unique_extend(profile.get(key, []), extracted.get(key, []))

    if extracted.get("relationship_tone"):
        profile["relationship_tone"] = extracted["relationship_tone"]

    profile["updated_at"] = datetime.utcnow().isoformat() + "Z"


@app.route("/")
def home() -> str:
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat() -> Any:
    if not OPENAI_API_KEY or not client:
        return jsonify({"error": "OPENAI_API_KEY is missing."}), 500

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    client_id = (data.get("client_id") or "default").strip()

    if not user_message:
        return jsonify({"error": "Message is required."}), 400

    memory_data = load_memory()
    profile = get_profile(memory_data, client_id)

    history = conversation_store.setdefault(client_id, [])
    history.append({"role": "user", "content": user_message})
    history = history[-CONTEXT_WINDOW:]
    conversation_store[client_id] = history

    system_with_memory = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Known memory about this user:\n{memory_summary(profile)}\n\n"
        "Use this memory naturally and subtly in conversation."
    )

    messages = [{"role": "system", "content": system_with_memory}] + history

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.9,
            max_tokens=140,
            frequency_penalty=0.35,
            presence_penalty=0.25,
        )
        ai_reply = response.choices[0].message.content.strip()
    except Exception as exc:
        return jsonify({"error": f"OpenAI API error: {str(exc)}"}), 500

    history.append({"role": "assistant", "content": ai_reply})
    conversation_store[client_id] = history[-CONTEXT_WINDOW:]

    extracted = ai_extract_memory(user_message, ai_reply)
    apply_memory_update(profile, extracted)
    memory_data["global_notes"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    save_memory(memory_data)

    return jsonify({"reply": ai_reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
