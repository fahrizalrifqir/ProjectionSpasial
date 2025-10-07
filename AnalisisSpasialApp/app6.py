import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import tempfile, os
from PIL import Image

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
# Streamlit UI
# ===============================
st.set_page_config(page_title="Cek Kelengkapan Dokumen", layout="wide")
st.title("📑 Cek Kelengkapan Dokumen Lingkungan Hidup")

jenis = st.selectbox("Pilih jenis dokumen", list(CRITERIA.keys()))
uploaded_file = st.file_uploader("Upload file PDF", type="pdf")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_input:
        tmp_input.write(uploaded_file.read())
        input_pdf = tmp_input.name

    output_pdf = input_pdf.replace(".pdf", "_checked.pdf")
    KEYWORDS = CRITERIA[jenis]
    found_pages = {k: [] for k in KEYWORDS}

    with pdfplumber.open(input_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:  # OCR jika halaman berupa gambar
                images = convert_from_path(input_pdf, first_page=i+1, last_page=i+1)
                text = pytesseract.image_to_string(images[0], lang="ind")

            for keyword in KEYWORDS:
                if keyword.lower() in text.lower():
                    found_pages[keyword].append(i+1)

    # Highlight hasil di PDF
    doc = fitz.open(input_pdf)
    for keyword, pages in found_pages.items():
        for page_num in pages:
            page = doc[page_num - 1]
            text_instances = page.search_for(keyword)
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.update()
    doc.save(output_pdf)

    # =======================
    # Tampilkan hasil cek
    # =======================
    st.subheader("📊 Hasil Pengecekan")
    for keyword, pages in found_pages.items():
        if pages:
            st.success(f"✅ {keyword} ditemukan di halaman {pages}")
        else:
            st.error(f"❌ {keyword} tidak ditemukan")

    # =======================
    # Preview PDF hasil
    # =======================
    st.subheader("👀 Preview PDF hasil cek")
    preview_pages = st.slider("Pilih halaman untuk dilihat", 1, len(doc), 1)

    page = doc[preview_pages - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # zoom biar lebih jelas
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    st.image(img, caption=f"Halaman {preview_pages}", use_container_width=True)

    # Tombol download
    with open(output_pdf, "rb") as f:
        st.download_button("⬇️ Download PDF hasil cek", f, file_name="dokumen_cek.pdf")

    doc.close()
    os.remove(input_pdf)
    os.remove(output_pdf)
