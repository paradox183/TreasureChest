
import pandas as pd
import re

def clean_age_group(age_group):
    if pd.isna(age_group):
        return ""
    return re.sub(r'^0(\d)-0?(\d)', r'\1-\2', age_group)

def extract_meets_with_times(report_csv_path):
    report_df = pd.read_csv(report_csv_path)
    result_sec_cols = [col for col in report_df.columns if "ResultSec" in col]
    meet_numbers = sorted(set(col.split("-")[0] for col in result_sec_cols), key=lambda x: int(x.replace("Meet", "")))
    valid_meets = []

    for meet in meet_numbers:
        result_col = f"{meet}-ResultSec"
        if result_col in report_df.columns and pd.to_numeric(report_df[result_col], errors='coerce').notna().any():
            title = report_df[f"{meet}-Name"].dropna().values[0] if f"{meet}-Name" in report_df else ""
            date = report_df[f"{meet}-Date"].dropna().values[0] if f"{meet}-Date" in report_df else ""
            display = f"{title} — {date}" if title or date else meet
            valid_meets.append((meet, display))

    return valid_meets

def generate_triple_drop_labels(report_csv_path, target_meet, roster_csv_path=None):
    report_df = pd.read_csv(report_csv_path)

    if target_meet is None:
        return []

    # Determine relevant column names
    improved_col = f"{target_meet}-Improved"
    date_col = f"{target_meet}-Date"
    name_col = f"{target_meet}-Name"
    result_col = f"{target_meet}-ResultSec"

    if not all(col in report_df.columns for col in [improved_col, date_col, name_col, result_col]):
        return []

    # Filter for improvements
    improved_df = report_df[report_df[improved_col] == True]

    # Count how many events each swimmer improved in
    triple_swimmers = improved_df["LastName_FirstName"].value_counts()
    triple_swimmers = triple_swimmers[triple_swimmers >= 3].index.tolist()

    triple_df = improved_df[improved_df["LastName_FirstName"].isin(triple_swimmers)]

    # Build label content
    labels = []

    for name, group in triple_df.groupby("LastName_FirstName"):
        row = group.iloc[0]
        last_first = name
        age_group = clean_age_group(row["AgeGroup"])
        date = row[date_col]
        meet_name = row[name_col]

        labels.append([
            last_first,
            age_group,
            "Triple Drop",
            f"{row['Team']} - {date}",
            meet_name
        ])

    return labels
