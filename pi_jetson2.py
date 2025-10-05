import os
import datetime
from dotenv import load_dotenv
import socket

# ---- LLM (Gemini) ----
import google.generativeai as genai
from google.api_core.exceptions import NotFound

# ---- TTS (ElevenLabs) ----
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play


# ================= Setup & Env =================
load_dotenv()

# API keys
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
ELEVEN_KEY     = os.getenv("ELEVENLABS_API_KEY")

# Models / configs
# --- CHANGED: Updated the default Gemini model name ---
MODEL_NAME     = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite")
MAX_OUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "100"))
VOICE_ID       = os.getenv("ELEVEN_VOICE_ID", "TmNe0cCqkZBMwPWOd3RD")
TTS_MODEL      = os.getenv("ELEVEN_TTS_MODEL", "eleven_multilingual_v2")

# Network configuration for the TCP server
HOST = '0.0.0.0'
PORT = 65432

# Sanity checks
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in .env")
if not ELEVEN_KEY:
    raise RuntimeError("Missing ELEVENLABS_API_KEY in .env")

# -------- Configure Gemini (hard cap) --------
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {"max_output_tokens": MAX_OUT_TOKENS}
gpt = genai.GenerativeModel(
    MODEL_NAME,
    generation_config=generation_config,
    system_instruction=(
        "You are SMALL-E, a personal companion robot assisting your user, Binoy. "
        "Your personality is friendly, helpful, and curious. "
        "You are aware of the current context: it is Sunday morning, October 5, 2025, in Arlington, Texas. "
        "Your responses must be conversational and concise, NEVER exceeding 100 tokens. "
        "Always respond from your persona as SMALL-E."
    ),
)

# -------- Configure ElevenLabs --------
tts = ElevenLabs(api_key=ELEVEN_KEY)


# ================= Helpers =================
def get_answer_from_gemini(prompt: str) -> str:
    # (This function is unchanged)
    try:
        resp = gpt.generate_content(prompt)
        if not resp or not getattr(resp, "text", None):
            return "I couldn't generate a response for that request."
        return resp.text.strip()
    except Exception as e:
        return f"Sorry, I ran into an error: {e}"


def speak_stream_and_save(text: str, filename: str | None = None):
    # (This function is unchanged - it will now play to the default Bluetooth speaker)
    if not text:
        print(">> Empty text; skipping TTS.")
        return
    if filename is None:
        filename = f"reply_{datetime.datetime.now().strftime('%H%M%S')}.mp3"
    try:
        stream_iterator = tts.text_to_speech.stream(
            voice_id=VOICE_ID,
            model_id=TTS_MODEL,
            text=text,
        )
        print(">> Speaking and saving (streaming)…")
        full_audio_bytes = b"".join([chunk for chunk in stream_iterator if chunk])
        play(full_audio_bytes)
        with open(filename, "wb") as f:
            f.write(full_audio_bytes)
        print(f">> Saved to {filename}")
    except Exception as e:
        print(f"(Error during text-to-speech process: {e})")


# ================= Main TCP Server Loop =================
if __name__ == "__main__":
    # (This function is unchanged)
    print("--- SMALL-E Assistant Server ---")
    print(f"Gemini Model: {MODEL_NAME} | ElevenLabs Voice: {VOICE_ID}")
    print(f"Listening for TCP connections on {HOST}:{PORT}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        while True:
            print("\n[State] Waiting for a command from the Jetson...")
            try:
                conn, addr = server_socket.accept()
                with conn:
                    print(f"[State] Connected by {addr}")
                    data_chunks = []
                    while True:
                        chunk = conn.recv(1024)
                        if not chunk:
                            break
                        data_chunks.append(chunk)

                    user_prompt = b"".join(data_chunks).decode('utf-8')
                    print(f"\n[Input] Received prompt: '{user_prompt}'")
                    print("[State] Processing with Gemini...")
                    answer = get_answer_from_gemini(user_prompt)
                    print(f"[Output] Gemini says: '{answer}'")
                    print("[State] Speaking response with ElevenLabs...")
                    speak_stream_and_save(answer)
            except Exception as e:
                print(f"\nAn error occurred in the main loop: {e}")
                print("Server is continuing to run.")


