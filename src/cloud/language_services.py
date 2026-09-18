import os

def transcribe_audio(audio_bytes: bytes, language_code: str, mime_type: str) -> str:
    stt_enabled = os.environ.get("SPEECH_TO_TEXT_ENABLED", "false").lower() == "true"
    
    if not stt_enabled:
        raise RuntimeError("Speech-to-text service is currently disabled")
        
    # In a real scenario, this would call Google STT API
    return f"[Simulated transcription in {language_code} from {mime_type} audio]"
