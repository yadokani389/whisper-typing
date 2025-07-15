import io

import torch
import uvicorn
from fastapi import FastAPI, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel

app = FastAPI()


def initialize_model():
    """Initialize Whisper model with automatic device detection"""
    if torch.cuda.is_available():
        return WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    else:
        return WhisperModel(
            "tiny",
            device="cpu",
            compute_type="int8",
        )


# Initialize model on startup
model = initialize_model()


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = Form(...)):
    """Transcribe uploaded audio file to text"""
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

        return {"transcription": result_text.strip()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": model is not None}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=18031)
