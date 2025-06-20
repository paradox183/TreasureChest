
import re
import os
import pytesseract
from pdf2image import convert_from_path
from tempfile import TemporaryDirectory
from PIL import Image, ImageOps
from pathlib import Path


def sanitize_for_pdf(text):
    return text.replace("™", "").replace("—", "-").encode("latin-1", "ignore").decode("latin-1")


def extract_events_from_microsoft_pdf(pdf_path):
    events = []
    meet_title = "Unknown Meet"
    image_paths = []

    with TemporaryDirectory() as temp_dir:
        images = convert_from_path(pdf_path, dpi=300, output_folder=temp_dir, fmt="png")

        for i, image in enumerate(images):
            image_filename = os.path.join("static/generated", f"debug_page_{i+1}.png")
            image.save(image_filename, "PNG")
            image_paths.append(image_filename)

            gray = ImageOps.grayscale(Image.open(image_filename))
            text = pytesseract.image_to_string(gray, config="--psm 6")

            print(f"\n--- OCR TEXT FROM {image_filename} ---\n{text}\n")

            event_pattern = re.compile(
                r"^(\d+)\s+"                             # Event number
                r"(Mixed|Girls|Boys|Women|Men)\s+"       # Gender
                r"([\d&\s\-Uunder]+)\s+"                 # Age group (e.g. 6 & Under, 9-10, etc.)
                r"(\d{2,4}yd)\s+"                        # Distance (e.g. 100yd)
                r"([\w\s]+?)\s+"                         # Stroke (e.g. Freestyle Relay)
                r"(\d+)\s+"                              # Entries
                r"(\d+)\s+"                              # Heats
                r"\d{1,2}:\d{2}\s*(AM|PM)?"              # Time (optional match, ignored)
            )

            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Try to extract meet title if not already found
                if line.startswith("Session Report") and "Page" in line:
                    try:
                        parts = line.split("Page")[0]  # Get everything before "Page"
                        title_part = parts.replace("Session Report", "").strip()
                        meet_title = sanitize_for_pdf(title_part)
                    except Exception as e:
                        print(f"Failed to extract title from: {line}")

                if meet_title == "Unknown Meet":
                    continue

                match = event_pattern.match(line)
                if match:
                    event_number = match.group(1)
                    gender = match.group(2)
                    age_group = match.group(3).strip()
                    distance = match.group(4)
                    stroke = match.group(5)
                    entries = int(match.group(6))
                    heats = int(match.group(7))

                    #desc_match = re.match(r"^(\d+)\s+(Mixed|Girls|Boys|Women|Men)\s+(.+)\s+(\d+)\s+(\d+)\s+\d{1,2}:\d{2}", description, re.IGNORECASE)
                    #if not desc_match:
                    #    print(f"Could not parse title: '{description}'")
                    #    continue

                    #gender = desc_match.group(1).capitalize()
                    #age_group = desc_match.group(2)
                    #distance = desc_match.group(3)
                    #stroke = desc_match.group(4).strip()

                    events.append({
                        "Event #": event_number,
                        "Gender": gender,
                        "Age Group": age_group,
                        "Distance": distance,
                        "Stroke": stroke,
                        "Entries": entries,
                        "Heats": heats,
                    })

    return events, meet_title, image_paths
