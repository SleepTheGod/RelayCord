import asyncio
import opuslib
import discord

class AudioBridge:
    def __init__(self, call_sid, voice_client):
        self.call_sid = call_sid
        self.voice_client = voice_client
        self.discord_to_twilio_queue = asyncio.Queue()
        self.twilio_to_discord_queue = asyncio.Queue()
        self.active = True
        self._play_task = None

    async def discord_audio_received(self, pcm):
        await self.discord_to_twilio_queue.put(pcm)

    async def twilio_audio_received(self, pcm):
        await self.twilio_to_discord_queue.put(pcm)

    async def play_to_discord(self):
        class BridgeSource(discord.AudioSource):
            def __init__(self, queue):
                self.queue = queue
                self.encoder = opuslib.Encoder(48000, 1, opuslib.APPLICATION_VOIP)

            def read(self):
                try:
                    pcm = self.queue.get_nowait()
                    opus = self.encoder.encode(pcm, 960)
                    return opus
                except asyncio.QueueEmpty:
                    return b''

        source = BridgeSource(self.twilio_to_discord_queue)
        self.voice_client.play(source)
        while self.voice_client.is_playing():
            await asyncio.sleep(0.1)

    async def start(self):
        self._play_task = asyncio.create_task(self.play_to_discord())

    async def stop(self):
        self.active = False
        if self.voice_client.is_playing():
            self.voice_client.stop()
        if self._play_task:
            self._play_task.cancel()

class DiscordAudioHandler:
    def __init__(self, voice_client):
        self.voice_client = voice_client
        self.decoder = opuslib.Decoder(48000, 1)
        self._listening = False
        self._wake_word_detector = None
        self._speech_recognizer = None
        self.audio_bridge = None

    async def start_listening(self, wake_word_detector, speech_recognizer, audio_bridge=None):
        self._wake_word_detector = wake_word_detector
        self._speech_recognizer = speech_recognizer
        self.audio_bridge = audio_bridge

        @self.voice_client.listen
        def on_audio(data):
            pcm = self.decoder.decode(data, 960)
            if self._wake_word_detector and self._wake_word_detector.feed_audio(pcm):
                asyncio.create_task(self._on_wake_word())
            if self._speech_recognizer and self._speech_recognizer.active:
                asyncio.create_task(self._speech_recognizer.feed(pcm))
            if self.audio_bridge and self.audio_bridge.active:
                asyncio.create_task(self.audio_bridge.discord_audio_received(pcm))

        self._listening = True

    async def _on_wake_word(self):
        if self._speech_recognizer and not self._speech_recognizer.active:
            await self._speech_recognizer.start()
