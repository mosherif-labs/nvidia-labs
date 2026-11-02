"""A synthetic customer call: hosted Magpie TTS (Riva) writes call.wav for the ASR step."""

import os, time, wave
import riva.client
from dotenv import load_dotenv

load_dotenv()  # nearest .env, searching up from this file

TEXT = (
    "Hi, this is Dana Kovacs, account A-1001. Last month I paid in four cash deposits, "
    "each just under ten thousand pounds, and sent the money on to Orbit Trading. "
    "Why has my account been frozen?"
)
TTS_FUNCTION = (
    "877104f7-e885-42b9-8de8-f6e4c6303969"  # magpie-tts-multilingual, from its API tab
)
RATE = 22050  # the client's default; the WAV header below must match it
auth = riva.client.Auth(
    uri="grpc.nvcf.nvidia.com:443",
    use_ssl=True,
    metadata_args=[
        ["function-id", TTS_FUNCTION],
        ["authorization", f"Bearer {os.environ['NVIDIA_API_KEY']}"],
    ],
)
t = time.perf_counter()
resp = riva.client.SpeechSynthesisService(auth).synthesize(
    TEXT,
    voice_name="Magpie-Multilingual.EN-US.Aria",
    language_code="en-US",
    sample_rate_hz=RATE,
)
print(f"TTS took {time.perf_counter() - t:.1f} s")
with wave.open("call.wav", "wb") as w:  # 16-bit mono PCM, what the ASR model expects
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(resp.audio)
