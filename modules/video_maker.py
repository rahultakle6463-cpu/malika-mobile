import os
import glob
import subprocess
import shutil
import sys

def create_review_video(audio_path, frames_dir, output_path, left_text="", right_text="", border_color="black", font_size=50, left_pos=None, right_pos=None, frame_durations=None, manual_blocks=None, contrast_val=1.0, progress_callback=None):
    """
    Creates an MP4 video using FFmpeg.
    Super fast rendering using concat demuxer. No zoompan.
    """
    if progress_callback: progress_callback("Initializing Video Maker (Fast Mode)...")

    if not os.path.exists(frames_dir):
        raise FileNotFoundError(f"Frames directory not found: {frames_dir}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_exe = "ffmpeg"

    if progress_callback: progress_callback("Analyzing audio duration...")
    
    try:
        from moviepy.editor import AudioFileClip
        with AudioFileClip(audio_path) as audio:
            total_duration = audio.duration
    except Exception:
        total_duration = 0

    temp_dir = os.path.join(os.path.dirname(frames_dir), "temp_video_clips")
    os.makedirs(temp_dir, exist_ok=True)
    
    concat_file_path = os.path.join(temp_dir, "concat.txt")
    
    # 1. Determine durations
    clips_data = []
    
    if manual_blocks and len(manual_blocks) > 0:
        if progress_callback: progress_callback("Using Manual Sync blocks...")
        frame_files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) + glob.glob(os.path.join(frames_dir, "*.png")))
        last_sec = 0.0
        last_idx = 0
        for b in manual_blocks:
            end_sec = float(b.get('end_seconds', 0))
            end_idx = int(b.get('end_frame_index', 0))
            block_dur = end_sec - last_sec
            frames_in_block = end_idx - last_idx
            
            if frames_in_block > 0 and block_dur > 0:
                dur_per_frame = block_dur / frames_in_block
                for i in range(last_idx, min(end_idx, len(frame_files))):
                    clips_data.append((frame_files[i], dur_per_frame))
            last_sec = end_sec
            last_idx = end_idx
            
        # Safeguard: If user didn't sync all the way to the end of the audio
        if total_duration > last_sec:
            rem_dur = total_duration - last_sec
            rem_frames = len(frame_files) - last_idx
            if rem_frames > 0:
                if progress_callback: progress_callback(f"Auto-syncing {rem_frames} remaining frames to the end of audio...")
                dur_per_frame = rem_dur / rem_frames
                for i in range(last_idx, len(frame_files)):
                    clips_data.append((frame_files[i], dur_per_frame))
            else:
                # Extend the very last frame if no frames are left
                if clips_data:
                    last_fpath, last_dur = clips_data[-1]
                    clips_data[-1] = (last_fpath, last_dur + rem_dur)
    else:
        frame_files = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")) + glob.glob(os.path.join(frames_dir, "*.png")))
        if not frame_files:
            raise ValueError(f"No frames found in {frames_dir}.")
            
        if frame_durations and len(frame_durations) > 0:
            if progress_callback: progress_callback("Using AI Sync durations...")
            for f in frame_files:
                fname = os.path.basename(f)
                dur = float(frame_durations.get(fname, 1.0))
                clips_data.append((f, dur))
        else:
            if progress_callback: progress_callback("Using Equal durations...")
            dur = total_duration / len(frame_files) if total_duration > 0 else 5.0
            for f in frame_files:
                clips_data.append((f, dur))
                
    # 2. Write concat.txt
    with open(concat_file_path, 'w', encoding='utf-8') as cf:
        for fpath, dur in clips_data:
            abs_path = os.path.abspath(fpath).replace("\\", "/")
            safe_path = abs_path.replace("'", "'\\''")
            cf.write(f"file '{safe_path}'\n")
            cf.write(f"duration {dur:.3f}\n")
        # The concat demuxer requires the last file to be repeated without duration
        if clips_data:
            abs_path = os.path.abspath(clips_data[-1][0]).replace("\\", "/")
            safe_path = abs_path.replace("'", "'\\''")
            cf.write(f"file '{safe_path}'\n")

    # 3. Prepare filter complex
    # No zoompan. Just scale, pad, contrast
    base_filter = (
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )
    if contrast_val and contrast_val != 1.0:
        base_filter += f",eq=contrast={contrast_val}"

    overlay_path = None
    if left_text or right_text:
        overlay_path = os.path.join(temp_dir, "overlay.png")
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_overlay.py")
        
        cmd = [sys.executable, script_path, "--output", overlay_path]
        if left_text:
            cmd.extend(["--left", left_text])
        if right_text:
            cmd.extend(["--right", right_text])
        cmd.extend(["--border_color", str(border_color)])
        cmd.extend(["--font_size", str(font_size)])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            filter_complex = f"[0:v]{base_filter}[bg];[1:v]scale=1920:1080[ov];[bg][ov]overlay=0:0[out]"
        except subprocess.CalledProcessError as e:
            print(f"Failed to create text overlay subprocess: {e.stderr}")
            filter_complex = f"[0:v]{base_filter}[out]"
            overlay_path = None
    else:
        filter_complex = f"[0:v]{base_filter}[out]"

    if progress_callback: progress_callback("Rendering Video (Lightning Fast)...")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file_path
    ]
    
    if overlay_path and os.path.exists(overlay_path):
        cmd.extend(["-i", overlay_path])
        audio_index = 2
    else:
        audio_index = 1
        
    cmd.extend([
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", f"{audio_index}:a",
        "-c:v", "libx264",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ])
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, text=True, encoding='utf-8', errors='replace')
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed while generating video:\n{e.stderr}")

    if progress_callback: progress_callback("Cleaning up temporary files...")
    shutil.rmtree(temp_dir, ignore_errors=True)

    if progress_callback: progress_callback("Video Rendering Complete!")
