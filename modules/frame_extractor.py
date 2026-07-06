import cv2
import os
import math

def extract_frames(video_path: str, output_dir: str, fps_extract: float = 1.0, progress_callback=None) -> list:
    """
    Extract frames from a video at a specific frame rate.
    Returns a list of dicts: [{"timestamp_str": "00:05", "timestamp_sec": 5.0, "frame_path": "path/to/frame.jpg"}]
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps else 0
    
    if progress_callback:
        progress_callback(f"Extracting frames from video (Duration: {int(duration)}s) at {fps_extract} FPS...")
        
    frame_interval = int(fps / fps_extract) if fps > 0 else 30
    
    frames_data = []
    current_frame = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if current_frame % frame_interval == 0:
            timestamp_sec = current_frame / fps
            
            # Format timestamp as MM:SS
            minutes = int(timestamp_sec // 60)
            seconds = int(timestamp_sec % 60)
            timestamp_str = f"{minutes:02d}:{seconds:02d}"
            
            frame_filename = f"frame_{minutes:02d}m_{seconds:02d}s.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            
            # Save the frame
            cv2.imwrite(frame_path, frame)
            
            frames_data.append({
                "timestamp_str": timestamp_str,
                "timestamp_sec": timestamp_sec,
                "frame_path": frame_path
            })
            
            saved_count += 1
            if progress_callback and saved_count % 10 == 0:
                progress_callback(f"Extracted {saved_count} frames... (Time: {timestamp_str})")
                
        current_frame += 1
        
    cap.release()
    
    if progress_callback:
        progress_callback(f"Finished extracting {saved_count} frames to {output_dir}")
        
    return frames_data

def extract_frames_for_timestamps(video_path: str, timestamps: list, output_dir: str, progress_callback=None) -> dict:
    """
    Extracts frames only at specific timestamps.
    timestamps: list of "MM:SS" or "HH:MM:SS" strings
    Returns: dict mapping timestamp -> frame path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")
        
    if progress_callback:
        progress_callback(f"Extracting {len(timestamps)} specific frames on-demand...")
        
    frames_map = {}
    for ts_str in timestamps:
        try:
            parts = ts_str.split(":")
            if len(parts) == 2:
                target_sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                target_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                continue
                
            # Jump to the exact millisecond
            cap.set(cv2.CAP_PROP_POS_MSEC, target_sec * 1000)
            ret, frame = cap.read()
            if ret:
                # Format timestamp safely for windows filenames
                safe_ts = ts_str.replace(":", "_")
                frame_filename = f"frame_{safe_ts}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                
                cv2.imwrite(frame_path, frame)
                frames_map[ts_str] = frame_path
                
        except Exception as e:
            pass # Ignore invalid timestamps
            
    cap.release()
    
    if progress_callback:
        progress_callback(f"Finished extracting {len(frames_map)} on-demand frames.")
        
    return frames_map



def get_closest_frame(timestamp_str: str, frames_data: list) -> str:
    """
    Given a timestamp like "00:05" or "01:23", find the closest frame image path.
    """
    try:
        parts = timestamp_str.split(":")
        if len(parts) == 2:
            target_sec = int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            target_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return None
    except ValueError:
        return None
        
    closest_frame = None
    min_diff = float("inf")
    
    for fd in frames_data:
        diff = abs(fd["timestamp_sec"] - target_sec)
        if diff < min_diff:
            min_diff = diff
            closest_frame = fd["frame_path"]
            
    return closest_frame