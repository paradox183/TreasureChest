import re
import os
import pytesseract
from pdf2image import convert_from_path
from tempfile import TemporaryDirectory
from PIL import Image, ImageOps
from pathlib import Path


def extract_events_from_microsoft_pdf(pdf_path):
    events = []
    meet_title = "Unknown Meet"
    image_paths = []

    # Use pdf2image to convert PDF pages to images
    with TemporaryDirectory() as temp_dir:
        images = convert_from_path(pdf_path, dpi=300, output_folder=temp_dir, fmt="png")

        for i, image in enumerate(images):
            image_filename = os.path.join("static/generated", f"debug_page_{i+1}.png")
            image.save(image_filename, "PNG")
            image_paths.append(image_filename)

            # Convert image to grayscale for better OCR results
            image_pil = Image.open(image_filename)
            gray = ImageOps.grayscale(image_pil)
            text = pytesseract.image_to_string(gray, config="--psm 6")

            print(f"\n--- OCR TEXT FROM {image_filename} ---\n{text}\n")

            # Extract meet title if found
            if "Session Report" in text:
                match = re.search(r"Session Report\s+(.*?)\s+Page", text, re.DOTALL)
                if match:
                    meet_title = sanitize_for_pdf(match.group(1).strip())

            # Match valid event rows (skip breaks and malformed lines)
            event_pattern = re.compile(r"^(\d+)\s+(.+?)\s+(\d+)\s+(\d+)\s+\d{1,2}:\d{2}\s+[AP]M", re.IGNORECASE)

            # Look for event blocks
            current_event = None
            for line in text.splitlines():
                if not line:
                    continue

                if meet_title == "Unknown Meet" and re.search(r"20\d{2}", line):
                    meet_title = line
                    continue

                if meet_title != "Unknown Meet":
                    match = re.match(r"^(\d+)\s+(.+?)\s+(\d+)\s+(\d+)\s+\d{1,2}:\d{2}\s+[AP]M", line, re.IGNORECASE)
                    if match:
                        try:
                            event_id = int(match.group(1))
                            title = match.group(2).strip()
                            entries = int(match.group(3))
                            heats = int(match.group(4))

                            parsed = parse_event_title(title)
                            if not parsed:
                                continue

                            gender, age_group, distance, stroke = parsed
                            events.append({
                                "Event #": event_id,
                                "Gender": gender,
                                "Age Group": age_group,
                                "Distance": distance,
                                "Stroke": stroke,
                                "Entries": entries,
                                "Heats": heats,
                            })
                        except ValueError:
                            continue

                    events.append(current_event)

                elif current_event:
                    heat_match = re.search(r"Heat\s+(\d+)", line)
                    if heat_match:
                        current_event["Heats"].append(int(heat_match.group(1)))

    return events, meet_title, image_paths


def sanitize_for_pdf(text):
    return text.replace("—", "-").replace("™", "")

def parse_event_title(title):
    title = title.lower()
    title = title.replace("&", "and")

    gender_match = re.match(r"(mixed|girls|boys|women|men)\s+", title)
    if not gender_match:
        return None
    gender = gender_match.group(1).capitalize()
    remainder = title[gender_match.end():]

    age_match = re.match(r"(\d+\s*and\s*under|\d+\s*-\s*\d+|\d+)", remainder)
    if not age_match:
        return None
    age_group = age_match.group(1).replace(" ", "")
    remainder = remainder[age_match.end():].strip()

    distance_match = re.match(r"(\d+)(yd|meter|m)\s+", remainder)
    if not distance_match:
        return None
    distance = f"{distance_match.group(1)}yd"
    stroke = remainder[distance_match.end():].strip().capitalize()

    return gender, age_group, distance, stroke