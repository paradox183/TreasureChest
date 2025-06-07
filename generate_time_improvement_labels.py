import math
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
            title = df[f"{meet}-Name"].dropna().values[0] if f"{meet}-Name" in df else ""
            date = df[f"{meet}-Date"].dropna().values[0] if f"{meet}-Date" in df else ""
            display = f"{title} — {date}" if title or date else meet
            valid_meets.append((meet, display))

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

    # Identify all meet numbers
    meet_nums = sorted(
        {col.split("-")[0] for col in df.columns if col.endswith("-Result")},
        key=lambda x: int(x.replace("Meet", ""))
    )

    earlier_meets = [m for m in meet_nums if m < target_meet]

    for _, row in improved_df.iterrows():
        swimmer = f"{row['LastName']}, {row['FirstName']}"
        event_name = f"{row['EventDistance']} {row['EventStroke']}".strip()
        new_time = clean_time(row[result_str_col])
        meet_date = row[date_col]
        meet_name = row[name_col]

        best_time_val = None
        best_time_str = None

        for m in earlier_meets:
            col = f"{m}-Result"
            if col in df.columns:
                val = row.get(col)
                if pd.notna(val):
                    try:
                        t = clean_time(val)
                        t_sec = float(t.split(":")[0]) * 60 + float(t.split(":")[1]) if ":" in t else float(t)
                        if best_time_val is None or t_sec < best_time_val:
                            best_time_val = t_sec
                            best_time_str = t
                    except:
                        continue

        if best_time_str:
            drop_str = calculate_time_drop(best_time_str, new_time)
            labels.append([
                swimmer,
                event_name,
                f"Previous best: {best_time_str} ({drop_str})",
                meet_date,
                meet_name
            ])

    return labels
