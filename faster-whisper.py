#!/usr/bin/env python3
import os
import signal
import threading
import time

import pyperclip
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel


class VoiceTypingDaemon:
    def __init__(self):
        self.is_recording = False
        self.recording_thread = None
        self.model = None
        self.model_size = "distil-large-v3"
        self.sample_rate = 16000
        self.audio_file = "voice.wav"
        self.pid_file = "/tmp/voice_typing.pid"
        self.running = True

    def load_model(self):
        if self.model is None:
            print(f"Loading Whisper model {self.model_size}...")
            start_time = time.time()
            self.model = WhisperModel(self.model_size, device="cpu")
            load_time = time.time() - start_time
            print(f"Model loaded in {load_time:.2f} seconds")

    def start_recording(self):
        print("🎙️  Recording started...")
        self.audio_data = []

        def callback(indata, frames, time, status):
            if status:
                print(f"Recording status: {status}")
            self.audio_data.append(indata.copy())

        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
            while self.is_recording and self.running:
                time.sleep(0.1)

    def stop_recording_and_transcribe(self):
        print("⏹️  Recording stopped, processing...")

        # 録音データを保存
        if hasattr(self, "audio_data") and self.audio_data:
            import numpy as np

            audio_array = np.concatenate(self.audio_data, axis=0)
            sf.write(self.audio_file, audio_array, self.sample_rate)

            # 音声を文字起こし
            self.load_model()
            print("📝 Transcribing...")
            segments, info = self.model.transcribe(
                self.audio_file,
                beam_size=5,
                language="ja",
                condition_on_previous_text=False,
            )

            # テキストを結合
            transcribed_text = " ".join([segment.text for segment in segments])

            if transcribed_text.strip():
                print(f"💬 Transcribed: {transcribed_text}")
                # クリップボードにコピー
                pyperclip.copy(transcribed_text)
                print("📋 Text copied to clipboard!")
            else:
                print("🔇 No speech detected")
        else:
            print("❌ No audio data recorded")

    def write_pid(self):
        """PIDファイルを作成"""
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            print(f"PID file error: {e}")

    def toggle_recording(self):
        if not self.is_recording:
            # 録音開始
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self.start_recording)
            self.recording_thread.daemon = True
            self.recording_thread.start()
        else:
            # 録音停止
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join()
            self.stop_recording_and_transcribe()

    def run(self):
        """デーモンメインループ"""
        print("👂 Voice typing daemon started. Waiting for signals...")
        self.write_pid()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        if signum == signal.SIGUSR1:
            print("\n📨 Received toggle signal")
            self.toggle_recording()
        elif signum == signal.SIGUSR2:
            status = "recording" if self.is_recording else "idle"
            print(f"\n📊 Status: {status}")
        elif signum in [signal.SIGINT, signal.SIGTERM]:
            print("\n🛑 Received shutdown signal")
            self.running = False
            if self.is_recording:
                self.is_recording = False
                if self.recording_thread:
                    self.recording_thread.join()


def main():
    daemon = VoiceTypingDaemon()

    # シグナルハンドラーを設定
    signal.signal(signal.SIGINT, daemon.signal_handler)
    signal.signal(signal.SIGTERM, daemon.signal_handler)
    signal.signal(signal.SIGUSR1, daemon.signal_handler)
    signal.signal(signal.SIGUSR2, daemon.signal_handler)

    try:
        daemon.run()
    except Exception as e:
        print(f"❌ Daemon error: {e}")
    finally:
        # クリーンアップ
        if os.path.exists(daemon.pid_file):
            os.remove(daemon.pid_file)


if __name__ == "__main__":
    main()
