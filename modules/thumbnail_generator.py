from PIL import Image, ImageDraw, ImageFont
import os
import urllib.request

def draw_speech_bubble(draw, x, y, width, height, text, font):
    # PIL doesn't have an easy speech bubble, so we draw a rounded rectangle and a polygon tail
    # Draw bubble background
    draw.rounded_rectangle((x, y, x + width, y + height), radius=20, fill="white", outline="black", width=4)
    
    # Draw tail
    tail_coords = [
        (x + width/2 - 10, y + height - 2),
        (x + width/2 + 20, y + height + 30),
        (x + width/2 + 10, y + height - 2)
    ]
    draw.polygon(tail_coords, fill="white", outline="black")
    
    # Draw text (centered)
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    text_x = x + (width - text_w) / 2
    text_y = y + (height - text_h) / 2 - 10 # Adjust slightly for baseline
    
    draw.text((text_x, text_y), text, font=font, fill="black")

def generate_thumbnail(image_paths, top_text, bottom_text, dialogues, date_text, out_path):
    width, height = 1920, 1080
    
    # Create empty canvas
    canvas = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(canvas)
    
    # Download font if not present
    font_path = os.path.join(os.path.dirname(__file__), "OpenSans-Bold.ttf")
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve("https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Bold.ttf", font_path)
        except:
            font_path = "arial.ttf"
            
    try:
        bubble_font = ImageFont.truetype(font_path, 40)
        top_font = ImageFont.truetype(font_path, 65)
        bot_font = ImageFont.truetype(font_path, 65)
        date_font = ImageFont.truetype(font_path, 70)
    except IOError:
        bubble_font = top_font = bot_font = date_font = ImageFont.load_default()

    positions = [
        (0, 0), (960, 0),
        (0, 540), (960, 540)
    ]
    
    # Draw images
    for i in range(4):
        if i < len(image_paths) and os.path.exists(image_paths[i]):
            try:
                img = Image.open(image_paths[i])
                # Resize and crop to 960x540
                img_ratio = img.width / img.height
                target_ratio = 960 / 540
                
                if img_ratio > target_ratio:
                    new_w = int(img.height * target_ratio)
                    offset = (img.width - new_w) // 2
                    img = img.crop((offset, 0, offset + new_w, img.height))
                else:
                    new_h = int(img.width / target_ratio)
                    offset = (img.height - new_h) // 2
                    img = img.crop((0, offset, img.width, offset + new_h))
                    
                img = img.resize((960, 540), Image.LANCZOS)
                canvas.paste(img, positions[i])
            except Exception as e:
                print(f"Error processing image {image_paths[i]}: {e}")
                
    # Draw Speech Bubbles
    bubble_w, bubble_h = 350, 150
    bubble_positions = [
        (300, 350),  (1260, 350),
        (300, 890),  (1260, 890) 
    ]
    
    for i in range(4):
        if i < len(dialogues) and dialogues[i].strip():
            bx, by = bubble_positions[i]
            draw_speech_bubble(draw, bx, by, bubble_w, bubble_h, dialogues[i], bubble_font)
            
    # Draw Top Banner (Black)
    draw.rectangle((0, 0, 1920, 120), fill="black")
    draw.text((40, 20), top_text, font=top_font, fill="yellow")
    
    # Draw Bottom Banner (Blue)
    draw.rectangle((0, 960, 1920, 1080), fill="#0d6efd")
    
    # Center bottom text
    bot_bbox = draw.textbbox((0, 0), bottom_text, font=bot_font)
    bot_w = bot_bbox[2] - bot_bbox[0]
    draw.text(((1920 - bot_w) / 2, 980), bottom_text, font=bot_font, fill="white")
    
    # Draw Date Badge (Blue Circle Top Right)
    if date_text:
        draw.ellipse((1600, 20, 1880, 300), fill="#0d6efd", outline="white", width=5)
        date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
        date_w = date_bbox[2] - date_bbox[0]
        date_h = date_bbox[3] - date_bbox[1]
        draw.text((1600 + (280 - date_w)/2, 20 + (280 - date_h)/2 - 10), date_text, font=date_font, fill="white")
        
    canvas.save(out_path, "JPEG", quality=95)
    return out_path