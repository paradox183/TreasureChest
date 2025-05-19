
import pandas as pd

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

def extract_meets_with_times(report_csv_path):
    df = pd.read_csv(report_csv_path)
    result_sec_cols = [col for col in df.columns if "ResultSec" in col]
    meet_numbers = sorted(set(col.split("-")[0] for col in result_sec_cols), key=lambda x: int(x.replace("Meet", "")))
    valid_meets = []

    for meet in meet_numbers:
        col = f"{meet}-ResultSec"
        if col in df.columns and pd.to_numeric(df[col], errors='coerce').notna().any():
            valid_meets.append(meet)

    return valid_meets

def generate_time_improvement_labels(report_csv_path, target_meet):
    df = pd.read_csv(report_csv_path)

    labels = []

    improved_col = f"{target_meet}-Improved"
    result_str_col = f"{target_meet}-Result"
    date_col = f"{target_meet}-Date"
    name_col = f"{target_meet}-Name"

    if not all(col in df.columns for col in [improved_col, result_str_col, date_col, name_col]):
        return []

    improved_df = df[df[improved_col] == True]

    for _, row in improved_df.iterrows():
        swimmer = f"{row['LastName']}, {row['FirstName']}"
        event_name = f"{row['EventDistance']} {row['EventStroke']}".strip()
        new_time = clean_time(row[result_str_col])
        meet_date = row[date_col]
        meet_name = row[name_col]

        # Find previous best time
        prev_time = None
        for col in df.columns:
            if col.startswith("Meet") and col.endswith("-Result"):
                if target_meet in col:
                    break
                val = row.get(col)
                if pd.notna(val):
                    prev_time = clean_time(val)

        if prev_time:
            labels.append([
                swimmer,
                event_name,
                f"Previous best: {prev_time} ({calculate_time_drop(prev_time, new_time)})",
                meet_date,
                meet_name
            ])

    return labels
