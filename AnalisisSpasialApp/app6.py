import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import tempfile, os, io, re
import docx
import pandas as pd
from openpyxl import Workbook

# ===============================
# Kriteria dokumen resmi (AMDAL + lainnya)
# ===============================
CRITERIA = {
    "DELH/DPHL": [
        "Kata Pengantar",
        "Berita Acara Penilaian",
        "Surat Pernyataan Pengelolaan"
    ],
    "KA": [
        "Berita Acara Rapat Tim Teknis Formulir Kerangka Acuan",
        "Kata Pengantar",
        "Berita Acara Rapat Tim Teknis Lanjutan",
        "Saran Masukan dan Tanggapan Tim Penilai",
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
        "Berita Acara Rapat Tim Teknis Lanjutan",
        "Kata Pengantar",
        "Saran Masukan dan Tanggapan Tim Penilai",
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
        "Berita Acara Rapat Tim Teknis Lanjutan",
        "Kata Pengantar",
        "Saran Masukan dan Tanggapan Tim Penilai",
        "Peta Tapak Proyek",
        "Peta Batas Ekologis",
        "Peta Batas Sosial",
        "Peta Batas Administrasi",
        "Surat Pengantar Penyampaian Dokumen Final Addendum",
        "Sertifikat Kompetensi Penyusun",
        "Surat Pernyataan Tenaga Ahli",
        "Surat Pernyataan Kesanggupan"
    ],
    "UKL-UPL": [
        "Berita Acara Rapat Koordinasi",
        "Kata Pengantar",
        "Saran Masukan dan Tanggapan Tim Penilai",
        "Peta Tapak Proyek",
        "Peta Pengelolaan Lingkungan Hidup",
        "Peta Pemantauan Lingkungan Hidup",
        "Surat Pengantar Penyampaian Dokumen Final UKL-UPL",
        "Surat Pernyataan Kesanggupan",
        "Surat Pernyataan Pemrakarsa"
    ]
}

# ===============================
# Matching kata utuh (lebih presisi)
# ===============================
def keyword_match(text, keyword, min_ratio=0.5):
    """
    Mencocokkan keyword hanya berdasarkan kata utuh, bukan substring.
    Contoh: 'saran masukan dan tanggapan' tidak cocok untuk 'sarana'.
    """
    words = keyword.lower().split()
    text_lower = text.lower()
    matches = 0
    for w in words:
        if re.search(rf"\b{re.escape(w)}\b", text_lower):
            matches += 1
    return matches / len(words) >= min_ratio, matches

# ===============================
# Analisis DOCX
# ===============================
def analyze_docx(input_docx, keywords):
    doc = docx.Document(input_docx)
    found = {k: [] for k in keywords}

    for i, para in enumerate(doc.paragraphs):
        for keyword in keywords:
            matched, _ = keyword_match(para.text, keyword)
            if matched:
                found[keyword].append(f"paragraf {i+1}")

    output_path = input_docx.replace(".docx", "_checked.docx")
    doc.save(output_path)
    return found, output_path

# ===============================
# Analisis PDF (dengan batas 3 halaman teratas)
# ===============================
def analyze_pdf(input_pdf, keywords):
    found = {k: [] for k in keywords}
    doc = fitz.open(input_pdf)
    match_scores = {k: {} for k in keywords}

    with pdfplumber.open(input_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            for keyword in keywords:
                matched, score = keyword_match(text, keyword)
                if score > 0:
                    match_scores[keyword][i+1] = score

    # Ambil 3 halaman teratas per keyword
    for keyword, page_scores in match_scores.items():
        top_pages = sorted(page_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        found[keyword] = [f"halaman {p[0]}" for p in top_pages]

    # Highlight kata pertama di halaman-halaman tersebut
    for keyword, pages in found.items():
        first_word = keyword.split()[0]
        for p in pages:
            page_num = int(p.split()[1])
            page = doc[page_num - 1]
            for inst in page.search_for(first_word):
                highlight = page.add_highlight_annot(inst)
                highlight.update()

    output_path = input_pdf.replace(".pdf", "_checked.pdf")
    doc.save(output_path)
    doc.close()
    return found, output_path

# ===============================
# Streamlit UI
# ===============================
st.set_page_config(page_title="Cek Dokumen AMDAL", layout="wide")
st.title("📑 Cek Kelengkapan Dokumen Lingkungan Hidup (AMDAL)")

jenis = st.selectbox("Pilih jenis dokumen", list(CRITERIA.keys()))
uploaded_files = st.file_uploader("Upload file (PDF/DOCX)", type=["pdf","docx"], accept_multiple_files=True)

if uploaded_files:
    KEYWORDS = CRITERIA[jenis]
    overall_found = {k: [] for k in KEYWORDS}

    for uploaded_file in uploaded_files:
        st.subheader(f"🔍 Mengecek: {uploaded_file.name}")

        if uploaded_file.name.lower().endswith(".docx"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(uploaded_file.read())
                input_docx = tmp.name

            found, output_docx = analyze_docx(input_docx, KEYWORDS)
            for k, v in found.items():
                overall_found[k].extend(v)
                st.write(f"{k}: {'✅ ditemukan' if v else '❌ tidak'}")

            with open(output_docx, "rb") as f:
                st.download_button("⬇️ Download hasil cek DOCX", f, file_name=f"{uploaded_file.name.replace('.docx','_cek.docx')}")

            os.remove(input_docx)
            os.remove(output_docx)

        elif uploaded_file.name.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                input_pdf = tmp.name

            found, output_pdf = analyze_pdf(input_pdf, KEYWORDS)
            for k, v in found.items():
                overall_found[k].extend(v)
                st.write(f"{k}: {'✅ ditemukan' if v else '❌ tidak'}")

            with open(output_pdf, "rb") as f:
                st.download_button("⬇️ Download hasil cek PDF", f, file_name=f"{uploaded_file.name.replace('.pdf','_cek.pdf')}")

            os.remove(input_pdf)
            os.remove(output_pdf)

    # ===============================
    # Rekap hasil
    # ===============================
    st.markdown("## 📋 Rekap")
    data = []
    for k, v in overall_found.items():
        data.append([k, "✅ Ada" if v else "❌ Tidak ada", ", ".join(v) if v else "-"])
    df = pd.DataFrame(data, columns=["Kriteria", "Status", "Lokasi"])
    st.dataframe(df)

    # Download Excel hasil rekap
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.append(["Kriteria", "Status", "Lokasi"])
    for row in data:
        ws.append(row)
    wb.save(output)
    st.download_button("⬇️ Download Rekap (Excel)", output.getvalue(), "rekap.xlsx")
