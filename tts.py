from google.cloud import texttospeech
import tempfile
import os
import discord

client = texttospeech.TextToSpeechClient()

def synthesize_speech(text):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(response.audio_content)
        return f.name

async def play_tts(voice_client, text):
    audio_file = synthesize_speech(text)
    source = discord.FFmpegPCMAudio(audio_file)
    voice_client.play(source, after=lambda e: os.unlink(audio_file))
    while voice_client.is_playing():
        await asyncio.sleep(0.1)
