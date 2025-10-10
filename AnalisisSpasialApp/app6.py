from PyPDF2 import PdfReader, PdfWriter

def split_pdf(input_pdf, splits):
    """
    Memisahkan PDF berdasarkan daftar rentang halaman.

    Parameters:
        input_pdf (str): Nama file PDF sumber.
        splits (list of tuple): Daftar rentang halaman, contoh [(1, 3), (4, 5)]
                                (menggunakan nomor halaman mulai dari 1)
    """
    reader = PdfReader(input_pdf)

    for idx, (start, end) in enumerate(splits, start=1):
        writer = PdfWriter()
        
        # konversi ke index (0-based)
        for i in range(start - 1, end):
            if i < len(reader.pages):
                writer.add_page(reader.pages[i])
        
        output_name = f"output_part_{idx}_halaman_{start}_sampai_{end}.pdf"
        with open(output_name, "wb") as f:
            writer.write(f)
        print(f"✅ File tersimpan: {output_name}")

# ==== Contoh penggunaan ====
if __name__ == "__main__":
    # Nama file PDF sumber
    input_pdf = "input.pdf"
    
    # Tentukan pembagian halaman di sini:
    # Contoh: (1,3) berarti halaman 1-3, (4,5) berarti halaman 4-5
    splits = [(1, 3), (4, 5)]

    # Jalankan fungsi
    split_pdf(input_pdf, splits)
