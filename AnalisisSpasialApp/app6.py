import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import tempfile, os, io
import docx
from rapidfuzz import fuzz
import easyocr
import numpy as np
import pandas as pd
from openpyxl import Workbook

# ===============================
# Kriteria resmi per jenis dokumen
# ===============================
CRITERIA = {
    "DELH/DPHL": [
        "Kata Pengantar",
        "Berita Acara Penilaian",
        "Surat Pernyataan Pengelolaan",
        "Surat Pernyataan Ketua Tim",
        "Daftar Isi",
        "Lampiran SK Menteri",
        "RKL-RPL"
    ],
    "KA": [
        "Berita Acara Rapat Tim Teknis Formulir Kerangka Acuan",
        "Kata Pengantar",
        "Berita Acara Rapat Tim Teknis Lanjutan",
        "Saran, Masukan dan Tanggapan Tim Penilai",
        "Surat Pernyataan Pemrakarsa",
        "Peta Tapak Proyek",
        "Peta Batas Ekologis",
        "Peta Batas Sosial",
        "Peta Batas Administrasi",
        "Hasil Konsultasi Publik",
        "Surat Pengantar Penyampaian Dokumen Final KA",
        "Sertifikat Kompetensi Penyusun",
        "Surat Pernyataan Tenaga Ahli"
    ],
    "ANDAL RKL-RPL": [
        "Berita Acara Rapat Tim Teknis",
        "Berita Acara Rapat Komisi",
        "Kata Pengantar",
        "Saran, Masukan dan Tanggapan Tim Penilai",
        "Surat Pernyataan Pemrakarsa",
        "Peta Tapak Proyek",
        "Peta Batas Ekologis",
        "Peta Batas Sosial",
        "Peta Batas Administrasi",
        "Surat Pengantar Penyampaian Dokumen Final ANDAL RKL-RPL",
        "Sertifikat Kompetensi Penyusun",
        "Surat Pernyataan Tenaga Ahli",
        "Surat Pernyataan Kesanggupan"
    ],
    "Addendum ANDAL RKL-RPL": [
        "Berita Acara Rapat Tim Teknis",
        "Berita Acara Rapat Komisi",
        "Kata Pengantar",
        "Saran, Masukan dan Tanggapan Tim Penilai",
        "Peta Tapak Proyek",
        "Surat Pengantar Penyampaian Dokumen Final Addendum",
        "Sertifikat Kompetensi Penyusun",
        "Surat Pernyataan Tenaga Ahli",
        "Surat Pernyataan Kesanggupan"
    ],
    "UKL-UPL": [
        "Berita Acara Rapat Koordinasi",
        "Kata Pengantar",
        "Saran, Masukan dan Tanggapan Tim Penilai",
        "Peta Tapak Proyek",
        "Peta Pengelolaan Lingkungan Hidup",
        "Peta Pemantauan Lingkungan Hidup",
        "Surat Pengantar Penyampaian Dokumen Final UKL-UPL",
        "Surat Pernyataan Kesanggupan",
        "Surat Pernyataan Pemrakarsa"
    ]
}

# ===============================
# Fuzzy matching
# ===============================
def fuzzy_match(text, keyword, threshold=80):
    score = fuzz.partial_ratio(keyword.lower(), text.lower())
    return score >= threshold, score

# ===============================
# EasyOCR Reader
# ===============================
reader = easyocr.Reader(['id', 'en'], gpu=False)

# ===============================
# Analisis DOCX
# ===============================
def analyze_docx(input_docx, keywords):
    doc = docx.Document(input_docx)
    found = {k: [] for k in keywords}

    for i, para in enumerate(doc.paragraphs):
        for keyword in keywords:
            match, score = fuzzy_match(para.text, keyword)
            if match:
                found[keyword].append(f"paragraf {i+1} (score {score})")
                for run in para.runs:
                    if fuzz.partial_ratio(run.text.lower(), keyword.lower()) >= 80:
                        run.font.highlight_color = 7  # highlight kuning

    output_path = input_docx.replace(".docx", "_checked.docx")
    doc.save(output_path)
    return found, output_path

# ===============================
# Analisis PDF
# ===============================
def analyze_pdf(input_pdf, keywords):
    found = {k: [] for k in keywords}
    doc = fitz.open(input_pdf)

    with pdfplumber.open(input_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            if not text:  # OCR dengan EasyOCR
                page_fitz = doc[i]
                pix = page_fitz.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_np = np.array(img)
                results = reader.readtext(img_np, detail=0)
                text = " ".join(results)

            for keyword in keywords:
                match, score = fuzzy_match(text, keyword)
                if match:
                    found[keyword].append(f"halaman {i+1} (score {score})")

    # Highlight PDF
    for keyword, pages in found.items():
        for p in pages:
            page_num = int(p.split()[1])
            page = doc[page_num - 1]
            for inst in page.search_for(keyword.split()[0]):
                highlight = page.add_highlight_annot(inst)
                highlight.update()

    output_path = input_pdf.replace(".pdf", "_checked.pdf")
    doc.save(output_path)
    doc.close()
    return found, output_path

# ===============================
# Streamlit UI
# ===============================
st.set_page_config(page_title="Cek Kelengkapan Dokumen", layout="wide")
st.title("📑 Cek Kelengkapan Dokumen Lingkungan Hidup")

jenis = st.selectbox("Pilih jenis dokumen", list(CRITERIA.keys()))
uploaded_files = st.file_uploader("Upload satu atau lebih file (PDF/DOCX)", type=["pdf","docx"], accept_multiple_files=True)

if uploaded_files:
    KEYWORDS = CRITERIA[jenis]
    overall_found = {k: [] for k in KEYWORDS}

    for uploaded_file in uploaded_files:
        st.markdown(f"### 🔍 Mengecek file: **{uploaded_file.name}**")

        if uploaded_file.name.lower().endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_input:
                tmp_input.write(uploaded_file.read())
                input_docx = tmp_input.name

            found_pages, output_docx = analyze_docx(input_docx, KEYWORDS)
            for k, v in found_pages.items():
                overall_found[k].extend(v)

            for keyword, paras in found_pages.items():
                if paras:
                    st.success(f"✅ {keyword} ditemukan di {paras}")
                else:
                    st.error(f"❌ {keyword} tidak ditemukan")

            with open(output_docx, "rb") as f:
                st.download_button(f"⬇️ Download hasil cek ({uploaded_file.name})", f, file_name=f"{uploaded_file.name.replace('.docx','_cek.docx')}")

            os.remove(input_docx)
            os.remove(output_docx)

        elif uploaded_file.name.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
                tmp_input.write(uploaded_file.read())
                input_pdf = tmp_input.name

            found_pages, output_pdf = analyze_pdf(input_pdf, KEYWORDS)
            for k, v in found_pages.items():
                overall_found[k].extend(v)

            for keyword, pages in found_pages.items():
                if pages:
                    st.success(f"✅ {keyword} ditemukan di {pages}")
                else:
                    st.error(f"❌ {keyword} tidak ditemukan")

            st.subheader(f"👀 Preview hasil {uploaded_file.name}")
            doc = fitz.open(output_pdf)
            preview_pages = st.slider(f"Pilih halaman ({uploaded_file.name})", 1, len(doc), 1, key=uploaded_file.name)
            page = doc[preview_pages - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.image(img, caption=f"{uploaded_file.name} - halaman {preview_pages}", use_container_width=True)
            doc.close()

            with open(output_pdf, "rb") as f:
                st.download_button(f"⬇️ Download hasil cek ({uploaded_file.name})", f, file_name=f"{uploaded_file.name.replace('.pdf','_cek.pdf')}")

            os.remove(input_pdf)
            os.remove(output_pdf)

    # ===============================
    # Rekap Tabel Checklist
    # ===============================
    st.markdown("## 📋 Rekap Kelengkapan Semua File (Tabel Checklist)")

    rekap_data = []
    for keyword, lokasi in overall_found.items():
        if lokasi:
            rekap_data.append([keyword, "✅ Ada", ", ".join(lokasi)])
        else:
            rekap_data.append([keyword, "❌ Tidak ada", "-"])

    df_rekap = pd.DataFrame(rekap_data, columns=["Kriteria", "Status", "Lokasi"])
    st.dataframe(df_rekap, use_container_width=True)

    # download Excel
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Kelengkapan"
    ws.append(["Kriteria", "Status", "Lokasi"])
    for row in rekap_data:
        ws.append(row)
    wb.save(output)

    st.download_button("⬇️ Download Rekap (Excel)", data=output.getvalue(), file_name="rekap_kelengkapan.xlsx")
