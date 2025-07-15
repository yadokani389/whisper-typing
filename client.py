#!/usr/bin/env python3
import os
import signal
import threading
import time

import pyperclip
import requests
import sounddevice as sd
import soundfile as sf
from setproctitle import setproctitle

class VoiceTypingClient:
    def __init__(self, server_url="http://localhost:18031"):
        self.is_recording = False
        self.recording_thread = None
        self.server_url = server_url
        self.sample_rate = 16000
        self.audio_file = "voice.wav"
        self.pid_file = "/tmp/voice_typing_client.pid"
        self.running = True

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

        if hasattr(self, "audio_data") and self.audio_data:
            import numpy as np

            # Save audio data
            audio_array = np.concatenate(self.audio_data, axis=0)
            sf.write(self.audio_file, audio_array, self.sample_rate)

            # Send to server for transcription
            self.transcribe_with_server()
        else:
            print("❌ No audio data recorded")

    def transcribe_with_server(self):
        """Send audio file to server for transcription"""
        try:
            print("📡 Sending audio to server...")

            # Check server health
            health_response = requests.get(f"{self.server_url}/health", timeout=5)
            if health_response.status_code != 200:
                print("❌ Server is not healthy")
                return

            # Send audio file
            with open(self.audio_file, "rb") as audio_file:
                files = {"file": audio_file}
                response = requests.post(
                    f"{self.server_url}/transcribe", files=files, timeout=30
                )

            if response.status_code == 200:
                result = response.json()
                transcribed_text = result.get("transcription", "")

                if transcribed_text.strip():
                    print(f"💬 Transcribed: {transcribed_text}")
                    # Copy to clipboard
                    pyperclip.copy(transcribed_text)
                    print("📋 Text copied to clipboard!")
                else:
                    print("🔇 No speech detected")
            else:
                print(f"❌ Server error: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Make sure the server is running.")
        except requests.exceptions.Timeout:
            print("❌ Server request timed out")
        except Exception as e:
            print(f"❌ Error during transcription: {e}")

    def write_pid(self):
        """Write PID file"""
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            print(f"PID file error: {e}")

    def toggle_recording(self):
        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self.start_recording)
            self.recording_thread.daemon = True
            self.recording_thread.start()
        else:
            # Stop recording
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join()
            self.stop_recording_and_transcribe()

    def run(self):
        """Main daemon loop"""
        print(f"👂 Voice typing client started. Connected to: {self.server_url}")
        print("Waiting for signals...")
        self.write_pid()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def signal_handler(self, signum, frame):
        """Signal handler"""
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
    import sys

    server_url = "http://localhost:18031"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    client = VoiceTypingClient(server_url)

    setproctitle("whisper-typing")

    # Set up signal handlers
    signal.signal(signal.SIGINT, client.signal_handler)
    signal.signal(signal.SIGTERM, client.signal_handler)
    signal.signal(signal.SIGUSR1, client.signal_handler)
    signal.signal(signal.SIGUSR2, client.signal_handler)

    try:
        client.run()
    except Exception as e:
        print(f"❌ Client error: {e}")
    finally:
        # Cleanup
        if os.path.exists(client.pid_file):
            os.remove(client.pid_file)


if __name__ == "__main__":
    main()

