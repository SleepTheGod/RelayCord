# 📞 RelayCord – Voice‑Activated Phone Calling from Discord

RelayCord is a production‑ready Discord bot that allows you to place real phone calls directly from a voice channel.  
Just say *“Hey Bot, call 123‑456‑7890”* – the bot joins your channel, listens for the wake word, uses Twilio to dial the number, and bridges the audio so you can talk naturally.  
It also supports **multiple simultaneous calls**, **encrypted call logs**, **text‑to‑speech announcements**, and **role‑based permissions**.

[![Discord](https://img.shields.io/badge/Discord-Bot-5865F2)](https://discord.com/developers/applications)
[![Twilio](https://img.shields.io/badge/Twilio-API-EB2F0E)](https://www.twilio.com)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)

---

## ✨ Features

- **Wake‑word detection** – local (offline) wake word (“Hey Bot”) using Porcupine; no constant cloud streaming.
- **Voice command** – say “call [phone number]” after the wake word; the bot parses it with Google Cloud Speech‑to‑Text.
- **Real phone calls** – outbound calls via Twilio; caller ID is randomly selected from your own numbers.
- **Two‑way audio bridge** – you hear the other party, and they hear you, in real time.
- **Multiple concurrent calls** – each Discord voice channel can have its own call, with per‑call audio bridges.
- **Call logging** – SQLite database with **encrypted phone numbers** (Fernet).
- **Text‑to‑speech** – Google Cloud TTS announces call status (“Calling…”, “Call ended”, errors).
- **Role‑based permissions** – restrict usage to specific Discord roles (e.g., `PhoneUser`).
- **Resource limits** – configurable maximum concurrent calls.

---

## 🧩 Architecture

```
Discord Voice Channel
        │
        ▼
  Discord Bot (opus → PCM)
        │
        ├─► Wake Word Detector (Porcupine)
        ├─► Speech Recognition (Google Cloud STT)
        │       └─► command “call 123…”
        │
        └─► Audio Bridge (per call)
                │
                └─► WebSocket Server
                        │
                        ▼
                    Twilio Media Stream
                        │
                        ▼
                    Phone Call
```

All components run in a single Python asyncio application.

---

## 🚀 Prerequisites

- **Python 3.8+**
- **Discord Bot** with intents:
  - `voice_states`
  - `message_content`
- **Twilio Account** with one or more phone numbers
- **Google Cloud Project** with:
  - Speech‑to‑Text API enabled
  - Text‑to‑Speech API enabled
  - Service account key (JSON)
- **ngrok** (or a public HTTPS URL) for the WebSocket server during testing

---

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/SleepTheGod/RelayCord.git
   cd RelayCord
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**  
   Create a `.env` file in the root directory with the following:
   ```env
   DISCORD_TOKEN=your_discord_bot_token
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_NUMBERS=+1234567890,+1987654321
   GOOGLE_APPLICATION_CREDENTIALS=path/to/google_credentials.json
   DATABASE_ENCRYPTION_KEY=your_32_byte_base64_key   # generate with: openssl rand -base64 32
   ALLOWED_ROLES=PhoneUser,Admin
   MAX_CONCURRENT_CALLS=5
   WEBSOCKET_PORT=8765
   WEBSOCKET_URL=wss://your-public-url/media-stream
   ```

   > **Important** – Replace all placeholders with your actual credentials.  
   > The `WEBSOCKET_URL` must be a public HTTPS endpoint (use ngrok for testing).

4. **Expose your WebSocket server** (for Twilio to reach it)  
   ```bash
   ngrok http 8765
   ```
   Copy the HTTPS forwarding URL and set it as `WEBSOCKET_URL` (e.g., `wss://abc123.ngrok.io/media-stream`).

5. **Run the bot**
   ```bash
   python main.py
   ```

---

## 📱 Usage

1. **Invite the bot** to your Discord server with the necessary permissions.
2. **Join a voice channel**.
3. **Type `!join`** – the bot will join your channel and start listening for the wake word.
4. **Say “Hey Bot”** (the wake word) followed by your command, e.g.:
   ```
   Hey Bot call 5551234567
   ```
5. The bot will:
   - Place the call via Twilio (from a random number you own)
   - Announce “Calling…” with TTS
   - Bridge the audio so you can talk
6. **To end the call** – just hang up the phone or wait for the other party to hang up; the bot will automatically stop the bridge and say “Call ended”.
7. **To leave the voice channel** – type `!leave`.

### Permissions
Only users with one of the roles listed in `ALLOWED_ROLES` (or server administrators) can use `!join` and `!leave`. Adjust the list in `.env`.

---

## 📂 Project Structure

```
RelayCord/
├── .env                     # Environment variables
├── config.py                # Load config
├── wake_word.py             # Porcupine wake word detection
├── speech_recognition.py    # Google Cloud STT (streaming)
├── audio_bridge.py          # AudioBridge and DiscordAudioHandler
├── database.py              # SQLite with encryption
├── tts.py                   # Google Cloud TTS
├── main.py                  # Discord bot + WebSocket server
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration Explained

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Your Discord bot token. |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID. |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token. |
| `TWILIO_NUMBERS` | Comma‑separated list of phone numbers you own (e.g., `+1234567890,+1987654321`). |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to the Google Cloud service account JSON file. |
| `DATABASE_ENCRYPTION_KEY` | 32‑byte base64 key for encrypting phone numbers. Generate with `openssl rand -base64 32`. |
| `ALLOWED_ROLES` | Discord role names that are allowed to use the bot (comma‑separated). |
| `MAX_CONCURRENT_CALLS` | Maximum number of simultaneous calls (default: 5). |
| `WEBSOCKET_PORT` | Port for the WebSocket server (default: 8765). |
| `WEBSOCKET_URL` | Public HTTPS WebSocket URL for Twilio (e.g., `wss://your‑domain.com/media-stream`). |

---

## 🧪 Testing

- Use **ngrok** to expose your WebSocket server.
- Make sure your Twilio phone numbers have the **voice URL** set correctly (or rely on the call initiation method used in the code).
- Test with a friend’s phone number (or a free Twilio trial number).

---

## ⚠️ Important Notes

- **Caller ID** – The bot uses random numbers from your own pool. **Do not** spoof numbers you do not own – it is illegal in most jurisdictions.
- **Costs** – Twilio charges per minute for calls. Google Cloud Speech‑to‑Text and Text‑to‑Speech also have costs. Monitor your usage.
- **Privacy** – Phone numbers are stored encrypted in the SQLite database. Keep your encryption key safe.
- **Production** – For production, run the WebSocket server behind a reverse proxy (nginx) with SSL.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📜 License

[MIT](LICENSE)

---

## 💬 Support

If you encounter any issues, please open an issue on GitHub.

---

**Built with ❤️ using Discord.py, Twilio, and Google Cloud.**
