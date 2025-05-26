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
            text = pytesseract.image_to_string(gray)

            # Extract meet title if found
            if "Session Report" in text:
                match = re.search(r"Session Report\s+(.*?)\s+Page", text, re.DOTALL)
                if match:
                    meet_title = match.group(1).strip()

            # Look for event blocks
            current_event = None
            for line in text.split("\n"):
                line = line.strip()

                if not line:
                    continue

                # Sanitize to remove unsupported characters
                line = sanitize_for_pdf(line)

                event_match = re.match(r"^Event\s+(\d+)\s+(Girls|Boys|Mixed)\s+(\d+)-?(\d+)?\s+(.+)$", line)
                if event_match:
                    current_event = {
                        "Event ID": int(event_match.group(1)),
                        "Gender": event_match.group(2),
                        "Age Group": event_match.group(3) + ("-" + event_match.group(4) if event_match.group(4) else ""),
                        "Distance": "",
                        "Stroke": event_match.group(5).strip(),
                        "Heats": []
                    }
                    events.append(current_event)

                elif current_event:
                    heat_match = re.search(r"Heat\s+(\d+)", line)
                    if heat_match:
                        current_event["Heats"].append(int(heat_match.group(1)))

    return events, meet_title, image_paths


def sanitize_for_pdf(text):
    return text.replace("—", "-").replace("™", "")