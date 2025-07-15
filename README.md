# Whisper Typing

A voice-to-text system using OpenAI's Whisper model for real-time speech recognition and typing. This project consists of a FastAPI server for speech transcription and a Python client for voice recording and text output.

## Features

- Real-time voice recording with toggle functionality
- GPU-accelerated speech recognition using Whisper large-v3 model
- Multiple output modes: clipboard or direct typing
- Signal-based control for seamless integration
- Japanese language support (configurable)
- Health monitoring and error handling

## Components

### Server (`server.py`)

- FastAPI-based transcription service
- Uses `faster-whisper` with CUDA acceleration
- Accepts audio files and returns transcribed text
- Optimized for Japanese language recognition
- Health check endpoint for monitoring

### Client (`client.py`)

- Voice recording daemon with signal handling
- Two output modes:
  - `clipboard`: Copy transcribed text to clipboard
  - `direct_type`: Type directly using `wtype` command
- Process management with PID file
- Configurable server URL and output mode

### Control Script (`voice_control.py`)

- Command-line interface for controlling the voice typing daemon
- Supports toggle, status, and quit commands

## Usage

This project uses Nix flakes for reproducible builds and dependency management.

### 1. Start the Server

```bash
nix run github:yadokani389/whisper-typing#server
```

The server will start on `http://localhost:18031` with GPU acceleration enabled.

### 2. Start the Client

```bash
# Default mode (direct typing)
nix run github:yadokani389/whisper-typing#server

# With custom server URL and output mode
nix run github:yadokani389/whisper-typing#server -- http://localhost:18031 clipboard

# Available output modes:
# - clipboard: Copy to clipboard only
# - direct_type: Type directly without using clipboard
```

### 3. Control Voice Recording

#### Using Signals (Recommended)

```bash
# Toggle recording on/off
pkill -SIGUSR1 whisper-typing

# Check status
pkill -SIGUSR2 whisper-typing

# Quit daemon
pkill -SIGTERM whisper-typing
```

#### Using Control Script

```bash
# Toggle recording
python voice_control.py toggle

# Check status
python voice_control.py status

# Quit daemon
python voice_control.py quit
```

## Configuration

### Server Configuration

- **Model**: Whisper large-v3 (configurable in `server.py:11`)
- **Device**: CUDA with float16 precision
- **Language**: Japanese (`ja`)
- **Port**: 18031 (default)

### Client Configuration

- **Server URL**: `http://localhost:18031` (default)
- **Output Mode**: `direct_type` (default)
- **Sample Rate**: 16000 Hz
- **PID File**: `/tmp/voice_typing_client.pid`

## API Endpoints

### POST /transcribe

Transcribe uploaded audio file to text.

**Request:**

- `file`: Audio file (multipart/form-data)

**Response:**

```json
{
  "transcription": "transcribed text here"
}
```
