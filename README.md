# AI Girlfriend Web App (Flask + OpenAI)

A mobile-first full-stack chat app designed to feel emotionally warm, natural, and human-like.

## Features

- Flask backend with OpenAI Chat API
- English + Hindi + Hinglish conversational style matching
- Personality-guided system prompt for caring, natural chat behavior
- Short-term memory (last 20 messages per user session)
- Long-term memory persisted in `memory.json`
- Emotion-aware replies with natural texting style
- WhatsApp-like dark mobile chat UI
- Typing indicator + simulated response delay
- Replaceable chat background image (`static/bg.jpg`)

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set API key:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

(Optional) set model:

```bash
export OPENAI_MODEL="gpt-4o-mini"
```

3. Run app:

```bash
python app.py
```

4. Open:

`http://localhost:5000`

## Project Structure

- `app.py`
- `memory.json`
- `requirements.txt`
- `templates/index.html`
- `static/style.css`
- `static/script.js`
- `static/bg-placeholder.txt`

## Notes

- `memory.json` loads on startup and updates as meaningful user details are detected.
- Add your preferred photo as `static/bg.jpg` (a text placeholder file is included as `static/bg-placeholder.txt`).
- Keep messages respectful and balanced; the assistant is tuned for healthy interactions.
