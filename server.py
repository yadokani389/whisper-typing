#!/usr/bin/env python3
import argparse
import io
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel

app = FastAPI()

# Global configuration
OLLAMA_BASE_URL = "http://localhost:11434"

# Initialize model on startup
model = WhisperModel("large-v3", device="cuda", compute_type="float16")


async def format_with_ollama(text: str, model_name: str, prompt: str) -> str:
    """Format text using Ollama API"""
    try:
        full_prompt = f"{prompt}\n\n{text}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": model_name, "prompt": full_prompt, "stream": False},
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", text)
            else:
                print(f"Ollama API error: {response.status_code}")
                return text

    except Exception as e:
        print(f"Ollama formatting error: {e}")
        return text


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = Form(...),
    use_ollama: bool = Form(False),
    ollama_model: Optional[str] = Form(None),
    ollama_prompt: Optional[str] = Form(None),
):
    """Transcribe uploaded audio file to text with optional Ollama formatting"""
    try:
        # Read uploaded file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)

        # Transcribe audio
        segments, info = model.transcribe(
            audio=file_stream,
            beam_size=5,
            language="ja",
            vad_filter=True,
            without_timestamps=True,
            condition_on_previous_text=False,
        )

        # Combine segments into single text
        result_text = ""
        for segment in segments:
            result_text += segment.text

        transcription = result_text.strip()

        # Format with Ollama if requested
        if use_ollama and ollama_model and ollama_prompt and transcription:
            formatted_text = await format_with_ollama(
                transcription, ollama_model, ollama_prompt
            )
            return {"transcription": transcription, "formatted_text": formatted_text}

        return {"transcription": transcription}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Whisper Typing Server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=18031,
        help="Port to bind the server to (default: 18031)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API base URL (default: http://localhost:11434)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Update global configuration
    OLLAMA_BASE_URL = args.ollama_url

    print(f"Starting Whisper Typing Server on {args.host}:{args.port}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")

    uvicorn.run(app, host=args.host, port=args.port)
