import pvporcupine
import numpy as np

class WakeWordDetector:
    def __init__(self, keyword="hey bot", sensitivity=0.5):
        self.porcupine = pvporcupine.create(
            keywords=[keyword],
            sensitivities=[sensitivity]
        )
        self.frame_size = self.porcupine.frame_length
        self.buffer = b''

    def feed_audio(self, pcm_48k: bytes):
        self.buffer += pcm_48k
        while len(self.buffer) >= 3 * self.frame_size * 2:
            samples_48k = np.frombuffer(self.buffer[:3 * self.frame_size * 2], dtype=np.int16)
            self.buffer = self.buffer[3 * self.frame_size * 2:]
            samples_16k = samples_48k[::3]
            if len(samples_16k) != self.frame_size:
                continue
            keyword_index = self.porcupine.process(samples_16k)
            if keyword_index >= 0:
                return True
        return False
