from fpdf import FPDF

class Avery5160LabelSheet(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='in', format='Letter')
        self.set_auto_page_break(False)
        self.labels_per_row = 3
        self.labels_per_column = 10
        self.label_width = 2.625
        self.label_height = 1.0
        self.margin_left = 0.1875
        self.margin_top = 0.5
        self.h_pitch = 2.75
        self.v_pitch = 1.0
        self.labels_per_page = self.labels_per_row * self.labels_per_column
        self.set_font("Helvetica", size=8)
        self.current_label_index = 0
        self.add_page()

    def add_label(self, lines):
        if self.current_label_index > 0 and self.current_label_index % self.labels_per_page == 0:
            self.add_page()
            self.current_label_index = 0

        col = self.current_label_index % self.labels_per_row
        row = (self.current_label_index // self.labels_per_row) % self.labels_per_column

        x = self.margin_left + col * self.h_pitch
        y = self.margin_top + row * self.v_pitch

        max_width = self.label_width

        # line_height = self.label_height / 5.0
        line_height = 0.16
        # max_chars = 40
        for i, text in enumerate(lines[:5]):
            clean_text = text.strip()

            # Truncate based on actual string width
            while self.get_string_width(clean_text) > max_width:
                clean_text = clean_text[:-1]
                if len(clean_text) <= 3:
                    break
            if self.get_string_width(clean_text) > max_width:
                clean_text = clean_text[:max(0, len(clean_text) - 3)] + "..."

            self.set_xy(x, y + i * line_height)
            self.cell(self.label_width, line_height, clean_text, ln=0)

        self.current_label_index += 1

def render_label_pdf(label_data, output_path):
    """
    label_data: list of lists (each sublist = 1 label of up to 5 lines)
    output_path: where to save the output PDF
    """
    pdf = Avery5160LabelSheet()
    for lines in label_data:
        pdf.add_label(lines)
    pdf.output(output_path)
