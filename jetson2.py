import sounddevice as sd
import numpy as np
import struct
import queue
import time
from faster_whisper import WhisperModel
import pvporcupine
import socket
import os

# --- CONFIGURATION ---
PICOVOICE_ACCESS_KEY = os.getenv("PICOKEY")
WAKE_WORD_PATH = "small_e.ppn"
WAKE_WORD_NAME = "SMALL-E"

MODEL_SIZE = "tiny.en"
DEVICE = "cuda"
COMPUTE_TYPE = "float16"

SAMPLE_RATE = 16000
CHANNELS = 1
COMMAND_RECORD_SECONDS = 5

SEND_VIA_TCP = True
PI_IP = "192.168.2.1" 
PI_PORT = 65432 

# --- MAIN FUNCTION ---
def main():
    print("Initializing...")
    porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keyword_paths=[WAKE_WORD_PATH])
    print(f"Loading Whisper model: {MODEL_SIZE}...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    
    # Stricter decoding options to help prevent repetition
    transcribe_options = {
        "beam_size": 2, "language": "en", "temperature": (0.0, 0.2, 0.4),
        "log_prob_threshold": -1.0, "no_speech_threshold": 0.7,
        "repetition_penalty": 1.2, "no_repeat_ngram_size": 2
    }

    audio_queue = queue.Queue()
    def audio_callback(indata, frames, time_info, status):
        if status: print(status)
        audio_queue.put(bytes(indata))
    
    stream = None
    try:
        stream = sd.RawInputStream(samplerate=porcupine.sample_rate, blocksize=porcupine.frame_length,
                                   channels=CHANNELS, dtype='int16', callback=audio_callback)
        stream.start()

        while True:
            print(f" Listening for '{WAKE_WORD_NAME}'...")
            while True:
                pcm = audio_queue.get()
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    print(" Wake word detected!")
                    break

            print(" Listening for command...")
            command_audio_frames = []
            num_frames_to_record = int((SAMPLE_RATE / porcupine.frame_length) * COMMAND_RECORD_SECONDS)
            while not audio_queue.empty(): audio_queue.get()
            for _ in range(num_frames_to_record):
                command_audio_frames.append(audio_queue.get())
            
            # --- CONVERT AUDIO FOR WHISPER ---
            audio_bytes = b"".join(command_audio_frames)
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            print(" Transcribing command...")
            segments, _ = model.transcribe(audio_float32, **transcribe_options)
            transcribed_text = "".join(segment.text for segment in segments).strip()
            
            if not transcribed_text:
                print("No command detected.\n")
                continue
            print(f"USER: {transcribed_text}")
            
            if SEND_VIA_TCP:
                # This is the section we will analyze in Part 2
                print(f" Sending to Pi at {PI_IP}:{PI_PORT}...")
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((PI_IP, PI_PORT))
                        s.sendall(transcribed_text.encode('utf-8'))
                    print(" Sent successfully.")
                except Exception as e:
                    print(f"An error occurred while sending data: {e}")
    finally:
        if stream is not None: stream.stop(); stream.close()
        if 'porcupine' in locals() and porcupine is not None: porcupine.delete()
        print("Cleanup complete. Exiting.")

if __name__ == "__main__":
    main()


