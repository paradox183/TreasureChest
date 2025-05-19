from flask import Flask, render_template, request, send_file, redirect, url_for
import os
from datetime import datetime
from parse_utils import (
    extract_events_from_pdf,
    evaluate_all_events,
    find_combinable_pairs,
    export_pairs_to_pdf,
    export_pairs_to_csv
)
from generate_triple_drop_labels import generate_triple_drop_labels
from generate_time_improvement_labels import generate_time_improvement_labels
from render_labels import render_label_pdf

app = Flask(__name__)
UPLOAD_FOLDER = "static/generated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

    if request.method == "POST":
        uploaded_file = request.files.get("report")
        if uploaded_file and uploaded_file.filename.endswith(".csv"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_path = os.path.join(UPLOAD_FOLDER, f"report_{timestamp}.csv")
            uploaded_file.save(saved_path)

            label_data = generate_triple_drop_labels(saved_path)

            if label_data:
                label_filename = f"triple_labels_{timestamp}.pdf"
                output_path = os.path.join(UPLOAD_FOLDER, label_filename)
                render_label_pdf(label_data, output_path)

    return render_template(
        "triple_drop.html",
        label_data=label_data,
        label_filename=label_filename
    )

@app.route("/time-improvement-labels", methods=["GET", "POST"])
def time_improvement_labels():
    label_data = []
    label_filename = ""

    if request.method == "POST":
        uploaded_file = request.files.get("report")
        if uploaded_file and uploaded_file.filename.endswith(".csv"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_path = os.path.join(UPLOAD_FOLDER, f"report_{timestamp}.csv")
            uploaded_file.save(saved_path)

            label_data = generate_time_improvement_labels(saved_path)

            if label_data:
                label_filename = f"time_improvement_{timestamp}.pdf"
                output_path = os.path.join(UPLOAD_FOLDER, label_filename)
                render_label_pdf(label_data, output_path)

    return render_template(
        "time_improvement.html",
        label_data=label_data,
        label_filename=label_filename
    )

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)