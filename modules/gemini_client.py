import os
import json
import time
from typing import Optional, Callable, Any
from google import genai

# Global client
_client = None

def configure(api_keys_str: str):
    """Configures the new Gemini API client with the given key."""
    global _client
    if not api_keys_str:
        raise ValueError("API key is required.")
    
    keys = [k.strip() for k in api_keys_str.split(',') if k.strip()]
    if keys:
        # Initialize the new google-genai Client
        _client = genai.Client(api_key=keys[0])
    else:
        raise ValueError("Invalid API key format.")

def get_model_by_name(model_name: str) -> Any:
    """Returns the model name string, which acts as the model reference for the new SDK."""
    return model_name

def _is_state(file_obj, target_state):
    if hasattr(file_obj.state, 'name'):
        return file_obj.state.name == target_state
    return str(file_obj.state) == target_state

def upload_video_file(video_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> Any:
    """Uploads a file to Gemini and waits for it to be active using the new SDK."""
    if not _client:
        raise ValueError("Gemini client is not configured.")
        
    if progress_callback:
        progress_callback(f"Uploading {os.path.basename(video_path)}... (Please wait)")
    
    uploaded_file = _client.files.upload(file=video_path)
    
    dots = 0
    while _is_state(uploaded_file, "PROCESSING"):
        dots = (dots + 1) % 4
        if progress_callback:
            progress_callback(f"File uploaded. Waiting for Gemini AI to process{'.' * dots}")
        time.sleep(2)
        uploaded_file = _client.files.get(name=uploaded_file.name)
            
    if _is_state(uploaded_file, "FAILED"):
        raise ValueError("File processing failed on Gemini servers.")
        
    if progress_callback:
        progress_callback("File is ready!")
        
    return uploaded_file

def upload_audio_file(audio_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> Any:
    """Alias for upload_video_file as the new SDK handles audio and video files the same way."""
    return upload_video_file(audio_path, progress_callback)

from google.genai import types

def generate_with_retry(
    model: Any, 
    prompt: str, 
    video_file: Optional[Any] = None, 
    max_retries: int = 3, 
    progress_callback: Optional[Callable[[str], None]] = None,
    **kwargs
) -> str:
    """Generates content using the new SDK, with automatic retries."""
    if not _client:
        raise ValueError("Gemini client is not configured.")
        
    contents = []
    if video_file:
        contents.append(video_file)
    contents.append(prompt)
    
    config = None
    if "temperature" in kwargs:
        config = types.GenerateContentConfig(temperature=kwargs["temperature"])
    
    for attempt in range(max_retries):
        try:
            if progress_callback:
                progress_callback(f"Generating content (Attempt {attempt+1}/{max_retries})...")
            
            response = _client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            return response.text
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error on attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
    return ""

def parse_json_response(response_text: str) -> Any:
    """Parses JSON from a model response, handling markdown blocks."""
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    return json.loads(text)
