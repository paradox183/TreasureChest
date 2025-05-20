
import pandas as pd

def clean_time_string(t):
    return str(t).strip().rstrip("Y").strip()

def parse_seconds(t):
    t = clean_time_string(t)
    if ":" in t:
        m, s = t.split(":")
        return float(m) * 60 + float(s)
    return float(t)

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

def generate_fast_fishy_labels(report_csv_path, target_meet):
    df = pd.read_csv(report_csv_path)
    drops_df = pd.DataFrame()
    rankings = {}

    meet_nums = sorted(
        {col.split("-")[0] for col in df.columns if "ResultSec" in col},
        key=lambda x: int(x.replace("Meet", ""))
    )

    prior_meets = [m for m in meet_nums if m < target_meet]
    if not prior_meets:
        return [], drops_df, rankings

    improved_col = f"{target_meet}-Improved"
    result_col = f"{target_meet}-Result"
    date_col = f"{target_meet}-Date"
    name_col = f"{target_meet}-Name"

    if not all(col in df.columns for col in [improved_col, result_col, date_col, name_col]):
        return [], drops_df, rankings

    # Track prior Fast Fishy winners
    prior_winners = {}
    for meet in meet_nums:
        if meet == target_meet:
            continue
        label_col = f"{meet}-Label"
        if label_col in df.columns:
            winners = df[df[label_col] == "Fast Fishy"]
            for _, row in winners.iterrows():
                prior_winners.setdefault(row["AgeGroup"], set()).add(row["LastName_FirstName"])

    drops = []

    for _, row in df.iterrows():
        if not row.get(improved_col):
            continue

        # Must have prior time
        has_prior = False
        for m in reversed(prior_meets):
            prev_col = f"{m}-Result"
            if prev_col in df.columns and pd.notna(row.get(prev_col)):
                has_prior = True
                break
        if not has_prior:
            continue

        try:
            prev_sec = parse_seconds(row[prev_col])
            new_sec = parse_seconds(row[result_col])
            drop = prev_sec - new_sec
            if drop > 0:
                drops.append({
                    "swimmer": row["LastName_FirstName"],
                    "last": row["LastName"],
                    "first": row["FirstName"],
                    "age": row["AgeGroup"],
                    "drop": drop,
                    "date": row[date_col],
                    "meet": row[name_col]
                })
        except:
            continue

    drops_df = pd.DataFrame(drops)
    labels = []

    for age, group in drops_df.groupby("age"):
        group_sorted = group.groupby("swimmer").agg({
            "drop": "sum",
            "last": "first",
            "first": "first",
            "date": "first",
            "meet": "first"
        }).reset_index().sort_values("drop", ascending=False)

        rankings[age] = [
            {
                "name": f"{row['last']}, {row['first']}",
                "drop": f"-{row['drop']:.2f}s"
            } for _, row in group_sorted.iterrows()
        ]

        prior = prior_winners.get(age, set())
        winner = None
        mentions = []

        for _, row in group_sorted.iterrows():
            swimmer = row["swimmer"]
            if swimmer not in prior and winner is None:
                winner = row
                labels.append([
                    f"{row['last']}, {row['first']}",
                    f"Fast Fishy - {age}",
                    f"Total time drop: -{row['drop']:.2f}s",
                    row["date"],
                    row["meet"]
                ])
            elif swimmer in prior:
                mentions.append(row)

        for m in mentions:
            labels.append([
                f"{m['last']}, {m['first']}",
                f"Honorable Mention - {age}",
                f"Total time drop: -{m['drop']:.2f}s",
                m["date"],
                m["meet"]
            ])

    return labels, drops_df, rankings
