import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import tempfile
import os

# =========================
# Konfigurasi
# =========================
KEYWORDS = ["Berita Acara", "Surat Pernyataan", "Kata Pengantar"]

st.set_page_config(page_title="Cek Kelengkapan Dokumen PDF", layout="centered")

st.title("📑 Cek Kelengkapan Dokumen PDF")
st.write("Upload PDF untuk dicek apakah mengandung: **Berita Acara**, **Surat Pernyataan**, **Kata Pengantar**.")

uploaded_file = st.file_uploader("Upload file PDF", type="pdf")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
        tmp_input.write(uploaded_file.read())
        input_pdf = tmp_input.name

    output_pdf = input_pdf.replace(".pdf", "_checked.pdf")

    found_pages = {k: [] for k in KEYWORDS}

    with pdfplumber.open(input_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            # Jika tidak ada teks, OCR
            if not text:
                images = convert_from_path(input_pdf, first_page=i+1, last_page=i+1)
                text = pytesseract.image_to_string(images[0], lang="ind")

            for keyword in KEYWORDS:
                if keyword.lower() in text.lower():
                    found_pages[keyword].append(i+1)

    # Tandai halaman di PDF asli
    doc = fitz.open(input_pdf)
    for keyword, pages in found_pages.items():
        for page_num in pages:
            page = doc[page_num - 1]
            text_instances = page.search_for(keyword)
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.update()
    doc.save(output_pdf)
    doc.close()

    # =========================
    # Output hasil
    # =========================
    st.subheader("📊 Hasil Pengecekan:")
    for keyword, pages in found_pages.items():
        if pages:
            st.success(f"✅ {keyword} ditemukan di halaman: {pages}")
        else:
            st.error(f"❌ {keyword} tidak ditemukan")

    with open(output_pdf, "rb") as f:
        st.download_button("⬇️ Download PDF hasil cek", f, file_name="dokumen_cek.pdf")

    os.remove(input_pdf)
    os.remove(output_pdf)
