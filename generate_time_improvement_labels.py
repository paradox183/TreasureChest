
import pandas as pd
from datetime import datetime

def calculate_time_drop(prev, new):
    try:
        def parse_time(t):
            t = str(t).strip().rstrip("Y").strip()
            if ":" in t:
                m, s = t.split(":")
                return float(m) * 60 + float(s)
            return float(t)

        prev_sec = parse_time(prev)
        new_sec = parse_time(new)
        drop = prev_sec - new_sec

        if drop <= 0:
            return "0.00s"
        return f"-{drop:.2f}"
    except:
        return "?"

def clean_time(t):
    return str(t).strip().rstrip("Y").strip()

def generate_time_improvement_labels(report_csv_path):
    report_df = pd.read_csv(report_csv_path)

    # Step 1: Identify all meet numbers
    result_sec_cols = [col for col in report_df.columns if "ResultSec" in col]
    meet_numbers = sorted(set(col.split("-")[0] for col in result_sec_cols), key=lambda x: int(x.replace("Meet", "")))

    labels = []

    for meet in meet_numbers:
        improved_col = f"{meet}-Improved"
        result_col = f"{meet}-ResultSec"
        result_str_col = f"{meet}-Result"
        date_col = f"{meet}-Date"
        name_col = f"{meet}-Name"

        # Skip if meet is missing necessary columns
        if not all(col in report_df.columns for col in [improved_col, result_col, result_str_col, date_col, name_col]):
            continue

        # Step 2: Filter rows where swimmer improved
        improved_df = report_df[report_df[improved_col] == True]

        for _, row in improved_df.iterrows():
            swimmer = f"{row['LastName']}, {row['FirstName']}"
            event_name = f"{row['EventDistance']} {row['EventStroke']}"
            new_time = row[result_str_col]
            meet_date = row[date_col]
            meet_name = row[name_col]

            # Step 3: Find the most recent previous valid time
            prev_time = None
            prev_meets = [m for m in meet_numbers if int(m.replace("Meet", "")) < int(meet.replace("Meet", ""))]

            for prev in reversed(prev_meets):
                prev_col = f"{prev}-Result"
                if prev_col in report_df.columns:
                    val = row.get(prev_col)
                    if pd.notna(val):
                        prev_time = val
                        break

            if prev_time:
                labels.append([
                    swimmer,
                    event_name,
                    f"Previous best: {clean_time(prev_time)} ({calculate_time_drop(prev_time, new_time)})",
                    meet_date,
                    meet_name
                ])

    return labels
