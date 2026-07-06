import json
from typing import Optional, Callable
from modules import gemini_client

V2_TRANSCRIPT_PROMPT = """You are a highly detail-oriented video transcriber.
Watch and LISTEN to this video extremely carefully. 
Your primary job is to extract EVERY SINGLE DIALOGUE spoken (word-for-word in Marathi/Hindi) from start to finish.

KNOWN CHARACTERS IN THIS SERIAL:
{known_characters}
(If a speaker matches one of these characters, use their exact name!)

CRITICAL AUDIO ACCURACY RULES:
1. STRICTLY WRITE IN MARATHI SCRIPT (DEVANAGARI). Do NOT translate dialogues to English. Do NOT write Marathi in English letters (e.g. write "कुठे आहेस", not "kuthe aahes").
2. DO NOT HALLUCINATE OR GUESS DIALOGUES. 
3. ONLY write down exactly what you hear in the audio track. Pay extremely close attention to the natural Marathi words.
4. If the audio is unclear, write "[unclear]".

OUTPUT FORMAT (STRICT PLAIN TEXT):
You must output the result in the following plain text format. Do NOT use JSON. Do NOT use markdown.
Separate fields using exactly double pipes `||`.

[00:05] ACTION || None || Action Description (e.g. A man secretly enters)
[01:23] DIALOGUE || Speaker Name || Emotional Context || The exact dialogue spoken word-for-word

CRITICAL:
- Every line must start with the timestamp in [MM:SS] format.
- Do not skip any part of the video! Keep extracting until the video completely ends.
- At the very end of the transcript, you MUST print the exact word: [END_OF_VIDEO]
"""

V2_SCRIPT_PROMPT_PART_1 = """You are an experienced YouTube TV serial review creator.
Here is PART 1 of the highly detailed transcript of the video episode:
{tagged_transcript}

Write the BEGINNING of an ENGAGING YOUTUBE NARRATION SCRIPT in Marathi.
Structure:
[HOOK] - (DERRAL EVES STYLE) Start IMMEDIATELY with the most shocking twist or suspense of the episode in 2-3 lines. Create a massive "Curiosity Gap". DO NOT say Hello, Welcome, or "I am late" here. Just drop the bomb!
[INTRO] - Welcome viewers briefly.
[SCENE BY SCENE EXPLANATION WITH REACTIONS] - Explain the episode play-by-play.

CRITICAL RULES FOR HIGH RETENTION:
1. NARRATE LIKE A STORYTELLER: Blend the actions and dialogues into a continuous, engaging paragraph.
2. DO NOT MISS ANY DIALOGUES: You MUST cover all the dialogues provided in the transcript, but DO NOT just dump them like 'Name: Dialogue'. Weave them naturally and EXPLAIN what they mean.
3. ADD YOUR REACTIONS: Add personal reactions and casual words (e.g., "बापरे हे सगळं भयंकर आहे", "काय वाटत बरं प्रेक्षकांनो", "बरं का", "मस्त दाखवला त्यांनी आजचा एपिसोड").
4. STRICTLY WRITE IN MARATHI. DO NOT use English except for common words.
5. NO SKIPPING & NO TIMESTAMPS: Do NOT jump ahead or skip parts. Do NOT write timestamps like `[18:44]`. Cover EVERYTHING sequentially.
6. GENDER-NEUTRAL PERSONA: You are a confident and engaging storyteller. Address the audience in a purely neutral, professional yet dramatic way (e.g., "प्रेक्षकांनो", "मंडळी", "बघा ना"). Do NOT use gender-specific words like "मित्रांनो" (male) or "मैत्रिणींनो" (female).
7. ENGLISH LOANWORDS RULE:
- If an English word contains a strong 'D' sound (e.g., Episode, Video, Accident, Record, Condition, DNA), write it in the ENGLISH ALPHABET.
- CRITICAL: Do NOT write any other English words in the English alphabet! Words without a strong 'D' sound (like Phone, Range, Plan, Report, Spot, Police, Time) MUST be written in Marathi script (फोन, रेंज, प्लॅन, रिपोर्ट, स्पॉट, पोलीस, टाईम).
- DO NOT alter natural Marathi words! Use completely natural, everyday Marathi (Bolbhasha). Letters like ळ, ड, ढ are perfectly fine for Marathi words. Never replace natural words with bookish synonyms.
9. IGNORE EXAMPLE'S WEAK HOOK: The example text below has a weak, slow opening. DO NOT COPY ITS OPENING! You MUST use the high-energy Derral Eves hook described above.
10. DO NOT END THE SCRIPT. Stop naturally when you reach the end of this transcript chunk.

EXAMPLE YOUTUBE NARRATION STYLE (Follow this exactly!):
{youtube_example_text}

Requirements:
- Conversational, energetic narration. Talk directly to viewers.
- Tone: Passionate, emotional, engaging, and dramatic.
"""

V2_SCRIPT_PROMPT_PART_MIDDLE = """You are an experienced YouTube TV serial review creator.
Here is the NEXT PART of the transcript:
{tagged_transcript}

CONTINUE the YouTube narration script seamlessly from where you left off.
Structure:
[SCENE BY SCENE EXPLANATION WITH REACTIONS] - Continue explaining the episode play-by-play.

CRITICAL RULES:
1. NARRATE LIKE A STORYTELLER: Blend the actions and dialogues into a continuous, engaging paragraph.
2. DO NOT MISS ANY DIALOGUES: You MUST cover all the dialogues provided, but weave them naturally and EXPLAIN them.
3. ADD YOUR REACTIONS: Add personal reactions and casual words (e.g., "बापरे हे सगळं भयंकर आहे", "बरं का").
4. RESPECT THE TAGS: If an ACTION or DIALOGUE is tagged with a character name, ALWAYS use that exact character name in your script, even if the action description text accidentally says a different name!
5. STRICTLY WRITE IN MARATHI. DO NOT use English except for common words.
6. NO SKIPPING & NO TIMESTAMPS: Do NOT jump ahead or skip parts. Do NOT write timestamps like `[18:44]`. Cover EVERYTHING sequentially.
6. GENDER-NEUTRAL PERSONA: You are a confident and engaging storyteller. Address the audience in a purely neutral, professional yet dramatic way (e.g., "प्रेक्षकांनो", "मंडळी", "बघा ना"). Do NOT use gender-specific words like "मित्रांनो" (male) or "मैत्रिणींनो" (female).
7. ENGLISH LOANWORDS RULE:
- If an English word contains a strong 'D' sound (e.g., Episode, Video, Accident, Record, Condition, DNA), write it in the ENGLISH ALPHABET.
- CRITICAL: Do NOT write any other English words in the English alphabet! Words without a strong 'D' sound (like Phone, Range, Plan, Report, Spot, Police, Time) MUST be written in Marathi script (फोन, रेंज, प्लॅन, रिपोर्ट, स्पॉट, पोलीस, टाईम).
- DO NOT alter natural Marathi words! Use completely natural, everyday Marathi (Bolbhasha). Letters like ळ, ड, ढ are perfectly fine for Marathi words. Never replace natural words with bookish synonyms.
9. DO NOT WRITE AN INTRO OR OUTRO. Just continue the story.
10. DO NOT END THE SCRIPT. Stop naturally when you reach the end of this chunk.
"""

V2_SCRIPT_PROMPT_PART_FINAL = """You are an experienced YouTube TV serial review creator.
Here is the FINAL PART of the transcript:
{tagged_transcript}

FINISH the YouTube narration script.
Structure:
[SCENE BY SCENE EXPLANATION WITH REACTIONS] - Explain the final scenes play-by-play.
[CLIFFHANGER] - How it ended.
[CALL TO ACTION] - Subscribe and comment.

CRITICAL RULES:
1. NARRATE LIKE A STORYTELLER: Blend the actions and dialogues into a continuous, engaging paragraph.
2. DO NOT MISS ANY DIALOGUES: You MUST cover all the dialogues provided, but weave them naturally and EXPLAIN them.
3. ADD YOUR REACTIONS: Add personal reactions and casual words (e.g., "बापरे हे सगळं भयंकर आहे", "बरं का").
4. RESPECT THE TAGS: If an ACTION or DIALOGUE is tagged with a character name, ALWAYS use that exact character name in your script, even if the action description text accidentally says a different name!
5. STRICTLY WRITE IN MARATHI. DO NOT use English except for common words.
6. NO SKIPPING & NO TIMESTAMPS: Do NOT jump ahead or skip parts. Do NOT write timestamps like `[18:44]`. Cover EVERYTHING sequentially.
6. GENDER-NEUTRAL PERSONA: You are a confident and engaging storyteller. Address the audience in a purely neutral, professional yet dramatic way (e.g., "प्रेक्षकांनो", "मंडळी", "बघा ना"). Do NOT use gender-specific words like "मित्रांनो" (male) or "मैत्रिणींनो" (female).
7. ENGLISH LOANWORDS RULE:
- If an English word contains a strong 'D' sound (e.g., Episode, Video, Accident, Record, Condition, DNA), write it in the ENGLISH ALPHABET.
- CRITICAL: Do NOT write any other English words in the English alphabet! Words without a strong 'D' sound (like Phone, Range, Plan, Report, Spot, Police, Time) MUST be written in Marathi script (फोन, रेंज, प्लॅन, रिपोर्ट, स्पॉट, पोलीस, टाईम).
- DO NOT alter natural Marathi words! Use completely natural, everyday Marathi (Bolbhasha). Letters like ळ, ड, ढ are perfectly fine for Marathi words. Never replace natural words with bookish synonyms.
9. Finish the story and write a strong cliffhanger!
"""

import os
def generate_timestamp_transcript(
    video_file,
    serial_name: str,
    model_name: str = "gemini-1.5-pro",
    progress_callback: Optional[Callable[[str], None]] = None
) -> list:
    if progress_callback:
        progress_callback("Extracting detailed transcript from video...")
        
    # Inject known characters
    known_chars_str = ""
    try:
        from v2_main_gui import SHOWS_DIR
        char_file = os.path.join(SHOWS_DIR, serial_name, "characters.json")
        if os.path.exists(char_file):
            with open(char_file, "r", encoding="utf-8") as f:
                chars = json.load(f)
                if chars:
                    known_chars_str = ", ".join(chars)
    except Exception as e:
        print(f"Failed to load characters for prompt: {e}")
        
    base_prompt = V2_TRANSCRIPT_PROMPT.replace("{known_characters}", known_chars_str)
    current_prompt = base_prompt
    model = gemini_client.get_model_by_name(model_name)
    
    parsed_data = []
    max_loops = 5
    
    for loop_idx in range(max_loops):
        if progress_callback:
            progress_callback(f"Extracting transcript part {loop_idx + 1}...")
            
        response_text = gemini_client.generate_with_retry(
            model=model,
            prompt=current_prompt,
            video_file=video_file,
            max_retries=3,
            progress_callback=progress_callback,
            temperature=0.0
        )
        
        lines = response_text.strip().split('\n')
        end_found = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "[END_OF_VIDEO]" in line:
                end_found = True
                continue
                
            # Parse format: [MM:SS] TYPE || Speaker || Context || Text
            if line.startswith('[') and ']' in line and '||' in line:
                try:
                    timestamp_end = line.find(']')
                    timestamp = line[1:timestamp_end]
                    rest = line[timestamp_end+1:].strip()
                    parts = [p.strip() for p in rest.split('||')]
                    
                    if len(parts) >= 3:
                        item_type = parts[0].lower() # action or dialogue
                        
                        if item_type == "action":
                            parsed_data.append({
                                "timestamp": timestamp,
                                "type": "action",
                                "speaker": "",
                                "context": parts[1] if parts[1].lower() != "none" else "",
                                "text": parts[2]
                            })
                        else:
                            parsed_data.append({
                                "timestamp": timestamp,
                                "type": "dialogue",
                                "speaker": parts[1] if parts[1].lower() != "none" else "",
                                "context": parts[2] if len(parts) > 3 else "",
                                "text": parts[3] if len(parts) > 3 else parts[2]
                            })
                except Exception as e:
                    print(f"Failed to parse line: {line} - {e}")
                    
        if end_found or not parsed_data:
            break
            
        # If we didn't find END_OF_VIDEO, it means output was truncated.
        last_ts = parsed_data[-1]['timestamp']
        current_prompt = f"CONTINUE EXTRACTING FROM WHERE YOU LEFT OFF. The last extracted timestamp was [{last_ts}]. Do NOT repeat anything before [{last_ts}]. Keep extracting until the end of the video, and strictly print [END_OF_VIDEO] when done.\n\n{base_prompt}"
        
    if progress_callback:
        progress_callback(f"Successfully extracted {len(parsed_data)} frames/dialogues.")
        
    return parsed_data

def generate_final_script(
    tagged_transcript: list,
    model_name: str = "gemini-2.5-flash",
    progress_callback: Optional[Callable[[str], None]] = None
) -> str:
    if progress_callback:
        progress_callback("Chunking transcript and generating final YouTube Script...")
        
    chunk_size = 60
    chunks = [tagged_transcript[i:i + chunk_size] for i in range(0, len(tagged_transcript), chunk_size)]
    
    final_script = ""
    model = gemini_client.get_model_by_name(model_name)
    
    for idx, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(f"Writing script part {idx + 1} of {len(chunks)}...")
            
        transcript_text = ""
        for item in chunk:
            ts = item.get("timestamp", "")
            typ = item.get("type", "")
            spk = item.get("speaker", "")
            txt = item.get("text", "")
            ctx = item.get("context", "")
            
            if typ == "dialogue":
                transcript_text += f"[{ts}] {spk} ({ctx}): {txt}\n"
            else:
                if spk:
                    transcript_text += f"[{ts}] ACTION (Character: {spk}) ({ctx}): {txt}\n"
                else:
                    transcript_text += f"[{ts}] ACTION ({ctx}): {txt}\n"
                
        if idx == 0:
            try:
                with open(os.path.join(os.path.dirname(__file__), "youtube_example.txt"), "r", encoding="utf-8") as f:
                    example_text = f.read()
            except Exception:
                example_text = "मंडळी ठरलं तर मग या मालिकेचा आजचा एपिसोड..."
            prompt = V2_SCRIPT_PROMPT_PART_1.replace("{tagged_transcript}", transcript_text).replace("{youtube_example_text}", example_text)
        elif idx == len(chunks) - 1:
            prompt = V2_SCRIPT_PROMPT_PART_FINAL.replace("{tagged_transcript}", transcript_text)
        else:
            prompt = V2_SCRIPT_PROMPT_PART_MIDDLE.replace("{tagged_transcript}", transcript_text)
            
        part_script = gemini_client.generate_with_retry(
            model=model,
            prompt=prompt,
            max_retries=3,
            progress_callback=progress_callback,
            temperature=0.7
        )
        
        final_script += part_script + "\n\n"
        
    if progress_callback:
        progress_callback("Script generation complete!")
        
    return final_script


def calculate_frame_durations(
    audio_file,
    script_text: str,
    frames_list: list,
    model_name: str = "gemini-1.5-pro",
    progress_callback: Optional[Callable[[str], None]] = None
) -> dict:
    if progress_callback:
        progress_callback("Analyzing audio with Gemini to sync frames...")
        
    prompt = f"""You are an expert video editor AI.
    
I have a voiceover audio file, a script, and a chronological list of video frames.
Your job is to align the video frames with the pacing of the audio.

### The Script:
{script_text}

### The Chronological Frames:
{json.dumps(frames_list, indent=2)}

### Task:
Listen to the audio. Figure out how many seconds each frame should remain on screen to match what is being spoken in the script.
Output MUST be a valid JSON dictionary where the keys are the EXACT frame filenames provided, and the values are the duration in seconds (float) that the frame should be shown.
Ensure that the sum of all durations approximately matches the total duration of the audio.
Do not output anything else but the raw JSON object.
"""

    model = gemini_client.get_model_by_name(model_name)
    response_text = gemini_client.generate_with_retry(
        model=model,
        prompt=prompt,
        video_file=audio_file,
        max_retries=3,
        progress_callback=progress_callback,
        temperature=0.2
    )
    
    return gemini_client.parse_json_response(response_text)

def generate_thumbnail_prompt(script_text: str, style: str = "1", model_name: str = "gemini-1.5-pro", progress_callback=None) -> str:
    if progress_callback:
        progress_callback(f"Analyzing script to create Prompt (Style {style})...")
        
    import datetime
    today_str = datetime.datetime.now().strftime("%d %B") # e.g., 27 June
    
    style_instruction = ""
    if style == "1":
        style_instruction = f"""
**The Classic 4-Grid Collage** (Safe & Clean)
"I am attaching 4 images from a Marathi TV serial. Create a 16:9 YouTube thumbnail. Place the 4 images in a clean 2x2 grid. Do not alter the faces.
Layout rules:
1. Top Banner: Thick black banner with bright yellow text saying: [YOUR TOP BANNER TEXT IN MARATHI]
2. Bottom Banner: Thick blue banner with white text saying: [YOUR BOTTOM BANNER TEXT IN MARATHI]
3. Add a large blue circular badge in the top right corner saying: {today_str}
4. For Image 1 (Top Left): Add a white speech bubble pointing to [CHARACTER NAME 1] saying: [DIALOGUE 1 IN MARATHI]
5. For Image 2 (Top Right): Add a white speech bubble pointing to [CHARACTER NAME 2] saying: [DIALOGUE 2 IN MARATHI]
6. For Image 3 (Bottom Left): Add a white speech bubble pointing to [CHARACTER NAME 3] saying: [DIALOGUE 3 IN MARATHI]
7. For Image 4 (Bottom Right): Add a white speech bubble pointing to [CHARACTER NAME 4] saying: [DIALOGUE 4 IN MARATHI]
8. Add 2-3 shocked (😱) and angry (😡) emojis around the collage."
"""
    elif style == "2":
        style_instruction = f"""
**The Dynamic Movie Poster** (High Energy, Overlapping)
"I am attaching 4 images from a Marathi TV serial. Create a 16:9 YouTube thumbnail. DO NOT use a grid. Use the widest/action scene as the background. Extract the faces from the other 3 images and SUPERIMPOSE (overlap) them dynamically over the background like a chaotic movie poster.
Layout rules:
1. Top Banner: Thick black banner with bright yellow text saying: [YOUR TOP BANNER TEXT IN MARATHI]
2. Bottom Banner: Thick blue banner with white text saying: [YOUR BOTTOM BANNER TEXT IN MARATHI]
3. Add a red 'Breaking News' style sub-banner under the top one saying: "जबरदस्त भाग 😱"
4. Add a large blue circular badge in the top right corner saying: {today_str}
5. Add comic-style 'BOOM!' graphics.
6. Add 4 distinct white speech bubbles pointing to 4 DIFFERENT characters with short aggressive Marathi dialogues: [DIALOGUE 1], [DIALOGUE 2], [DIALOGUE 3], and [DIALOGUE 4]."
"""
    else:
        style_instruction = f"""
**The 3-Panel Split** (Storytelling Layout)
"I am attaching 4 images from a Marathi TV serial. Create a 16:9 YouTube thumbnail. Split the screen into 3 vertical panels. 
Left panel: Close up of [CHARACTER NAME 1]. 
Right panel: Close up of [CHARACTER NAME 2]. 
Middle panel: The wide action scene, but add small cutouts of [CHARACTER NAME 3] and [CHARACTER NAME 4] at the bottom of the middle panel.
Layout rules:
1. Top Banner: Thick black banner with bright yellow text saying: [YOUR TOP BANNER TEXT IN MARATHI]
2. Bottom Banner: Thick blue banner with white text saying: [YOUR BOTTOM BANNER TEXT IN MARATHI]
3. Add a large blue circular badge in the top right corner saying: {today_str}
4. Add 4 distinct speech bubbles (one for each of the 4 characters) with short aggressive Marathi dialogues: [DIALOGUE 1], [DIALOGUE 2], [DIALOGUE 3], and [DIALOGUE 4]."
"""

    prompt = f"""You are a master YouTube thumbnail strategist for Marathi TV serials.
I will give you the narration script of today's episode.

Your job is to read it, find the most dramatic scenes, and generate ONE PERFECT ChatGPT (DALL-E) Prompt based on the specific layout style I request.

CRITICAL RULE (DERRAL EVES SMART CLICKBAIT): Pour your creative energy into making the Marathi text and dialogues extremely clickbaity using the "Curiosity Gap" and "Open Loop" strategy. 
Instead of revealing the full spoiler, ask a shocking question or make a dramatic incomplete statement (e.g., instead of "Priya is pregnant", write "प्रियाचा सर्वात मोठा डाव! 😱" or "आता अर्जुन काय करणार?"). 
Base the drama STRICTLY on the actual events in the script. You may exaggerate the tension, but DO NOT invent completely fake storylines. The clickbait must be believable, highly emotional (shock, anger, crying), and force the viewer to click immediately!

### Episode Script:
{script_text}

### INSTRUCTIONS:
Create the prompt using THIS EXACT format (fill in the bracketed parts with your highly engaging Marathi text):

--------------------------------------------------
Here is your prompt for ChatGPT:

{style_instruction}
--------------------------------------------------
"""
    model = gemini_client.get_model_by_name(model_name)
    response_text = gemini_client.generate_with_retry(
        model=model,
        prompt=prompt,
        max_retries=3,
        progress_callback=progress_callback,
        temperature=0.7
    )
    
    return response_text