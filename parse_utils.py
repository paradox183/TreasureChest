
import pdfplumber
import unicodedata
import pandas as pd
import re
import os
import pytesseract
from pdf2image import convert_from_path
from tempfile import TemporaryDirectory
from PIL import Image, ImageOps
from datetime import datetime
from zoneinfo import ZoneInfo
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from weasyprint import HTML

from parse_bad_pdf import sanitize_for_pdf


def extract_events_from_pdf(pdf_path):
    events = []
    meet_title = "Meet Title"

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            lines = page.extract_text().split('\n')

            for line_num, line in enumerate(lines):
                if "Session Report" in line and "Page" in line:
                    try:
                        start = line.index("Session Report") + len("Session Report")
                        end = line.index("Page")
                        meet_title = line[start:end].strip(" —-")
                        meet_title = meet_title.replace("—", "-")
                    except:
                        pass

                match = re.match(r'^(\d+)\s+(Mixed|Girls|Boys|Women|Men)\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d{1,2}:\d{2}\s*[AP]M)$', line.strip())
                if not match:
                    continue

                number = int(match.group(1))
                gender = match.group(2)
                rest = match.group(3).strip()
                entries = int(match.group(4))
                heats = int(match.group(5))

                if rest.startswith("6"):
                    age_group = rest[:9]
                    remainder = rest[9:]
                elif rest.startswith("7"):
                    age_group = rest[:3]
                    remainder = rest[3:]
                elif rest.startswith("9"):
                    age_group = rest[:4]
                    remainder = rest[4:]
                elif rest.startswith("1"):
                    age_group = rest[:5]
                    remainder = rest[5:]
                else:
                    continue

                distance_match = re.match(r'^(\d{2,3}yd)(.+)$', remainder)
                if not distance_match:
                    continue

                distance = distance_match.group(1)
                stroke = distance_match.group(2).strip()

                events.append({
                    "Event #": number,
                    "Gender": gender,
                    "Age Group": age_group,
                    "Distance": distance,
                    "Stroke": stroke,
                    "Entries": entries,
                    "Heats": heats
                })

    if not events:
        events, meet_title = extract_events_from_bad_pdf(pdf_path)
    if not events:
        events, meet_title = extract_events_from_microsoft_pdf(pdf_path)


    return events, meet_title

def find_combinable_pairs(events, lanes=6, aggressiveness=1):
    pairs = []
    for i, e1 in enumerate(events):
        if e1["Gender"] not in ("Girls", "Women") or e1["Entries"] < 1:
            continue

        for e2 in events[i + 1:]:
            if e2["Gender"] not in ("Boys", "Men") or e2["Entries"] < 1:
                continue

            if (
                e1["Age Group"] == e2["Age Group"]
                and e1["Distance"] == e2["Distance"]
                and e1["Stroke"] == e2["Stroke"]
            ):
                r1 = e1["Entries"] % lanes
                r2 = e2["Entries"] % lanes

                if r1 == 0 or r2 == 0:
                    continue
                if r1 + r2 > lanes:
                    continue
                if r1 < aggressiveness or r2 < aggressiveness:
                    continue

                pairs.append({
                    "Female Event #": e1["Event #"],
                    "Female Age": f"{e1['Gender']} {e1['Age Group']}",
                    "Female Heat #": e1["Heats"],
                    "Female # Swimmers": r1,
                    "combine with": "combine with",
                    "Male Event #": e2["Event #"],
                    "Male Age": f"{e2['Gender']} {e2['Age Group']}",
                    "Male Heat #": 1,
                    "Male # Swimmers": r2,
                    "Distance": e1["Distance"],
                    "Stroke": e1["Stroke"]
                })

    return pairs

def evaluate_all_events(events, lanes, aggressiveness):
    result = []
    used_male_ids = set()

    for i, e1 in enumerate(events):
        if e1["Gender"] in ("Boys", "Men") and e1["Event #"] in used_male_ids:
            continue  # already paired and added

        row = e1.copy()

        # Only female events initiate a combo
        if e1["Gender"] not in ("Girls", "Women"):
            row["Can Combine?"] = ""
            row["Reason"] = ""
            result.append(row)
            continue

        matching = next(
            (e2 for e2 in events[i + 1:]
             if e2["Gender"] in ("Boys", "Men")
             and e2["Age Group"] == e1["Age Group"]
             and e2["Distance"] == e1["Distance"]
             and e2["Stroke"] == e1["Stroke"]
             and e2["Event #"] not in used_male_ids),
            None
        )

        if not matching:
            row["Can Combine?"] = "No"
            row["Reason"] = "No male counterpart"
            result.append(row)
            continue

        r1 = e1["Entries"] % lanes
        r2 = matching["Entries"] % lanes

        if e1["Entries"] < 1 or matching["Entries"] < 1:
            row["Can Combine?"] = "No"
            row["Reason"] = "One event has 0 entries"
        elif r1 == 0 or r2 == 0:
            row["Can Combine?"] = "No"
            row["Reason"] = "One event fills all lanes"
        elif r1 + r2 > lanes:
            row["Can Combine?"] = "No"
            row["Reason"] = "Too many remainder swimmers"
        elif r1 < aggressiveness or r2 < aggressiveness:
            row["Can Combine?"] = "No"
            row["Reason"] = "Combo strategy too conservative"
        else:
            row["Can Combine?"] = "Yes"
            row["Reason"] = f"{r1} swimmers"
            used_male_ids.add(matching["Event #"])

            # Append female row first
            result.append(row)

            # Now insert a silent highlight flag in male row (not shown in table)
            male_row = matching.copy()
            male_row["Can Combine?"] = ""
            male_row["Reason"] = f"{r2} swimmers"
            male_row["_highlight_partner"] = True  # internal only
            result.append(male_row)
            continue

        result.append(row)

    return result

def export_pairs_to_csv(pairs, csv_path, meet_title):
    if not pairs:
        return

    df = pd.DataFrame(pairs)
    headers = [col for col in df.columns if col not in ("Female # Swimmers", "Male # Swimmers")]

    central_time = datetime.now(ZoneInfo("America/Chicago"))
    timestamp = central_time.strftime("Report generated %m/%d/%Y %I:%M:%S %p")

    safe_title = meet_title.replace(",", "")

    with open(csv_path, "w", newline="") as f:
        # Top header
        f.write("Combo Events\n")
        f.write(f"{safe_title}\n")
        f.write("\n")

        # Column headers
        f.write(",".join(headers) + "\n")

        # Data rows
        for _, row in df.iterrows():
            f.write(",".join([str(row[col]) for col in headers]) + "\n")

        # Footer
        f.write("\n")
        f.write(f"{timestamp}\n")

def export_pairs_to_pdf(pairs, pdf_path, meet_title):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Centered title
    pdf.set_font("Helvetica", "B", 12)
    from fpdf.enums import XPos, YPos

    pdf.cell(0, 10, "Combo Events", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 8, meet_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.ln(4)  # Small space before table

    pdf.set_font("Helvetica", size=10)

    # Table column headers
    headers = [
        "Female\nEvent #", "Female\nAge", "Female\nHeat #",
        "combine\nwith",
        "Male\nEvent #", "Male\nAge", "Male\nHeat #",
        "Distance\n ", "Stroke\n "
    ]

    data_keys = [
        "Female Event #", "Female Age", "Female Heat #",
        "combine with",
        "Male Event #", "Male Age", "Male Heat #",
        "Distance", "Stroke"
    ]

    # Column widths (adjust as needed)
    col_widths = [20, 27, 20, 25, 20, 27, 20, 20, 30]
    table_width = sum(col_widths)

    gray_fill = (235, 235, 235)  # RGB for #CCCCCC

    # Draw header row
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x((pdf.w - table_width) / 2)
    y_start = pdf.get_y()
    x_start = pdf.get_x()

    from fpdf.enums import XPos, YPos

    for i, header in enumerate(headers):
        col_width = col_widths[i]
        # Draw filled rectangle behind header
        pdf.set_fill_color(*gray_fill)
        pdf.rect(x_start, y_start, col_width, 8, style='F')
        pdf.set_x((pdf.w - table_width) / 2)

        # Then write the header text (can be multi-line)
        pdf.set_xy(x_start, y_start)
        pdf.multi_cell(
            col_width, 4, header,
            border=1, align="C",
            new_x=XPos.RIGHT, new_y=YPos.TOP,
            max_line_height=4
        )
        x_start += col_width

    pdf.ln(8)  # Adjust spacing below header row

    # Draw each row
    pdf.set_font("Helvetica", size=9)
    for row in pairs:
        pdf.set_x((pdf.w - table_width) / 2)
        for i, key in enumerate(data_keys):
            text = str(row[key])

            # Determine if this column should have gray fill
            if key in ["combine with", "Distance", "Stroke"]:
                pdf.set_fill_color(*gray_fill)
                fill = True
            else:
                fill = False

            pdf.cell(col_widths[i], 8, sanitize_for_pdf(text), border=1, fill=fill)
        pdf.ln()

    # Add timestamp centered below the table, in CDT
    pdf.set_font("Helvetica", size=7)
    local_time = datetime.now(ZoneInfo("America/Chicago"))
    timestamp = local_time.strftime("Report generated %m/%d/%Y %I:%M:%S %p")
    pdf.ln(4)
    pdf.cell(0, 5, timestamp, align="C")

    pdf.output(pdf_path)
    print(f"📄 Exported {len(pairs)} combinable pairs to '{pdf_path}'")

def extract_events_from_bad_pdf(pdf_path):
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
                        meet_title = meet_title.replace("—", "-")

            for line in lines:
                # Skip lines that don't look like events
                if not re.match(r"^\d+\s+(Mixed|Boys|Girls|Men|Women)\s", line):
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
                    "Age Group": age_group,
                    "Distance": distance,
                    "Stroke": stroke,
                    "Entries": entries,
                    "Heats": heats,
                })

    return events, meet_title

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

def save_html_as_pdf(html_content, output_path):
    html_content = "<style>body { font-family: Arial, sans-serif; font-size: 10pt; } th, td { border: 1px solid #888; padding: 6px; text-align: left; } th { background-color: #f0f0f0; } </style>" + html_content
    HTML(string=html_content).write_pdf(output_path)