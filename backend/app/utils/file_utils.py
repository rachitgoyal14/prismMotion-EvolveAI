import re
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile

def sanitize_filename(filename: str) -> str:
    """
    Remove problematic characters from filenames.
    
    Handles:
    - Non-breaking spaces (\u202f, \xa0)
    - Special characters
    - Multiple spaces
    
    Examples:
        "Screenshot 2026-02-06 at 7.27.42 PM.png" 
        → "Screenshot_2026_02_06_at_7_27_42_PM.png"
        
        "My Brand Logo™.png"
        → "My_Brand_Logo.png"
    """
    # Replace non-breaking spaces and other unicode spaces with regular spaces
    filename = filename.replace('\u202f', ' ').replace('\xa0', ' ')
    
    # Split into name and extension
    parts = filename.rsplit('.', 1)
    name = parts[0]
    ext = parts[1] if len(parts) > 1 else ''
    
    # Remove or replace problematic characters (keep alphanumeric, dash, underscore)
    name = re.sub(r'[^\w\s\-]', '', name)
    
    # Replace spaces and multiple underscores/dashes with single underscore
    name = re.sub(r'[\s_\-]+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Reassemble with extension
    return f"{name}.{ext}" if ext else name

def save_compliance_asset(uploaded_file: UploadFile, video_id: str, remotion_public_dir: Path) -> str:
    """
    Save uploaded file with sanitized name to remotion/public/media/{video_id}/
    
    Args:
        uploaded_file: FastAPI UploadFile object
        video_id: Unique video identifier
        remotion_public_dir: Path to remotion/public directory
        
    Returns:
        Sanitized filename (just the filename, not full path)
    """
    if not uploaded_file or not uploaded_file.filename:
        return None
    
    original_name = uploaded_file.filename
    clean_name = sanitize_filename(original_name)
    
    dest_dir = remotion_public_dir / "media" / video_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = dest_dir / clean_name
    
    # Save file
    with dest_path.open("wb") as f:
        shutil.copyfileobj(uploaded_file.file, f)
    
    return clean_name