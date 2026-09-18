import os

def analyse_photo(image_bytes: bytes, mime_type: str) -> tuple[str, str]:
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Image size exceeds 10MB limit")
        
    if not mime_type.startswith("image/"):
        raise ValueError("Invalid mime type, must be an image")
        
    gemini_enabled = os.environ.get("GEMINI_PHOTO_ENABLED", "false").lower() == "true"
    
    if gemini_enabled:
        # In a real scenario, this would call the Gemini API
        return "The image shows a scene with visible particulate matter or emissions. This is an objective visual assessment.", "gemini"
    else:
        return "Image received but AI analysis is currently disabled. Generic scene detected.", "placeholder"
