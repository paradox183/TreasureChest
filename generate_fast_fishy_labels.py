
import pandas as pd
from datetime import datetime

def clean_time_string(t):
    return str(t).strip().rstrip("Y").strip()

def parse_seconds(t):
    t = clean_time_string(t)
    if ":" in t:
        m, s = t.split(":")
        return float(m) * 60 + float(s)
    return float(t)

def generate_fast_fishy_labels(report_csv_path):
    df = pd.read_csv(report_csv_path)

    meet_nums = sorted(
        {col.split("-")[0] for col in df.columns if "ResultSec" in col},
        key=lambda x: int(x.replace("Meet", ""))
    )

    last_meet = None
    for meet in reversed(meet_nums):
        if pd.to_numeric(df.get(f"{meet}-ResultSec"), errors="coerce").notna().any():
            last_meet = meet
            break
    if not last_meet:
        return []

    improved_col = f"{last_meet}-Improved"
    result_col = f"{last_meet}-Result"
    date_col = f"{last_meet}-Date"
    name_col = f"{last_meet}-Name"

    prior_winners = {}
    for meet in meet_nums:
        if meet == last_meet:
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

        prev_time = None
        for m in reversed([mn for mn in meet_nums if mn < last_meet]):
            val = row.get(f"{m}-Result")
            if pd.notna(val):
                prev_time = val
                break

        if prev_time:
            try:
                prev_sec = parse_seconds(prev_time)
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

    return labels, drops_df, full_rankings
