import streamlit as st
import edge_tts
import asyncio
import os
import subprocess
import uuid

# Configuration
VOICE = "mr-IN-AarohiNeural" # Marathi Female Voice (Azure Engine)
BGM_FILE = "suspense_bgm.mp3" # Keep this in the same folder if you want BGM

def mix_bgm(voice_file, bgm_file, final_output):
    if not os.path.exists(bgm_file):
        # If no BGM uploaded, just return the voice file
        return voice_file
        
    # Mix using FFmpeg
    cmd = [
        "ffmpeg", "-y", 
        "-i", voice_file, 
        "-stream_loop", "-1", "-i", bgm_file,
        "-filter_complex", "[0:a]volume=1.0[a0];[1:a]volume=0.10[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2",
        final_output
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return final_output
    except Exception as e:
        st.error(f"FFmpeg Error: {e}")
        return voice_file # Fallback to unmixed audio

async def generate_audio(text, output_filename):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_filename)

st.set_page_config(page_title="Malika v2 Cloud App", page_icon="📱")

st.title("📱 Malika v2 (Zero-Cost Mobile Studio)")
st.write("Welcome to your private YouTube Automation Studio. This runs 100% on the cloud.")

# Serial Selection
serial_name = st.selectbox("Select Serial Target:", ["Bai Tuza Ashirwad", "Lapandav", "Other"])

# Script Input
st.subheader("📝 Step 1: Paste Your Script")
script_text = st.text_area("Paste your 10,000 characters script here:", height=250)

# Optional BGM Upload
st.subheader("🎵 Step 2: Background Music (Optional)")
uploaded_bgm = st.file_uploader("Upload 'Suspense BGM' (MP3) - Optional", type=["mp3"])
if uploaded_bgm:
    with open(BGM_FILE, "wb") as f:
        f.write(uploaded_bgm.getbuffer())
    st.success("BGM Uploaded successfully!")

# Generate Button
if st.button("🚀 Step 3: Generate Final Audio"):
    if not script_text.strip():
        st.warning("Please paste a script first!")
    else:
        with st.spinner("Generating High-Quality AI Voice... Please wait..."):
            # Unique filenames to avoid clash
            raw_audio = f"voice_{uuid.uuid4().hex}.mp3"
            final_audio = f"final_{uuid.uuid4().hex}.mp3"
            
            # 1. Generate Voice
            asyncio.run(generate_audio(script_text, raw_audio))
            
            # 2. Mix BGM
            with st.spinner("Mixing Suspense BGM using FFmpeg..."):
                output_file = mix_bgm(raw_audio, BGM_FILE, final_audio)
            
            st.success("✅ Final Audio Ready!")
            
            # Provide Audio Player
            st.audio(output_file, format='audio/mp3')
            
            # Provide Download Button
            with open(output_file, "rb") as file:
                st.download_button(
                    label="💾 Download Final MP3 to Phone",
                    data=file,
                    file_name=f"{serial_name.replace(' ', '_')}_audio.mp3",
                    mime="audio/mp3"
                )
            
            # Cleanup temp files
            try:
                os.remove(raw_audio)
                if output_file == final_audio:
                    os.remove(final_audio)
            except:
                pass
