from elevenlabs.client import ElevenLabs

API_KEY = "551a36d7562c9632973193f602001d1787765c17e89fc45ece61c04097dcef1f"
VOICE_ID = "3AwU3nHsI4YWeBJbz6yn"

print("API key length:", len(API_KEY))
print("API key prefix:", API_KEY[:3])
print("Voice ID:", VOICE_ID)

client = ElevenLabs(
    api_key=API_KEY
)

audio = client.text_to_speech.convert(
    text="Halo Marvin, ini suara LANY.",
    voice_id=VOICE_ID,
    model_id="eleven_v3",
    output_format="mp3_44100_128",
)

with open("test.mp3", "wb") as f:
    for chunk in audio:
        if isinstance(chunk, bytes):
            f.write(chunk)

print("SUCCESS - test.mp3 berhasil dibuat")