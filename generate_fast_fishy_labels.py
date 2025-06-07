
import pandas as pd
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

def clean_time_string(t):
    return str(t).strip().rstrip("Y").strip()

def parse_seconds(t):
    t = clean_time_string(t)
    if ":" in t:
        m, s = t.split(":")
        return float(m) * 60 + float(s)
    return float(t)

def generate_fast_fishy_labels(report_csv_path, target_meet):
    df = pd.read_csv(report_csv_path)
    all_winners = set()
    labels = []
    rankings = {}
    drops_df = pd.DataFrame()

    # Get all meet numbers
    meet_nums = sorted(
        {col.split("-")[0] for col in df.columns if "ResultSec" in col},
        key=lambda x: int(x.replace("Meet", ""))
    )

    prior_meets = [m for m in meet_nums if m < target_meet]

    def get_drops_for_meet(meet, earlier_meets):
        improved_col = f"{meet}-Improved"
        result_col = f"{meet}-Result"
        date_col = f"{meet}-Date"
        name_col = f"{meet}-Name"

        drops = []

        for _, row in df.iterrows():
            if not row.get(improved_col):
                continue

            try:
                new_sec = parse_seconds(row[result_col])
            except:
                continue

            # Find best prior time across all earlier meets
            best_sec = None
            for m in earlier_meets:
                prev_col = f"{m}-Result"
                if prev_col in df.columns and pd.notna(row.get(prev_col)):
                    try:
                        prev_sec = parse_seconds(row[prev_col])
                        if best_sec is None or prev_sec < best_sec:
                            best_sec = prev_sec
                    except:
                        continue

            if best_sec is None:
                continue

            drop = best_sec - new_sec
            if drop > 0:
                drops.append({
                    "swimmer": row["LastName_FirstName"],
                    "last": row["LastName"],
                    "first": row["FirstName"],
                    "age": row.get("AgeGroup", "").strip(),
                    "drop": drop,
                    "date": row[date_col],
                    "meet": row[name_col]
                })

        df_drops = pd.DataFrame(drops)
        if "age" not in df_drops.columns:
            df_drops["age"] = ""
        return df_drops

    # Step 1: Loop through all earlier meets to accumulate winners
    for m in prior_meets:
        meet_drops = get_drops_for_meet(m, [x for x in prior_meets if x < m])
        for age, group in meet_drops.groupby("age"):
            sorted_group = group.groupby("swimmer").agg({
                "drop": "sum",
                "last": "first",
                "first": "first"
            }).reset_index().sort_values("drop", ascending=False)
            for _, row in sorted_group.iterrows():
                if row["swimmer"] not in all_winners:
                    all_winners.add(row["swimmer"])
                    break

    # Step 2: Handle the selected meet
    selected_drops = get_drops_for_meet(target_meet, prior_meets)
    drops_df = selected_drops.copy()

    for age, group in selected_drops.groupby("age"):
        sorted_group = group.groupby("swimmer").agg({
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
            } for _, row in sorted_group.iterrows()
        ]

        if len(sorted_group) == 1:
            row = sorted_group.iloc[0]
            labels.append([
                f"{row['last']}, {row['first']}",
                f"Fast Fishy - {age}",
                f"Total time drop: -{row['drop']:.2f}s",
                row["date"],
                row["meet"]
            ])
            all_winners.add(row["swimmer"])
        else:
            top_row = sorted_group.iloc[0]
            if top_row["swimmer"] in all_winners:
                # Honorable Mention
                labels.append([
                    f"{top_row['last']}, {top_row['first']}",
                    f"Repeat Fast Fishy - {age}",
                    f"Total time drop: -{top_row['drop']:.2f}s",
                    top_row["date"],
                    top_row["meet"]
                ])
                # Find next eligible
                for _, row in sorted_group.iloc[1:].iterrows():
                    if row["swimmer"] not in all_winners:
                        labels.append([
                            f"{row['last']}, {row['first']}",
                            f"Fast Fishy - {age}",
                            f"Total time drop: -{row['drop']:.2f}s",
                            row["date"],
                            row["meet"]
                        ])
                        all_winners.add(row["swimmer"])
                        break
            else:
                # Top swimmer is eligible
                labels.append([
                    f"{top_row['last']}, {top_row['first']}",
                    f"Fast Fishy - {age}",
                    f"Total time drop: -{top_row['drop']:.2f}s",
                    top_row["date"],
                    top_row["meet"]
                ])
                all_winners.add(top_row["swimmer"])

    return labels, drops_df, rankings