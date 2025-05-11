import pdfplumber
import pandas as pd
import re
from datetime import datetime

LANES = 6  # Change this if needed

def extract_events_from_pdf(pdf_path):
    events = []
    meet_title="Today's Meet"

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            lines = page.extract_text().split('\n')

            for line_num, line in enumerate(lines):
                if "Session Report" in line and "Page" in line:
                    try:
                        start = line.index("Session Report") + len("Session Report")
                        end = line.index("Page")
                        meet_title = line[start:end]
                        meet_title = meet_title.replace("—", "-")
                    except:
                        pass  # fallback to default if slicing fails

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

    return events, meet_title

def find_combinable_pairs(events):
    pairs = []
    for i, e1 in enumerate(events):
        if e1["Gender"] not in ("Girls", "Women") or e1["Entries"] < 1:
            continue

        for j in range(i + 1, len(events)):
            e2 = events[j]

            if e2["Gender"] not in ("Boys", "Men") or e2["Entries"] < 1:
                continue

            if (
                e1["Age Group"] == e2["Age Group"] and
                e1["Distance"] == e2["Distance"] and
                e1["Stroke"] == e2["Stroke"]
            ):
                r1 = e1["Entries"] % LANES
                r2 = e2["Entries"] % LANES

                if r1 == 0 or r2 == 0:
                    continue

                if r1 + r2 <= LANES:
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

def export_pairs_to_csv(pairs, csv_path):
    df = pd.DataFrame(pairs)
    df = df[[
        "Female Event #", "Female Age", "Female Heat #", "Female # Swimmers",
        "combine with",
        "Male Event #", "Male Age", "Male Heat #", "Male # Swimmers",
        "Distance", "Stroke"
    ]]
    df.to_csv(csv_path, index=False)
    print(f"✅ Exported {len(pairs)} combinable pairs to '{csv_path}'")

from fpdf import FPDF

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
        "Female\nEvent #", "Female\nAge", "Female\nHeat #", "Female\n# Swimmers",
        "combine\nwith",
        "Male\nEvent #", "Male\nAge", "Male\nHeat #", "Male\n# Swimmers",
        "Distance\n ", "Stroke\n "
    ]

    data_keys = [
        "Female Event #", "Female Age", "Female Heat #", "Female # Swimmers",
        "combine with",
        "Male Event #", "Male Age", "Male Heat #", "Male # Swimmers",
        "Distance", "Stroke"
    ]

    # Column widths (adjust as needed)
    col_widths = [20, 27, 20, 25, 25, 20, 27, 20, 25, 20, 30]
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

            pdf.cell(col_widths[i], 8, text, border=1, fill=fill)
        pdf.ln()

    # Add timestamp centered below the table
    pdf.set_font("Helvetica", size=7)
    timestamp = datetime.now().strftime("Report generated %m/%d/%Y %I:%M:%S %p")
    pdf.ln(4)
    pdf.cell(0, 5, timestamp, align="C")

    pdf.output(pdf_path)
    print(f"📄 Exported {len(pairs)} combinable pairs to '{pdf_path}'")

if __name__ == "__main__":
    input_pdf = "SessionReport.pdf"
    output_csv = "combinable_events.csv"

    all_events, meet_title = extract_events_from_pdf(input_pdf)
    combinable_pairs = find_combinable_pairs(all_events)
    export_pairs_to_csv(combinable_pairs, output_csv)

    output_pdf = "combinable_events.pdf"
    export_pairs_to_pdf(combinable_pairs, output_pdf, meet_title)