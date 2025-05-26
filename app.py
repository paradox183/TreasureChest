from flask import Flask, render_template, request, send_file, redirect, url_for
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from parse_utils import (
    extract_events_from_pdf,
    evaluate_all_events,
    find_combinable_pairs,
    export_pairs_to_pdf,
    export_pairs_to_csv,
    sanitize_for_pdf
)
from parse_bad_pdf import extract_events_from_microsoft_pdf
from generate_triple_drop_labels import generate_triple_drop_labels, extract_meets_with_times
from generate_time_improvement_labels import generate_time_improvement_labels, extract_meets_with_times
from generate_fast_fishy_labels import generate_fast_fishy_labels, extract_meets_with_times
from render_labels import render_label_pdf

app = Flask(__name__)
UPLOAD_FOLDER = "static/generated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def home():
    return render_template("landing.html")

@app.route("/combo-generator", methods=["GET", "POST"])
def combo_generator():
    table = []
    meet_title = ""
    csv_path = pdf_path = None
    lanes = None

    if request.method == "POST":
        uploaded_file = request.files.get("pdf")
        lanes = int(request.form.get("lanes", 6))

        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SessionReport_{timestamp}.pdf"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            uploaded_file.save(filepath)

            events, meet_title = extract_events_from_pdf(filepath)
            table = evaluate_all_events(events, lanes)

            csv_path = os.path.join(UPLOAD_FOLDER, f"combo_{timestamp}.csv")
            pdf_path = os.path.join(UPLOAD_FOLDER, f"combo_{timestamp}.pdf")
            combinable_only = find_combinable_pairs(events, lanes)
            combo_count = len(combinable_only)
            export_pairs_to_csv(combinable_only, csv_path, meet_title)
            export_pairs_to_pdf(combinable_only, pdf_path, meet_title)

            return render_template(
                "combo.html",
                meet_title=meet_title,
                table=table,
                lanes=lanes,
                csv_filename=os.path.basename(csv_path),
                pdf_filename=os.path.basename(pdf_path),
                combo_count=combo_count
            )

    return render_template("combo.html")

@app.route("/triple-drop-labels", methods=["GET", "POST"])
def triple_drop_labels():
    label_data = []
    label_filename = ""
    meet_options = []
    selected_meet = ""
    csv_path = ""

    if request.method == "POST":
        if "report" in request.files:
            # Step 1: upload report and show meet dropdown
            uploaded_file = request.files["report"]
            if uploaded_file and uploaded_file.filename.endswith(".csv"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_path = os.path.join(UPLOAD_FOLDER, f"report_{timestamp}.csv")
                uploaded_file.save(csv_path)

                meet_options = extract_meets_with_times(csv_path)

                return render_template(
                    "triple_drop.html",
                    meet_options=meet_options,
                    label_data=[],
                    label_filename="",
                    selected_meet="",
                    csv_uploaded=True,
                    csv_path=os.path.basename(csv_path)
                )

        elif "meet" in request.form and "csv_path" in request.form:
            # Step 2: user selects meet
            selected_meet = request.form["meet"]
            csv_path = os.path.join(UPLOAD_FOLDER, request.form["csv_path"])
            label_data = generate_triple_drop_labels(csv_path, selected_meet)

            if label_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                label_filename = f"triple_drop_{timestamp}.pdf"
                output_path = os.path.join(UPLOAD_FOLDER, label_filename)
                render_label_pdf(label_data, output_path)

    return render_template(
        "triple_drop.html",
        meet_options=[],
        label_data=label_data,
        label_filename=label_filename,
        selected_meet=selected_meet,
        csv_uploaded=False,
        csv_path=""
    )

@app.route("/time-improvement-labels", methods=["GET", "POST"])
def time_improvement_labels():
    label_data = []
    label_filename = ""
    meet_options = []
    selected_meet = ""
    csv_path = ""

    if request.method == "POST":
        if "report" in request.files:
            # Step 1: Upload the file and extract valid meets
            uploaded_file = request.files["report"]
            if uploaded_file and uploaded_file.filename.endswith(".csv"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_path = os.path.join(UPLOAD_FOLDER, f"report_{timestamp}.csv")
                uploaded_file.save(csv_path)

                meet_options = extract_meets_with_times(csv_path)

                return render_template(
                    "time_improvement.html",
                    meet_options=meet_options,
                    label_data=[],
                    label_filename="",
                    selected_meet="",
                    csv_uploaded=True,
                    csv_path=os.path.basename(csv_path)
                )

        elif "meet" in request.form and "csv_path" in request.form:
            # Step 2: User selected a meet
            selected_meet = request.form["meet"]
            csv_path = os.path.join(UPLOAD_FOLDER, request.form["csv_path"])
            label_data = generate_time_improvement_labels(csv_path, selected_meet)

            if label_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                label_filename = f"time_improvement_{timestamp}.pdf"
                output_path = os.path.join(UPLOAD_FOLDER, label_filename)
                render_label_pdf(label_data, output_path)

    return render_template(
        "time_improvement.html",
        meet_options=[],
        label_data=label_data,
        label_filename=label_filename,
        selected_meet=selected_meet,
        csv_uploaded=False,
        csv_path=""
    )

@app.route("/fast-fishy-labels", methods=["GET", "POST"])
def fast_fishy_labels():
    label_data = []
    rankings = {}
    label_filename = ""
    meet_options = []
    selected_meet = ""
    csv_path = ""

    if request.method == "POST":
        if "report" in request.files:
            uploaded_file = request.files["report"]
            if uploaded_file and uploaded_file.filename.endswith(".csv"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_path = os.path.join(UPLOAD_FOLDER, f"report_{timestamp}.csv")
                uploaded_file.save(csv_path)

                meet_options = extract_meets_with_times(csv_path)

                return render_template(
                    "fast_fishy.html",
                    label_data=[],
                    label_filename="",
                    rankings={},
                    meet_options=meet_options,
                    selected_meet="",
                    csv_uploaded=True,
                    csv_path=os.path.basename(csv_path)
                )

        elif "meet" in request.form and "csv_path" in request.form:
            selected_meet = request.form["meet"]
            csv_path = os.path.join(UPLOAD_FOLDER, request.form["csv_path"])
            label_data, _, rankings = generate_fast_fishy_labels(csv_path, selected_meet)

            if label_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                label_filename = f"fast_fishy_{timestamp}.pdf"
                output_path = os.path.join(UPLOAD_FOLDER, label_filename)
                render_label_pdf(label_data, output_path)

    return render_template(
        "fast_fishy.html",
        label_data=label_data,
        label_filename=label_filename,
        rankings=rankings,
        meet_options=[],
        selected_meet=selected_meet,
        csv_uploaded=False,
        csv_path=""
    )

@app.route("/combo-generator-bad", methods=["GET", "POST"])
def combo_generator_bad():
    # output_images = []
    '''
    for i, image in enumerate(images):
        image_id = uuid.uuid4().hex[:8]
        filename = f"ocr_page_{i+1}_{image_id}.png"
        image_path = output_dir / filename
        image.save(image_path)
        output_images.append(str(image_path))
        print("Saved image:", image_path)
    '''

    if request.method == "POST":
        uploaded_file = request.files["pdf"]
        lanes = int(request.form.get("lanes", 6))
        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            filename = secure_filename(uploaded_file.filename)
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            uploaded_file.save(pdf_path)

            try:
                events, meet_title, debug_images = extract_events_from_microsoft_pdf(pdf_path)
                combinable_only = find_combinable_pairs(events, lanes)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base = os.path.splitext(filename)[0]
                csv_name = f"{base}_combos_bad_{timestamp}.csv"
                pdf_name = f"{base}_combos_bad_{timestamp}.pdf"
                csv_path = os.path.join(app.config["UPLOAD_FOLDER"], csv_name)
                pdf_path_out = os.path.join(app.config["UPLOAD_FOLDER"], pdf_name)

                export_pairs_to_csv(combinable_only, csv_path, meet_title)
                # export_pairs_to_pdf(combinable_only, pdf_path_out, meet_title)

                # Tag partner rows for web rendering
                partner_ids = set(row["combine with"] for row in combinable_only)
                full_table = []
                for row in events:
                    d = dict(row)
                    d["_highlight_partner"] = str(row["Event #"]) in partner_ids
                    full_table.append(d)

                return render_template(
                    "combo_bad.html",
                    table=full_table,
                    lanes=lanes,
                    combo_count=len(combinable_only),
                    meet_title=meet_title,
                    csv_filename=csv_name,
                    pdf_filename=pdf_name,
                )

            except Exception as e:
                return f"<h3>Error: {str(e)}</h3>", 500

    return render_template(
        "combo_bad.html",
        events=events,
        meet_title=meet_title,
        debug_images=debug_images)

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)