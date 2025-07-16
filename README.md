# Whisper Typing

A voice-to-text system using OpenAI's Whisper model for real-time speech recognition and typing. This project consists of a FastAPI server for speech transcription and a Python client for voice recording and text output.

## Features

- Real-time voice recording with toggle functionality
- GPU-accelerated speech recognition using Whisper large-v3 model
- Multiple output modes: clipboard or direct typing
- Signal-based control for seamless integration
- Japanese language support (configurable)
- Optional system tray icon with visual status indicators
- Error handling

## Components

### Server (`server.py`)

- FastAPI-based transcription service
- Uses `faster-whisper` with CUDA acceleration
- Accepts audio files and returns transcribed text
- Optimized for Japanese language recognition

### Client (`client.py`)

- Voice recording daemon with signal handling
- Two output modes:
  - `clipboard`: Copy transcribed text to clipboard
  - `direct_type`: Type directly using `wtype` command
- Configurable server URL and output mode
- Optional system tray icon with status-based visual indicators:
  - 🟢 Green: Idle/ready
  - 🔴 Red: Recording
  - ⚫ Gray: Stopped/error

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
nix run github:yadokani389/whisper-typing#client

# With custom configuration using flags
nix run github:yadokani389/whisper-typing#client -- --server-url http://localhost:18031 --output-mode clipboard

# Enable system tray icon
nix run github:yadokani389/whisper-typing#client -- --tray

# Show available options
nix run github:yadokani389/whisper-typing#client -- --help
```

#### Command Line Options

- `--server-url`: Server URL (default: `http://localhost:18031`)
- `--output-mode`: Output mode (default: `direct_type`)
  - `clipboard`: Copy to clipboard only
  - `direct_type`: Type directly without using clipboard
- `--tray`: Enable system tray icon with visual status indicators

### 3. Control Voice Recording

#### Signal-based Control

```bash
# Toggle recording on/off
pkill -SIGUSR1 whisper-typing

# Quit daemon
pkill -SIGTERM whisper-typing
```

#### Tray Icon Control (when `--tray` is enabled)

- Right-click the tray icon to access the menu
- **Toggle Recording**: Start/stop voice recording
- **Status**: Show current application status
- **Quit**: Exit the application

#### Status Indicators

- 🟢 **Green**: Ready/idle - waiting for voice input
- 🔴 **Red**: Recording - actively capturing audio
- ⚫ **Gray**: Stopped/error - application stopped or server unreachable

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
