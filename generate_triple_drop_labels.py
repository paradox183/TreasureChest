
import pandas as pd
import re

def clean_age_group(age_group):
    if pd.isna(age_group):
        return ""
    return re.sub(r'^0(\d)-0?(\d)', r'\1-\2', age_group)

def generate_triple_drop_labels(report_csv_path):
    report_df = pd.read_csv(report_csv_path)

    # Identify meet numbers
    result_sec_cols = [col for col in report_df.columns if "ResultSec" in col]
    meet_numbers = sorted(set(col.split("-")[0] for col in result_sec_cols), key=lambda x: int(x.replace("Meet", "")))

    # Identify the last meet with any data
    last_meet = None
    for meet in reversed(meet_numbers):
        result_col = f"{meet}-ResultSec"
        if pd.to_numeric(report_df[result_col], errors='coerce').notna().any():
            last_meet = meet
            break

    if not last_meet:
        return []

    # Determine relevant column names
    improved_col = f"{last_meet}-Improved"
    date_col = f"{last_meet}-Date"
    name_col = f"{last_meet}-Name"
    result_col = f"{last_meet}-ResultSec"

    # Filter only rows marked as improved
    candidates = report_df[report_df[improved_col] == True].copy()

    valid_rows = []
    for _, row in candidates.iterrows():
        swimmer = row["LastName_FirstName"]
        distance = row["EventDistance"]
        stroke = row["EventStroke"]

        # Get all prior meets
        prior_meets = [m for m in meet_numbers if int(m.replace("Meet", "")) < int(last_meet.replace("Meet", ""))]
        prior_result_cols = [f"{m}-ResultSec" for m in prior_meets]

        # Get all rows with same swimmer + event
        row_subset = report_df[
            (report_df["LastName_FirstName"] == swimmer) &
            (report_df["EventDistance"] == distance) &
            (report_df["EventStroke"] == stroke)
            ]

        valid_prior = row_subset[prior_result_cols].apply(
            lambda x: pd.to_numeric(x, errors='coerce').notna().any(), axis=1
        ).any()

        if valid_prior:
            valid_rows.append(row)

    filtered_df = pd.DataFrame(valid_rows)

    # Count by swimmer
    triple_qualifiers = filtered_df.groupby("LastName_FirstName").filter(lambda x: len(x) >= 3).copy()
    final_labels = triple_qualifiers.sort_values(by="LastName_FirstName").drop_duplicates(subset=["LastName_FirstName"])

    label_data = []
    for _, row in final_labels.iterrows():
        label_data.append([
            row["LastName_FirstName"],
            clean_age_group(row.get("AgeGroup", "")),
            "Triple Drop",
            row[date_col],
            row[name_col]
        ])

    return label_data
