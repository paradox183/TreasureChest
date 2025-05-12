
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

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

    return events, meet_title

def find_combinable_pairs(events, lanes=6):
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

def evaluate_all_events(events, lanes):
    result = []
    for i, e1 in enumerate(events):
        row = e1.copy()
        if e1["Gender"] not in ("Girls", "Women"):
            row["Can Combine?"] = ""
            row["Why Not?"] = ""
            result.append(row)
            continue

        matching = next((e2 for e2 in events[i+1:]
                         if e2["Gender"] in ("Boys", "Men") and
                         e2["Age Group"] == e1["Age Group"] and
                         e2["Distance"] == e1["Distance"] and
                         e2["Stroke"] == e1["Stroke"]), None)

        if not matching:
            row["Can Combine?"] = "No"
            row["Why Not?"] = "No male counterpart"
        else:
            r1 = e1["Entries"] % lanes
            r2 = matching["Entries"] % lanes

            if e1["Entries"] < 1 or matching["Entries"] < 1:
                row["Can Combine?"] = "No"
                row["Why Not?"] = "One event has 0 entries"
            elif r1 == 0 or r2 == 0:
                row["Can Combine?"] = "No"
                row["Why Not?"] = "One event fills all lanes"
            elif r1 + r2 > lanes:
                row["Can Combine?"] = "No"
                row["Why Not?"] = "Too many remainder swimmers"
            else:
                row["Can Combine?"] = "Yes"
                row["Why Not?"] = ""

        result.append(row)
    return result

def export_pairs_to_csv(pairs, csv_path):
    df = pd.DataFrame(pairs)
    df.to_csv(csv_path, index=False)

def export_pairs_to_pdf(pairs, pdf_path, meet_title):
    headers = list(pairs[0].keys()) if pairs else []
    col_widths = [max(20, len(h) * 3) for h in headers]

    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Combo Events", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 8, meet_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(4)

    # Headers
    gray = (204, 204, 204)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*gray)
    x_start = (pdf.w - sum(col_widths)) / 2
    pdf.set_x(x_start)
    for i, header in enumerate(headers):
        pdf.rect(pdf.get_x(), pdf.get_y(), col_widths[i], 8, style='F')
        pdf.multi_cell(col_widths[i], 4, header, border=1, align="C",
                       new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=4)
    pdf.ln(8)

    # Rows
    pdf.set_font("Helvetica", size=9)
    for row in pairs:
        pdf.set_x(x_start)
        for i, key in enumerate(headers):
            text = str(row[key])
            fill = key in ("combine with", "Distance", "Stroke")
            if fill:
                pdf.set_fill_color(*gray)
            pdf.cell(col_widths[i], 8, text, border=1, fill=fill)
        pdf.ln()

    # Timestamp
    pdf.set_font("Helvetica", size=6)
    pdf.ln(4)
    timestamp = datetime.now().strftime("Report generated %m/%d/%Y %I:%M:%S %p")
    pdf.cell(0, 5, timestamp, align="C")

    pdf.output(pdf_path)
