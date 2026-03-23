"""Voice capture and speech-to-text using OpenAI Whisper API."""

import io
import logging
import struct
import tempfile
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class VoiceCapture:
    """Records audio from the microphone and transcribes it via Whisper."""

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        max_seconds: int = 30,
    ):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_seconds = max_seconds
        self._recording = False

    def record(self) -> np.ndarray | None:
        """Record audio until silence is detected or max duration reached.

        Returns the audio as a numpy array, or None if nothing was captured.
        """
        logger.info("Listening... speak now.")
        self._recording = True

        frames: list[np.ndarray] = []
        silence_frames = 0
        silence_frame_limit = int(self.silence_duration * self.sample_rate / 1024)
        max_frames = int(self.max_seconds * self.sample_rate / 1024)
        started_speaking = False

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
            ) as stream:
                for _ in range(max_frames):
                    if not self._recording:
                        break

                    data, _ = stream.read(1024)
                    rms = np.sqrt(np.mean(data**2))

                    if rms > self.silence_threshold:
                        started_speaking = True
                        silence_frames = 0
                        frames.append(data.copy())
                    elif started_speaking:
                        silence_frames += 1
                        frames.append(data.copy())
                        if silence_frames >= silence_frame_limit:
                            logger.info("Silence detected, stopping recording.")
                            break
        except Exception:
            logger.exception("Error during recording")
            return None
        finally:
            self._recording = False

        if not frames or not started_speaking:
            return None

        audio = np.concatenate(frames, axis=0)
        logger.info("Captured %.1f seconds of audio.", len(audio) / self.sample_rate)
        return audio

    def stop(self) -> None:
        self._recording = False

    @staticmethod
    def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Convert float32 numpy audio to WAV bytes for the Whisper API."""
        pcm = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()


class Transcriber:
    """Transcribes audio using OpenAI Whisper API."""

    def __init__(self, api_key: str):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio numpy array to text."""
        wav_bytes = VoiceCapture.audio_to_wav_bytes(audio, sample_rate)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = Path(tmp.name)

        try:
            with open(tmp_path, "rb") as f:
                result = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en",
                )
            text = result.text.strip()
            logger.info("Transcription: %s", text)
            return text
        finally:
            tmp_path.unlink(missing_ok=True)
