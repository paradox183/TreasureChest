import re
import pdfplumber
from datetime import datetime


def parse_bad_session_report(pdf_path):
    events = []
    meet_title = "Unknown Meet"

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.splitlines()

            # Extract meet title
            for line in lines:
                if "Session Report" in line and "Page" in line:
                    match = re.search(r"Session Report (.*?) Page", line)
                    if match:
                        meet_title = match.group(1).strip()

            for line in lines:
                # Skip lines that don't look like events
                if not re.match(r"^\d+\s+(Boys|Girls|Men|Women)\s", line):
                    continue

                # Split on whitespace but preserve stroke name
                parts = line.strip().split()
                if len(parts) < 8:
                    continue  # skip malformed lines

                # Extract fields
                event_number = int(parts[0])
                gender = parts[1]
                age_group_parts = []
                i = 2
                # Capture age group until we find the yard/meter indicator
                while not re.match(r"\d+(yd|m)", parts[i]):
                    age_group_parts.append(parts[i])
                    i += 1
                age_group = " ".join(age_group_parts)

                distance = re.match(r"(\d+)(yd|m)", parts[i]).group(0)
                i += 1
                stroke_parts = []
                # Capture stroke name until we reach numbers (Entries, Heats, Time)
                while i < len(parts) and not parts[i].isdigit():
                    stroke_parts.append(parts[i])
                    i += 1
                stroke = " ".join(stroke_parts)

                try:
                    entries = int(parts[i])
                    heats = int(parts[i + 1])
                    start_time = parts[i + 2]
                except (IndexError, ValueError):
                    continue  # malformed row

                events.append({
                    "Event #": event_number,
                    "Gender": gender,
                    "Age": age_group,
                    "Distance": distance,
                    "Stroke": stroke,
                    "Entries": entries,
                    "Heats": heats,
                    "Start": start_time,
                })

    return events, meet_title