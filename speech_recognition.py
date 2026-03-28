import asyncio
from google.cloud import speech_v1p1beta1 as speech

class SpeechRecognizer:
    def __init__(self, timeout_seconds=5):
        self.client = speech.SpeechClient()
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
        )
        self.active = False
        self.timeout = timeout_seconds
        self.audio_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self._task = None

    async def start(self):
        if self.active:
            return
        self.active = True
        self._task = asyncio.create_task(self._recognize())
        asyncio.create_task(self._timeout())

    async def feed(self, pcm_bytes):
        if self.active:
            await self.audio_queue.put(pcm_bytes)

    async def _recognize(self):
        async def request_generator():
            while self.active:
                try:
                    chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)
                except asyncio.TimeoutError:
                    if not self.active:
                        break
                    continue

        requests = request_generator()
        responses = self.client.streaming_recognize(self.streaming_config, requests)

        for response in responses:
            if not self.active:
                break
            for result in response.results:
                if result.is_final:
                    transcript = result.alternatives[0].transcript
                    await self.result_queue.put(transcript)

        self.active = False

    async def _timeout(self):
        await asyncio.sleep(self.timeout)
        self.active = False

    async def get_command(self):
        try:
            transcript = await asyncio.wait_for(self.result_queue.get(), timeout=self.timeout + 1)
            return transcript
        except asyncio.TimeoutError:
            return None

    async def stop(self):
        self.active = False
        if self._task:
            self._task.cancel()
