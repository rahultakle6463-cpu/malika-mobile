import streamlit as st
import os
import shutil
import glob
import json
import base64
import streamlit.components.v1 as components
from modules import gemini_client, v2_analyzer, frame_extractor, video_maker, thumbnail_generator
from PIL import Image

# --- Configuration ---
st.set_page_config(page_title="Malika V2 Ultimate", page_icon="🚀", layout="wide")
st.title("🚀 Malika V2 Ultimate Cloud Suite")
st.markdown("Your entire YouTube automation studio, running 100% on the cloud.")

# --- Session State ---
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'transcript_data' not in st.session_state:
    st.session_state.transcript_data = []
if 'frames_dir' not in st.session_state:
    st.session_state.frames_dir = ""
if 'final_script' not in st.session_state:
    st.session_state.final_script = ""

# Global settings
st.sidebar.header("⚙️ Global Settings")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password", value=st.session_state.api_key)
if api_key_input:
    st.session_state.api_key = api_key_input
    gemini_client.configure(st.session_state.api_key)

selected_model = st.sidebar.selectbox("Gemini Model", [
    "gemini-1.5-pro",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite"
])
st.session_state.model_name = selected_model

# Directories
temp_base = "temp_cloud"
os.makedirs(temp_base, exist_ok=True)
shows_dir = "shows"
os.makedirs(shows_dir, exist_ok=True)

# Helper: Load characters
def get_characters(serial_name):
    char_file = os.path.join(shows_dir, serial_name, "characters.json")
    if os.path.exists(char_file):
        try:
            with open(char_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict): return list(data.keys())
                if isinstance(data, list): return data
        except:
            pass
    return []

def save_characters(serial_name, char_list):
    char_file = os.path.join(shows_dir, serial_name, "characters.json")
    os.makedirs(os.path.dirname(char_file), exist_ok=True)
    try:
        with open(char_file, "w", encoding="utf-8") as f:
            json.dump(char_list, f, ensure_ascii=False, indent=4)
    except:
        pass

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 1. Script Engine", "🎬 2. Video Maker", "🖼️ 3. Thumbnail Maker", "📝 4. Script Editor", "🔊 5. ElevenLabs Tagger"])

# ==========================================
# TAB 1: SCRIPT ENGINE
# ==========================================
with tab1:
    st.header("1. The Transcript & Script Engine")
    
    # 1. Shows Dropdown
    existing_shows = [d for d in os.listdir(shows_dir) if os.path.isdir(os.path.join(shows_dir, d))]
    selected_serial = st.selectbox("Select TV Show/Serial", ["Select Show...", "➕ Add New Serial..."] + existing_shows)
    
    if selected_serial == "➕ Add New Serial...":
        new_serial_name = st.text_input("Enter New Serial Name:")
        initial_chars = st.text_input("Enter Main Characters (comma separated):", placeholder="e.g. Sachin, Sayali, Arjun, Vimal")
        if st.button("Create Serial"):
            if new_serial_name.strip():
                os.makedirs(os.path.join(shows_dir, new_serial_name.strip()), exist_ok=True)
                if initial_chars.strip():
                    char_list = [c.strip() for c in initial_chars.split(",") if c.strip()]
                    save_characters(new_serial_name.strip(), char_list)
                st.success(f"Serial '{new_serial_name}' created! Please refresh the page to select it.")
                st.rerun()
            else:
                st.error("Name cannot be empty.")
    
    elif selected_serial != "Select Show...":
        uploaded_vid = st.file_uploader("Upload Serial Episode (Video or Audio)", type=['mp4', 'avi', 'mov', 'mp3', 'wav', 'm4a'])
        
        if st.button("Extract Transcript & Frames", key="btn_extract"):
            if not uploaded_vid:
                st.error("Please upload a video or audio file first!")
            elif not st.session_state.api_key:
                st.error("Please enter your Gemini API Key in the sidebar!")
            else:
                with st.status("🎬 Processing Episode (Smart Mode)...", expanded=True) as status_box:
                    is_audio_only = uploaded_vid.name.lower().endswith(('.mp3', '.wav', '.m4a'))
                    
                    vid_path = os.path.join(temp_base, "episode.mp4" if not is_audio_only else uploaded_vid.name)
                    with open(vid_path, "wb") as f:
                        f.write(uploaded_vid.getbuffer())
                    
                    frames_dir = os.path.join(temp_base, "frames")
                    if os.path.exists(frames_dir):
                        shutil.rmtree(frames_dir)
                    os.makedirs(frames_dir, exist_ok=True)
                    
                    def log_cb(msg):
                        status_box.write(f"🔄 {msg}")
                    
                    if not is_audio_only:
                        # 1. Create Lightweight Proxy (High Quality Audio)
                        proxy_path = os.path.join(temp_base, "proxy_temp.mp4")
                        status_box.write("⚙️ Creating 480p proxy with 128k High-Quality Audio for AI...")
                        import subprocess
                        proxy_cmd = [
                            'ffmpeg', '-y', '-i', vid_path,
                            '-vf', 'scale=-2:480',
                            '-r', '2',
                            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '35',
                            '-c:a', 'aac', '-b:a', '128k', # UPGRADED AUDIO BITRATE
                            proxy_path
                        ]
                        try:
                            subprocess.run(proxy_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            upload_target = proxy_path
                            status_box.write("✅ Proxy created successfully!")
                        except Exception as e:
                            status_box.write(f"⚠️ Proxy failed, using original video: {e}")
                            upload_target = vid_path
                    else:
                        status_box.write("🔊 Audio file detected! Skipping video proxy creation...")
                        upload_target = vid_path
                        
                    # 2. Upload and Transcribe (Native Continuation Loop)
                    status_box.write("☁️ Uploading to Gemini...")
                    video_file = gemini_client.upload_video_file(upload_target, progress_callback=log_cb)
                    
                    status_box.write(f"🧠 AI ({st.session_state.model_name}) is transcribing (using Smart Continuation Loop)...")
                    full_transcript = v2_analyzer.generate_timestamp_transcript(
                        video_file=video_file,
                        serial_name=selected_serial,
                        model_name=st.session_state.model_name,
                        progress_callback=log_cb
                    )
                    
                    # Clean up proxy
                    try:
                        if os.path.exists(proxy_path): os.remove(proxy_path)
                    except:
                        pass
                            
                    # 3. Process Full Transcript
                    if full_transcript:
                        if not is_audio_only:
                            status_box.write("🎞️ Extracting High-Quality frames from Original Video for detected scenes...")
                            timestamps = list(set([item.get("timestamp", "00:00") for item in full_transcript]))
                            frames_map = frame_extractor.extract_frames_for_timestamps(
                                video_path=vid_path,
                                timestamps=timestamps,
                                output_dir=frames_dir,
                                progress_callback=log_cb
                            )
                            st.session_state.frames_dir = frames_dir
                            
                            for item in full_transcript:
                                ts = item.get("timestamp", "00:00")
                                item["frame_img"] = frames_map.get(ts, None)
                                item["user_tag"] = item.get("speaker", "")
                        else:
                            status_box.write("🔊 Audio mode: Skipping frame extraction...")
                            for item in full_transcript:
                                item["frame_img"] = None
                                item["user_tag"] = item.get("speaker", "")
                                
                        st.session_state.transcript_data = full_transcript
                        status_box.update(label="✅ Processing Complete!", state="complete", expanded=False)
                        st.success(f"Transcript Extracted ({len(full_transcript)} scenes)! Review and Tag below.")
                        
                        # Prepare ZIP file in memory (only if video was uploaded and frames exist)
                        if not is_audio_only and os.path.exists(frames_dir) and len(os.listdir(frames_dir)) > 0:
                            import zipfile
                            import io
                            mem_zip = io.BytesIO()
                            with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                                for root, _, files in os.walk(frames_dir):
                                    for file in files:
                                        zf.write(os.path.join(root, file), arcname=file)
                            mem_zip.seek(0)
                            
                            st.download_button(
                                label="📦 Download All Frames (ZIP)",
                                data=mem_zip,
                                file_name="extracted_frames.zip",
                                mime="application/zip",
                                help="Download your frames now so you can use them later in Tab 2 if you close the app!"
                            )
                        st.rerun()
                    else:
                        status_box.update(label="❌ AI Failed to generate transcript", state="error", expanded=True)

        # Tagging UI
        if st.session_state.transcript_data:
            st.markdown("### Review & Tag Characters")
            current_chars = get_characters(selected_serial)
            
            # Sort characters by frequency in current transcript so the most used is at the top!
            from collections import Counter
            counts = Counter([item.get("user_tag", item.get("speaker", "")) for item in st.session_state.transcript_data])
            # Sort: highest count first. If count is same or 0, maintain alphabetical or existing order.
            current_chars = sorted(current_chars, key=lambda x: counts.get(x, 0), reverse=True)
            
            with st.form("tagging_form"):
                updated_transcript = []
                
                for i, item in enumerate(st.session_state.transcript_data):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if item.get("frame_img") and os.path.exists(item["frame_img"]):
                            st.image(item["frame_img"], width=200, caption=item["timestamp"])
                    with col2:
                        st.markdown(f"**[{item['type'].upper()}]** {item['timestamp']} - *AI thinks: {item.get('speaker', '')}*")
                        
                        # Editable Text
                        new_text = st.text_area("Transcript Text", value=item.get('text', ''), key=f"txt_{i}", height=100)
                        
                        tag_options = current_chars if current_chars else ["Speaker 1"]
                        default_tag_idx = 0
                        predicted_speaker = item.get("user_tag", item.get("speaker", ""))
                        if predicted_speaker in tag_options:
                            default_tag_idx = tag_options.index(predicted_speaker)
                            
                        # Simulate Editable Combobox for Streamlit Form
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            selected_tag = st.selectbox(f"Select Character", tag_options, index=default_tag_idx, key=f"sel_{i}")
                        with col_t2:
                            custom_tag = st.text_input("Or Type New Name", placeholder="Leave empty to use selection", key=f"custom_{i}")
                            
                        final_tag = custom_tag.strip() if custom_tag.strip() else selected_tag
                            
                        updated_transcript.append({
                            "timestamp": item["timestamp"],
                            "type": item["type"],
                            "speaker": final_tag,
                            "text": new_text,
                            "frame_img": item["frame_img"],
                            "context": item.get("context", "")
                        })
                
                submit_tags = st.form_submit_button("💾 Save My Tags (Important: Click this to apply your selections!)")
                
                if submit_tags:
                    # Update session state with exact selections
                    for i, item in enumerate(updated_transcript):
                        item["user_tag"] = item["speaker"]
                        
                        # Dynamically add new characters to the global list!
                        t = item["speaker"].strip()
                        if t and t not in current_chars:
                            current_chars.insert(0, t)
                            
                    save_characters(selected_serial, current_chars)
                    st.session_state.transcript_data = updated_transcript
                    
                    st.success("✅ Tags Saved successfully! You can now Copy Transcript or Generate Script below.")
                    st.rerun()
                        
            # --- New Copy Transcript Button ---
            st.markdown("### 📋 1. Copy Tagged Transcript")
            st.info("👆 Use the copy icon on the top right of this box to copy your entire tagged transcript, or click the download button below!")
            
            tagged_text_output = ""
            for item in st.session_state.transcript_data:
                tagged_text_output += f"[{item['timestamp']}] {item['type'].upper()} || {item.get('speaker', '')} || {item.get('text', '')}\n"
            
            st.code(tagged_text_output, language="text")
            
            st.download_button(
                label="💾 Download Transcript (.txt)",
                data=tagged_text_output,
                file_name=f"{selected_serial.replace(' ', '_')}_transcript.txt",
                mime="text/plain"
            )
            
            # --- Generate Script Button ---
            st.markdown("### ✨ 2. Generate AI Blockbuster Script")
            st.info("Click below to automatically generate the YouTube Script using Gemini API.")
            if st.button("🚀 Generate Script (using Gemini)"):
                with st.spinner("Writing Blockbuster Script..."):
                    final_script = v2_analyzer.generate_final_script(st.session_state.transcript_data, progress_callback=lambda x: None)
                    st.session_state.final_script = final_script
                    st.rerun()
            
            # --- Emergency Prompt View ---
            with st.expander("🚨 View Emergency Prompt"):
                st.markdown("If you want to generate the script manually externally, use this prompt:")
                try:
                    with open("emergency_prompt.txt", "r", encoding="utf-8") as f:
                        em_prompt = f.read()
                    st.code(em_prompt, language="text")
                except:
                    st.warning("Emergency prompt file not found.")
                        
    # --- Always Visible Final Script & Prompt Generator ---
    st.markdown("---")
    st.markdown("### 📝 Final Script & ChatGPT Prompt")
    st.info("You can review the AI-generated script here, or PASTE/UPLOAD an existing script directly to generate a prompt!")
    
    uploaded_final_script = st.file_uploader("Upload Script File (.txt)", type=["txt"], key="final_script_upload")
    if uploaded_final_script:
        content = uploaded_final_script.getvalue().decode("utf-8")
        if st.session_state.final_script != content:
            st.session_state.final_script = content
            st.rerun()
            
    st.session_state.final_script = st.text_area("Final Script (Edit or Paste here)", st.session_state.final_script, height=400)
    
    st.markdown("#### 🤖 ChatGPT (DALL-E) Thumbnail Prompt Generator")
    prompt_style = st.selectbox("Select Thumbnail Style", ["1. Classic Grid", "2. Movie Poster", "3. Panel Split"])
    
    if st.button("Generate ChatGPT Prompt", key="btn_chatgpt"):
        if not st.session_state.final_script.strip():
            st.warning("Please generate or paste a script first!")
        elif not st.session_state.api_key:
            st.error("Please enter your Gemini API Key in the sidebar!")
        else:
            with st.spinner("Generating Prompt..."):
                style_idx = prompt_style.split(".")[0]
                chatgpt_prompt = v2_analyzer.generate_thumbnail_prompt(
                    script_text=st.session_state.final_script,
                    style=style_idx,
                    model_name=st.session_state.model_name,
                    progress_callback=lambda x: None
                )
                st.success("Prompt Generated!")
                st.info("Copy the prompt below and paste it into ChatGPT (along with 4 extracted frames) to generate an AI Thumbnail!")
                st.code(chatgpt_prompt, language="text")

# --- TAB 2: MANUAL SYNC ---
with tab2:
    st.header("2. MP4 Video Maker")
    st.markdown("Merge your Audio with Frames and Text Overlay. You can use Auto-Extracted frames or upload Manual frames.")
    
    audio_upload = st.file_uploader("Upload Voice Audio (MP3/WAV)", type=['mp3', 'wav'], key="aud")
    
    if audio_upload:
        st.audio(audio_upload, format="audio/mp3")
        
    st.markdown("### Frames Source")
    frame_source = st.radio("Choose Frames Source:", ["Use Extracted Frames (from Tab 1)", "Upload Frames ZIP File", "Upload Custom Frames Folder"])
    
    manual_frames_dir = os.path.join(temp_base, "manual_frames")
    os.makedirs(manual_frames_dir, exist_ok=True)
    
    if frame_source == "Upload Frames ZIP File":
        zip_upload = st.file_uploader("Upload Frames ZIP File", type=['zip'])
        if zip_upload:
            import zipfile
            for f in glob.glob(os.path.join(manual_frames_dir, "*")):
                try: os.remove(f)
                except: pass
            
            with zipfile.ZipFile(zip_upload, "r") as zf:
                zf.extractall(manual_frames_dir)
            st.success("Frames extracted from ZIP successfully!")
            
    elif frame_source == "Upload Custom Frames Folder":
        manual_uploads = st.file_uploader("Upload All Frames from Folder", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        if manual_uploads:
            for f in glob.glob(os.path.join(manual_frames_dir, "*")):
                try: os.remove(f)
                except: pass
            for idx, mf in enumerate(manual_uploads):
                save_path = os.path.join(manual_frames_dir, f"{idx:04d}_{mf.name}")
                with open(save_path, "wb") as f:
                    f.write(mf.getbuffer())
            st.success(f"Uploaded {len(manual_uploads)} frames successfully!")
            
    active_frames_dir = manual_frames_dir if frame_source in ["Upload Frames ZIP File", "Upload Custom Frames Folder"] else st.session_state.frames_dir
    
    active_frame_files = []
    if os.path.exists(active_frames_dir):
        active_frame_files = sorted(glob.glob(os.path.join(active_frames_dir, "*.jpg")) + glob.glob(os.path.join(active_frames_dir, "*.png")))
    
    with st.expander("⏱️ Fast Desktop-Style Sync", expanded=True):
        st.markdown("1. Play the **Audio Player** below (it stays at the top!).<br>2. Look at the **Horizontal Gallery** to find the frame number.<br>3. Type the time and frame number in the table at the bottom.", unsafe_allow_html=True)
        
        # Sticky Audio CSS
        st.markdown(
            """
            <style>
            [data-testid="stAudio"] {
                position: sticky;
                top: 0px;
                z-index: 999;
                background-color: #1e1e1e;
                padding: 10px;
                border-bottom: 2px solid #0dcaf0;
            }
            </style>
            """, unsafe_allow_html=True
        )
        
        if audio_upload:
            st.audio(audio_upload)
            
        st.markdown("### 🖼️ Horizontal Frame Gallery (Scroll Left-Right)")
        if active_frame_files:
            def get_b64_thumb(path):
                img = Image.open(path)
                img.thumbnail((160, 90))
                import io
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=60)
                return base64.b64encode(buf.getvalue()).decode()

            with st.spinner("Loading gallery..."):
                gallery_html = "<div style='display:flex; overflow-x:auto; gap:10px; padding-bottom:10px; font-family:sans-serif; color:white;'>"
                for idx, src in enumerate(active_frame_files):
                    b64 = get_b64_thumb(src)
                    gallery_html += f"<div style='text-align:center; min-width:160px; background:#333; padding:5px; border-radius:5px;'><img src='data:image/jpeg;base64,{b64}' style='width:100%; border-radius:3px;'><br><b>Frame {idx+1}</b></div>"
                gallery_html += "</div>"
            
            components.html(gallery_html, height=180, scrolling=True)
        else:
            st.info("No frames available.")
            
        import pandas as pd
        if "sync_blocks" not in st.session_state:
            st.session_state.sync_blocks = pd.DataFrame([
                {"End Time (e.g. 1.19 for 1m 19s)": "0.00", "End Frame Index": 1}
            ])
            
        st.session_state.sync_blocks = st.data_editor(
            st.session_state.sync_blocks,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### Overlay / Banner Settings")
    colA, colB = st.columns(2)
    with colA:
        left_txt = st.text_input("Left Top Text", "सौजन्य स्टार प्रवाह")
        b_color = st.selectbox("Border/Outline Color", ["black", "blue", "red", "green", "white"])
    with colB:
        right_txt = st.text_input("Right Top Text", "25 जुन")
        f_size = st.number_input("Text Size", min_value=20, max_value=150, value=50)
        
    contrast = st.number_input("Contrast (1.0 = normal)", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
    
    # Live Preview Button
    if st.button("👁️ Preview Banner on First Frame"):
        if active_frame_files:
            try:
                from PyQt5.QtGui import QImage, QPainter, QFont, QColor
                from PyQt5.QtCore import Qt
                
                # 1. Generate overlay.png using PyQt5 (Perfect Devanagari Support)
                overlay_path = os.path.join(temp_base, "preview_overlay.png")
                img_q = QImage(1920, 1080, QImage.Format_ARGB32)
                img_q.fill(Qt.transparent)
                
                painter = QPainter(img_q)
                font = QFont("Nirmala UI", int(f_size), QFont.Bold)
                painter.setFont(font)
                
                def draw_outlined(x, y, text):
                    base_y = int(y) + int(f_size * 1.2)
                    painter.setPen(QColor(b_color))
                    for dx in [-2, 0, 2]:
                        for dy in [-2, 0, 2]:
                            if dx != 0 or dy != 0: painter.drawText(int(x)+dx, base_y+dy, text)
                    painter.setPen(QColor("white"))
                    painter.drawText(int(x), base_y, text)
                
                if left_txt: draw_outlined(40, 40, left_txt)
                if right_txt: draw_outlined(1920 - 400, 40, right_txt)
                painter.end()
                img_q.save(overlay_path)
                
                # 2. Composite with first frame using PIL for Streamlit display
                base_img = Image.open(active_frame_files[0]).convert("RGBA")
                base_img = base_img.resize((1920, 1080))
                overlay_img = Image.open(overlay_path).convert("RGBA")
                
                preview_combined = Image.alpha_composite(base_img, overlay_img)
                
                st.image(preview_combined, caption="Live Overlay Preview (Perfect Devanagari Render)", use_container_width=True)
            except Exception as e:
                st.error(f"Error checking status: {e}")
        else:
            st.warning("Extract or upload frames first to see the preview!")
    
    if st.button("Generate MP4 Video", key="btn_vid"):
        active_dir = manual_frames_dir if frame_source in ["Upload Frames ZIP File", "Upload Custom Frames Folder"] else st.session_state.frames_dir
        
        if not audio_upload:
            st.error("Upload Audio first!")
        elif not os.path.exists(active_dir) or len(glob.glob(os.path.join(active_dir, "*"))) == 0:
            st.error("No frames available! Please upload frames or extract them in Tab 1.")
        else:
            with st.spinner("Rendering Final Video using FFmpeg (Please wait)..."):
                aud_path = os.path.join(temp_base, "voice.mp3")
                out_path = os.path.join(temp_base, "final_video.mp4")
                with open(aud_path, "wb") as f:
                    f.write(audio_upload.getbuffer())
                    
                try:
                    # Convert DataFrame to manual_blocks list of dicts
                    m_blocks = []
                    if "sync_blocks" in st.session_state:
                        for _, row in st.session_state.sync_blocks.iterrows():
                            # Parse custom string format 1.19 or 1:19 or 79
                            time_val = str(row.get("End Time (e.g. 1.19 for 1m 19s)", "0"))
                            time_val = time_val.replace(":", ".")
                            sec = 0.0
                            
                            if "." in time_val:
                                parts = time_val.strip().split(".")
                                if len(parts) == 2:
                                    min_part = int(parts[0]) if parts[0].isdigit() else 0
                                    sec_part = int(parts[1]) if parts[1].isdigit() else 0
                                    sec = (min_part * 60) + sec_part
                            else:
                                try: sec = float(time_val)
                                except: pass
                                
                            try:
                                idx = int(row.get("End Frame Index", 0))
                            except:
                                idx = 0
                                
                            if sec > 0 and idx > 0:
                                m_blocks.append({"end_seconds": sec, "end_frame_index": idx})
                    
                    video_maker.create_review_video(
                        audio_path=aud_path,
                        frames_dir=active_dir,
                        output_path=out_path,
                        left_text=left_txt,
                        right_text=right_txt,
                        border_color=b_color,
                        font_size=f_size,
                        manual_blocks=m_blocks if m_blocks else None,
                        contrast_val=contrast
                    )
                    st.success("Video Rendered Successfully!")
                    st.video(out_path)
                    
                    with open(out_path, "rb") as f:
                        st.download_button("💾 Download Final MP4", f, file_name="final_video.mp4", mime="video/mp4")
                except Exception as e:
                    st.error(f"Video Generation Failed: {str(e)}")

# ==========================================
# TAB 3: THUMBNAIL MAKER
# ==========================================
with tab3:
    st.header("3. Thumbnail Generator")
    
    st.markdown("Select 4 images to use for the thumbnail:")
    active_dir2 = manual_frames_dir if os.path.exists(manual_frames_dir) and len(glob.glob(os.path.join(manual_frames_dir, "*"))) > 0 else st.session_state.frames_dir
    
    available_images = []
    if os.path.exists(active_dir2):
        available_images = sorted(glob.glob(os.path.join(active_dir2, "*.jpg")) + glob.glob(os.path.join(active_dir2, "*.png")))
        
    if not available_images:
        st.info("Extract frames in Tab 1 or upload frames in Tab 2 to use them here.")
    else:
        # Multiselect for exactly 4 images
        selected_images_paths = st.multiselect("Choose exactly 4 images", available_images, default=available_images[:4] if len(available_images)>=4 else available_images)
        
        col1, col2 = st.columns(2)
        with col1:
            top_banner = st.text_input("Top Text", placeholder="Top Banner Text (e.g. सायली आणि प्रतिमाचा...)")
            bot_banner = st.text_input("Bottom Text", placeholder="Bottom Banner Text (e.g. आजच्या भागात मोठा ट्विस्ट...)")
            date_badge = st.text_input("Date Badge (Optional)", placeholder="Date Badge (e.g. 23 जून)")
        with col2:
            d1 = st.text_input("Dialogue 1", placeholder="Dialogue 1")
            d2 = st.text_input("Dialogue 2", placeholder="Dialogue 2")
            d3 = st.text_input("Dialogue 3", placeholder="Dialogue 3")
            d4 = st.text_input("Dialogue 4", placeholder="Dialogue 4")
            
        if st.button("Generate Thumbnail 🚀"):
            if len(selected_images_paths) != 4:
                st.error(f"Please select exactly 4 images! (You selected {len(selected_images_paths)})")
            else:
                with st.spinner("Generating Thumbnail..."):
                    thumb_out = os.path.join(temp_base, "thumbnail.jpg")
                    thumbnail_generator.generate_thumbnail(
                        selected_images_paths, top_banner, bot_banner, [d1, d2, d3, d4], date_badge, thumb_out
                    )
                    st.image(thumb_out)
                    with open(thumb_out, "rb") as f:
                        st.download_button("💾 Download Thumbnail", f, file_name="thumbnail.jpg", mime="image/jpeg")

# ==========================================
# TAB 4: SCRIPT EDITOR
# ==========================================
with tab4:
    st.header("4. Script Editor & Batch Splitter")
    st.markdown("Edit your script here. When ready, split it into 1200-character batches for ElevenLabs!")
    
    # File uploader for quick import
    uploaded_script = st.file_uploader("Optional: Upload a .txt script file", type=["txt"])
    
    if "raw_script" not in st.session_state:
        st.session_state.raw_script = ""
        
    if uploaded_script:
        content = uploaded_script.getvalue().decode("utf-8")
        if st.session_state.raw_script != content:
            st.session_state.raw_script = content
            st.rerun()

    # The massive text editor
    script_input = st.text_area("Your Script", value=st.session_state.raw_script, height=400, placeholder="Paste or type your script here...")
    st.session_state.raw_script = script_input
    
    if st.button("✂️ Split Script into Batches (Max 1200 chars)"):
        if not script_input.strip():
            st.warning("Please enter a script first.")
        else:
            st.success("Script split successfully! Click the 'Copy' icon in the top right of each batch box.")
            
            import re
            batches = []
            current_batch = ""
            
            paragraphs = re.split(r'(\n\n+)', script_input)
            
            for p in paragraphs:
                if len(current_batch) + len(p) > 1200:
                    if current_batch.strip():
                        batches.append(current_batch.strip())
                        current_batch = ""
                    
                    if len(p) > 1200:
                        sentences = re.split(r'(?<=[.!?।])\s+', p)
                        for s in sentences:
                            if len(current_batch) + len(s) > 1200:
                                if current_batch.strip():
                                    batches.append(current_batch.strip())
                                    current_batch = s + " "
                                else:
                                    batches.append(s)
                                    current_batch = ""
                            else:
                                current_batch += s + " "
                    else:
                        current_batch += p
                else:
                    current_batch += p
            
            if current_batch.strip():
                batches.append(current_batch.strip())
            
            for i, b in enumerate(batches):
                st.markdown(f"**Batch {i+1} ({len(b)} chars)**")
                st.code(b, language="text")

# ==========================================
# TAB 5: ELEVENLABS TAGGER
# ==========================================
with tab5:
    st.header("5. ElevenLabs Emotion Tagger")
    st.markdown("Automatically insert ElevenLabs emotion tags (like `[happy]`, `[sad]`) into your Marathi/Hindi script without changing the language!")
    
    tagger_models = [
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]
    selected_tagger_model = st.selectbox("Select Model", tagger_models, index=0, key="tagger_model")
    
    tagger_script = st.text_area("Script to Tag", height=300, placeholder="Paste your script here...", key="tagger_input")
    
    if st.button("🏷️ Generate Tagged Script"):
        if not tagger_script.strip():
            st.warning("Please enter a script to tag.")
        elif not st.session_state.api_key:
            st.error("Please configure Gemini API Key in the sidebar first.")
        else:
            with st.spinner("Tagging script..."):
                try:
                    from google import genai
                    client = genai.Client(api_key=st.session_state.api_key)
                    
                    system_prompt = """You are an expert director for daily soap serials. 
Your job is to insert ElevenLabs emotion tags into the provided script.
The script is in Marathi or Hindi. 
Insert ENGLISH emotion tags (e.g., [happy], [sad], [angry], [crying], [suspense], [shocked], [romantic], [serious], [pleading], [excited], [calm], [teasing], [relieved], [affectionate]) at the beginning of sentences or paragraphs where the emotion changes.
RULES:
1. DO NOT translate the script. Keep the original language exactly as it is.
2. ONLY insert the emotion tags in brackets.
3. Return ONLY the tagged script, nothing else."""

                    prompt = f"{system_prompt}\n\nHere is the script:\n\n{tagger_script}"
                    
                    response = client.models.generate_content(
                        model=selected_tagger_model,
                        contents=prompt
                    )
                    
                    if response.text:
                        st.success("Tagged successfully!")
                        st.code(response.text, language="text")
                    else:
                        st.error("Failed to generate tags.")
                except Exception as e:
                    st.error(f"Error: {e}")
