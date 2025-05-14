
import pandas as pd
import re

def clean_age_group(age_group):
    if pd.isna(age_group):
        return ""
    return re.sub(r'^0(\d)-0?(\d)', r'\1-\2', age_group)

def generate_triple_drop_labels(report_csv_path):
    report_df = pd.read_csv(report_csv_path)

    # Step 1: find the most recent ResultSec column
    result_sec_cols = [col for col in report_df.columns if "ResultSec" in col]
    last_valid_result_col = None
    for col in reversed(result_sec_cols):
        if pd.to_numeric(report_df[col], errors='coerce').notna().any():
            last_valid_result_col = col
            break

    if not last_valid_result_col:
        return []

    meet_prefix = last_valid_result_col.split("-")[0]
    improved_col = f"{meet_prefix}-Improved"
    date_col = f"{meet_prefix}-Date"
    name_col = f"{meet_prefix}-Name"

    # Step 2: filter TRUE improvements with prior valid times
    filtered_rows = []
    last_index = result_sec_cols.index(last_valid_result_col)

    for _, row in report_df.iterrows():
        if not row.get(improved_col, False):
            continue

        # Check earlier ResultSec columns only by index
        prev_results = [
            pd.to_numeric(row[col], errors='coerce')
            for col in result_sec_cols[:last_index]
        ]
        prior_valid_times = [val for val in prev_results if pd.notna(val)]

        if prior_valid_times:
            filtered_rows.append(row)

    filtered_df = pd.DataFrame(filtered_rows)

    # Step 3: find swimmers with 3+ valid improvements
    triple_qualifiers = filtered_df.groupby("LastName_FirstName").filter(lambda x: len(x) >= 3).copy()
    final_labels = triple_qualifiers.sort_values(by=["LastName_FirstName"]).drop_duplicates(subset=["LastName_FirstName"])

    # Step 4: build label output
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
