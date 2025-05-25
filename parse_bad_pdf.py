import re
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
import unicodedata
import uuid
from datetime import datetime


def extract_events_from_microsoft_pdf(pdf_path):
    print ("Running OCR parser for MS PDF")
    events = []
    meet_title = "Unknown Meet"

    # Convert each page of the PDF into an image
    try:
        images = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return [], "Error reading PDF"

    output_images = []
    output_dir = Path("static/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    images = convert_from_path(pdf_path, dpi=300)

    for i, image in enumerate(images):
        image_id = uuid.uuid4().hex[:8]
        filename = f"ocr_page_{i+1}_{image_id}.png"
        image_path = output_dir / filename
        image.save(image_path)
        output_images.append(str(image_path))

    return [], "Unknown Meet Title", output_images

    full_text = ""
    for image in images:
        text = pytesseract.image_to_string(image)
        full_text += text + "\n"

    # Attempt to extract meet title
    title_match = re.search(r"Session Report\s+(.+?)\s+Page", full_text, re.DOTALL)
    if title_match:
        meet_title = title_match.group(1).strip()

    # Define a regex pattern to match event headers
    event_pattern = re.compile(
        r"Event\s+(\d+)\s+((Mixed|Girls|Boys|Women|Men)\s+(\d+[-–]\d+|\d+)\s+(.+?))\s+Heat",
        re.IGNORECASE
    )

    lines = full_text.splitlines()
    seen = set()

    for line in lines:
        match = event_pattern.search(line)
        if match:
            event_number = int(match.group(1))
            gender = match.group(3).capitalize()
            age_group = match.group(4)
            stroke = match.group(5).strip()

            key = (event_number, gender, age_group, stroke)
            if key not in seen:
                seen.add(key)
                events.append({
                    "Event #": event_number,
                    "Gender": gender,
                    "Age Group": age_group,
                    "Distance": None,  # Distance parsing optional
                    "Stroke": stroke,
                    "Heats": []  # Optional: can be ignored if not extracting swimmers
                })

    print(f"📄 Parsed {len(events)} events from Microsoft PDF")
    return events, meet_title

def sanitize_for_pdf(text: str) -> str:
    # Replace known problematic characters
    replacements = {
        "—": "-",       # em-dash to hyphen
        "–": "-",       # en-dash to hyphen
        "™": "",        # remove trademark symbol
        "“": '"',       # curly quotes to straight
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",     # ellipsis
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Normalize and remove any remaining non-Latin-1 characters
    return unicodedata.normalize("NFKD", text).encode("latin-1", "ignore").decode("latin-1")