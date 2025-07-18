#!/usr/bin/env python3
import signal
import subprocess
import threading
import time

import pyperclip
import requests
import sounddevice as sd
import soundfile as sf
from setproctitle import setproctitle

# Optional tray icon imports
try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# Constants
SAMPLE_RATE = 16000
DEFAULT_SERVER_URL = "http://localhost:18031"
DEFAULT_OUTPUT_MODE = "direct_type"
ICON_SIZE = 64
ICON_CIRCLE_MARGIN = 8


class VoiceTypingClient:
    def __init__(
        self,
        server_url=DEFAULT_SERVER_URL,
        output_mode=DEFAULT_OUTPUT_MODE,
        enable_tray=False,
        use_ollama=False,
        ollama_model=None,
        ollama_prompt=None,
    ):
        # Input validation
        if not server_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid server URL format: {server_url}")

        valid_modes = ["clipboard", "direct_type"]
        if output_mode not in valid_modes:
            raise ValueError(
                f"Invalid output mode: {output_mode}. Valid modes: {valid_modes}"
            )

        self.is_recording = False
        self.recording_thread = None
        self.server_url = server_url
        self.sample_rate = SAMPLE_RATE
        self.running = True
        self.output_mode = output_mode
        self.enable_tray = enable_tray and TRAY_AVAILABLE
        self.tray_icon = None
        self.tray_thread = None

        # Ollama settings
        self.use_ollama = use_ollama
        self.ollama_model = ollama_model
        self.ollama_prompt = ollama_prompt

    def start_recording(self):
        print("Recording started...")
        self.audio_data = []

        def callback(indata, frames, time, status):
            if status:
                print(f"Recording status: {status}")
            self.audio_data.append(indata.copy())

        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
            while self.is_recording and self.running:
                time.sleep(0.1)

    def stop_recording_and_transcribe(self):
        print("Recording stopped, processing...")

        if hasattr(self, "audio_data") and self.audio_data:
            import numpy as np
            import io

            # Prepare audio data in memory
            audio_array = np.concatenate(self.audio_data, axis=0)

            # Create in-memory buffer
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, audio_array, self.sample_rate, format="WAV")
            audio_buffer.seek(0)

            # Send to server for transcription
            self.transcribe_with_server(audio_buffer)
        else:
            print("No audio data recorded")

    def transcribe_with_server(self, audio_buffer):
        """Send audio buffer to server for transcription"""
        try:
            print("Sending audio to server...")

            # Prepare form data
            files = {"file": ("audio.wav", audio_buffer, "audio/wav")}
            data = {
                "use_ollama": self.use_ollama,
                "ollama_model": self.ollama_model or "",
                "ollama_prompt": self.ollama_prompt or "",
            }
            response = requests.post(
                f"{self.server_url}/transcribe", files=files, data=data, timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                transcribed_text = result.get("transcription", "")
                formatted_text = result.get("formatted_text", "")

                if transcribed_text.strip():
                    print(f"Transcribed: {transcribed_text}")

                    # Use formatted text if available, otherwise use original
                    output_text = formatted_text if formatted_text else transcribed_text

                    if formatted_text:
                        print(f"Formatted: {formatted_text}")

                    # Output text based on configured mode
                    self.output_text(output_text)
                else:
                    print("No speech detected")
            else:
                print(f"Server error: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError:
            print("Cannot connect to server. Make sure the server is running.")
        except requests.exceptions.Timeout:
            print("Server request timed out")
        except Exception as e:
            print(f"Error during transcription: {e}")
        finally:
            # Update tray icon after processing
            if self.enable_tray and self.tray_icon:
                self.update_tray_icon()

    def output_text(self, text):
        """Output text based on configured mode"""
        if self.output_mode == "clipboard":
            pyperclip.copy(text)
            print("Text copied to clipboard!")
        elif self.output_mode == "direct_type":
            print("Direct typing...")
            subprocess.run(["wtype", text])
        else:
            print(f"Unknown output mode: {self.output_mode}")

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

        # Update tray icon
        if self.enable_tray and self.tray_icon:
            self.update_tray_icon()

    def create_icon(self, color):
        """Create a simple circular icon with the given color and transparent background"""
        image = Image.new(
            "RGBA", (ICON_SIZE, ICON_SIZE), (255, 255, 255, 0)
        )  # Transparent background
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            [
                ICON_CIRCLE_MARGIN,
                ICON_CIRCLE_MARGIN,
                ICON_SIZE - ICON_CIRCLE_MARGIN,
                ICON_SIZE - ICON_CIRCLE_MARGIN,
            ],
            fill=color,
        )
        return image

    def get_tray_icon(self):
        """Get the appropriate icon based on current status"""
        if self.is_recording:
            return self.create_icon("red")  # Recording
        elif not self.running:
            return self.create_icon("gray")  # Stopped
        else:
            return self.create_icon("green")  # Idle

    def update_tray_icon(self):
        """Update the tray icon based on current status"""
        if self.tray_icon:
            self.tray_icon.icon = self.get_tray_icon()

    def setup_tray_icon(self):
        """Setup the system tray icon"""
        if not self.enable_tray:
            return

        # Create menu items
        menu = pystray.Menu(
            pystray.MenuItem("Toggle Recording", self.tray_toggle_recording),
            pystray.MenuItem("Status", self.show_status),
            pystray.MenuItem("Quit", self.quit_application),
        )

        # Create tray icon
        self.tray_icon = pystray.Icon(
            "whisper-typing", self.get_tray_icon(), menu=menu, title="Whisper Typing"
        )

        # Run tray icon in separate thread
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def tray_toggle_recording(self, icon, item):
        """Handle toggle recording from tray menu"""
        self.toggle_recording()

    def show_status(self, icon, item):
        """Show current status (placeholder for now)"""
        status = "Recording" if self.is_recording else "Idle"
        print(f"Current status: {status}")

    def quit_application(self, icon, item):
        """Quit the application from tray"""
        self.running = False
        self.cleanup()

    def run(self):
        """Main daemon loop"""
        print(f"Voice typing client started. Connected to: {self.server_url}")

        # Setup tray icon if enabled
        if self.enable_tray:
            print("Setting up system tray icon...")
            self.setup_tray_icon()

        print("Waiting for signals...")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def cleanup(self):
        """Centralized cleanup method"""
        # Stop recording if active
        if self.is_recording:
            self.is_recording = False
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=5)

        # Clean up tray icon
        if self.enable_tray and self.tray_icon:
            self.tray_icon.stop()

    def signal_handler(self, signum, frame):
        """Signal handler"""
        if signum == signal.SIGUSR1:
            print("\nReceived toggle signal")
            self.toggle_recording()
        elif signum in [signal.SIGINT, signal.SIGTERM]:
            print("\nReceived shutdown signal")
            self.running = False
            self.cleanup()


def create_argument_parser():
    """Create and configure the argument parser"""
    import argparse

    parser = argparse.ArgumentParser(description="Voice typing client")
    parser.add_argument(
        "--server-url",
        default=DEFAULT_SERVER_URL,
        help=f"Server URL (default: {DEFAULT_SERVER_URL})",
    )
    parser.add_argument(
        "--output-mode",
        default=DEFAULT_OUTPUT_MODE,
        choices=["clipboard", "direct_type"],
        help=f"Output mode (default: {DEFAULT_OUTPUT_MODE})",
    )
    parser.add_argument("--tray", action="store_true", help="Enable system tray icon")
    parser.add_argument(
        "--use-ollama", action="store_true", help="Enable Ollama text formatting"
    )
    parser.add_argument("--ollama-model", help="Ollama model to use (e.g., gemma3)")
    parser.add_argument(
        "--ollama-prompt", help="Prompt to send to Ollama for text formatting"
    )
    return parser


def validate_dependencies(args):
    """Validate that required dependencies are available"""
    import sys

    if args.tray and not TRAY_AVAILABLE:
        print("Tray icon functionality not available. Install required dependencies:")
        print("   pip install pystray pillow")
        sys.exit(1)


def setup_signal_handlers(client):
    """Setup signal handlers for the client"""
    signal.signal(signal.SIGINT, client.signal_handler)
    signal.signal(signal.SIGTERM, client.signal_handler)
    signal.signal(signal.SIGUSR1, client.signal_handler)


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    validate_dependencies(args)

    try:
        client = VoiceTypingClient(
            args.server_url,
            args.output_mode,
            args.tray,
            args.use_ollama,
            args.ollama_model,
            args.ollama_prompt,
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1

    print(f"Output mode: {args.output_mode}")
    if args.tray:
        print("Tray icon enabled")
    if args.use_ollama:
        print(
            f"Ollama enabled - Model: {args.ollama_model}, Prompt: {args.ollama_prompt}"
        )

    setproctitle("whisper-typing")
    setup_signal_handlers(client)

    try:
        client.run()
    except Exception as e:
        print(f"Client error: {e}")
        return 1
    finally:
        # Cleanup handled by signal handlers
        pass

    return 0


if __name__ == "__main__":
    main()
