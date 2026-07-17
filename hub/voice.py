"""Universal dictation: toggle recording, transcribe, type into the focused field.

Engines (settings.yaml -> voice.engine):
  openai        : Whisper API (needs OPENAI_API_KEY)
  anthropic-... : n/a — use 'local' or 'openai'
  local         : faster-whisper on-device (pip install faster-whisper)

This works in ANY app (Claude, Cursor, Slack, browser) because the transcript
is typed into whatever input field currently has focus.
"""
import io
import os
import threading
import wave

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    sd = None

SAMPLE_RATE = 16000


class VoiceRecorder:
    def __init__(self, settings, platform):
        self.settings = settings.get("voice", {})
        self.platform = platform
        self.is_recording = False
        self._frames = []
        self._stream = None

    def toggle(self):
        if self.is_recording:
            self.stop()
        else:
            self.start()

    def start(self):
        if sd is None:
            print("voice: pip install sounddevice numpy")
            return
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16",
            callback=lambda indata, *_: self._frames.append(indata.copy()))
        self._stream.start()
        self.is_recording = True
        print("voice: recording...")

    def stop(self):
        if not self.is_recording:
            return
        self._stream.stop(); self._stream.close()
        self.is_recording = False
        audio = np.concatenate(self._frames) if self._frames else None
        if audio is None or len(audio) < SAMPLE_RATE // 4:
            print("voice: too short, discarded")
            return
        threading.Thread(target=self._transcribe_and_type,
                         args=(audio,), daemon=True).start()

    # ---------- transcription ----------
    def _wav_bytes(self, audio):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
            w.writeframes(audio.tobytes())
        buf.seek(0); buf.name = "speech.wav"
        return buf

    def _transcribe_and_type(self, audio):
        engine = self.settings.get("engine", "local")
        try:
            if engine == "openai":
                text = self._openai(audio)
            else:
                text = self._local(audio)
        except Exception as e:
            print(f"voice: transcription failed: {e}")
            return
        text = (text or "").strip()
        if text:
            print(f"voice: -> {text!r}")
            self.platform.type_text(text)

    def _openai(self, audio):
        from openai import OpenAI
        client = OpenAI()  # OPENAI_API_KEY from env
        r = client.audio.transcriptions.create(
            model=self.settings.get("openai_model", "whisper-1"),
            file=self._wav_bytes(audio))
        return r.text

    _local_model = None

    def _local(self, audio):
        from faster_whisper import WhisperModel
        if VoiceRecorder._local_model is None:
            size = self.settings.get("local_model", "base.en")
            VoiceRecorder._local_model = WhisperModel(size, compute_type="int8")
        segments, _ = VoiceRecorder._local_model.transcribe(
            audio.astype("float32").flatten() / 32768.0)
        return " ".join(s.text for s in segments)
