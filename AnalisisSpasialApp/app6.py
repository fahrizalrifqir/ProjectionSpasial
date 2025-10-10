import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import io
import os

st.set_page_config(page_title="PDF Splitter (Hal 1 & 2–Akhir)", page_icon="📄", layout="centered")

st.title("📄 PDF Splitter — Pisahkan Halaman 1 dan Halaman 2–Akhir")
st.write("Unggah PDF, lalu aplikasi ini akan otomatis membagi:")
st.markdown("- 📘 **Halaman 1** → tetap dengan nama file asli\n- 📗 **Halaman 2 sampai terakhir** → diberi awalan **RPD_** pada nama file")

uploaded_file = st.file_uploader("📤 Upload file PDF", type=["pdf"])

if uploaded_file is not None:
    # Ambil nama file tanpa ekstensi
    original_name = os.path.splitext(uploaded_file.name)[0]
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    
    if total_pages < 2:
        st.warning("⚠️ File PDF ini hanya memiliki 1 halaman, tidak bisa dipisah.")
    else:
        st.success(f"File terbaca: **{uploaded_file.name}** dengan {total_pages} halaman.")

        if st.button("🔪 Split Sekarang"):
            try:
                # === Split halaman 1 ===
                writer1 = PdfWriter()
                writer1.add_page(reader.pages[0])
                output1 = io.BytesIO()
                writer1.write(output1)
                output1.seek(0)

                # === Split halaman 2 sampai akhir ===
                writer2 = PdfWriter()
                for i in range(1, total_pages):
                    writer2.add_page(reader.pages[i])
                output2 = io.BytesIO()
                writer2.write(output2)
                output2.seek(0)

                # Buat nama file sesuai logika
                output_name1 = f"{original_name}.pdf"
                output_name2 = f"RPD_{original_name}.pdf"

                st.success("✅ Split berhasil! Unduh hasil di bawah ini:")
                st.download_button(
                    label=f"⬇️ Unduh Halaman 1 ({output_name1})",
                    data=output1,
                    file_name=output_name1,
                    mime="application/pdf"
                )
                st.download_button(
                    label=f"⬇️ Unduh Halaman 2–{total_pages} ({output_name2})",
                    data=output2,
                    file_name=output_name2,
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
else:
    st.info("Unggah file PDF untuk memulai proses pemisahan.")
