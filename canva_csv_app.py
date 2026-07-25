import streamlit as st
import pandas as pd
import io
import re
import json
import tempfile
import os

# Coba import library AI
try:
    import google.generativeai as genai
    from PIL import Image
    import cv2
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# ==========================================
# KONFIGURASI APLIKASI
# ==========================================
st.set_page_config(page_title="Canva CSV Fast", page_icon="⚡", layout="wide")

st.title("⚡ Canva CSV Fast")
st.markdown("**Format Otomatis untuk Canva Bulk Create (Manual & AI Mode)**")

tab_manual, tab_ai = st.tabs(["📝 Mode Manual (Teks)", "🤖 Mode AI (Gemini Vision)"])

# ==========================================
# TAB 1: MODE MANUAL
# ==========================================
with tab_manual:
    st.subheader("Mode Manual (Ubah Daftar Teks)")
    st.markdown("Ubah teks atau daftar nama file biasa menjadi format CSV Canva. Sangat cepat, tanpa AI.")
    
    raw_text = st.text_area("Tempel teks atau daftar nama file di sini...", height=250, key="manual_input")

    if st.button("🚀 Proses Teks", type="primary", key="btn_manual"):
        if not raw_text.strip():
            st.warning("Teks masih kosong. Silakan tempel teks terlebih dahulu.")
        else:
            try:
                # Deteksi jika sudah CSV
                if "," in raw_text and len(raw_text.split('\n')) > 1:
                    result_csv = raw_text
                    st.success("✓ CSV Terdeteksi! (Data langsung diteruskan)")
                else:
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    
                    data = []
                    for line in lines:
                        # Hilangkan ekstensi dan ubah tanda hubung/garis bawah jadi spasi
                        title = re.sub(r'\.[^/.]+$', '', line)
                        title = re.sub(r'[_-]', ' ', title)
                        keywords = ",".join(title.split(' '))
                        
                        data.append({
                            "filename": line,
                            "title": title,
                            "keywords": keywords
                        })
                    
                    df = pd.DataFrame(data)
                    result_csv = df.to_csv(index=False)
                    st.success("✓ Berhasil Konversi Teks menjadi CSV Canva!")

                st.download_button(
                    label="📥 Download CSV (Manual)",
                    data=result_csv,
                    file_name="canva_manual_upload.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data: {e}")

# ==========================================
# TAB 2: MODE AI
# ==========================================
with tab_ai:
    st.subheader("Mode AI (Auto Title & Keywords dari Konten File)")
    st.markdown(
        "Upload gambar, video, atau SVG. Aplikasi akan melihat preview visualnya dan menyuruh Gemini AI "
        "membuatkan **Title** dan **Keywords** otomatis.\n\n"
        "💡 *Sangat hemat biaya: Untuk video (mp4, mov, dll), aplikasi otomatis hanya memotong 1 frame gambar pertama "
        "untuk dikirim ke AI, bukan seluruh videonya.*"
    )
    
    if not AI_AVAILABLE:
        st.error("Library AI belum terinstall. Pastikan `google-generativeai`, `pillow`, dan `opencv-python-headless` sudah ter-install.")
        st.stop()

    api_key = st.text_input("🔑 Masukkan Gemini API Key", type="password", help="Aman: Kunci ini tidak akan disimpan di sistem, hanya di memori sementara browser.")
    
    uploaded_files = st.file_uploader(
        "Upload File (Image, Video, SVG)", 
        accept_multiple_files=True, 
        type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "avi", "svg"]
    )
    
    if st.button("🤖 Analisis dengan AI", type="primary", key="btn_ai"):
        if not api_key:
            st.warning("Silakan masukkan Gemini API Key terlebih dahulu.")
        elif not uploaded_files:
            st.warning("Silakan upload minimal 1 file.")
        else:
            try:
                # Inisialisasi Gemini
                genai.configure(api_key=api_key)
                # Pakai gemini-1.5-flash karena cepat, murah, dan support vision + text
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                ai_data = []
                my_bar = st.progress(0, text="Mempersiapkan...")
                
                for idx, file in enumerate(uploaded_files):
                    file_ext = file.name.split('.')[-1].lower()
                    
                    try:
                        # Prompt sistem yang disuruh membalas dalam format JSON
                        prompt = f"""
                        Kamu adalah ahli desain grafis Canva. Buatlah metadata untuk file dengan nama asli: "{file.name}".
                        Tugasmu:
                        1. Berikan "title" singkat (maksimal 3-6 kata) yang relevan dengan isi gambar/teks ini.
                        2. Berikan "keywords" (5-12 kata kunci relevan) yang dipisahkan oleh tanda koma, cocok untuk pencarian Canva.
                        
                        Balas WAJIB dalam format JSON murni TANPA markdown block.
                        Formatnya harus: {{"title": "Judul Disini", "keywords": "kata1, kata2, kata3"}}
                        """
                        
                        response_text = ""
                        
                        # -- PROSES GAMBAR --
                        if file_ext in ['png', 'jpg', 'jpeg', 'webp']:
                            img = Image.open(file)
                            response = model.generate_content([prompt, img])
                            response_text = response.text
                            
                        # -- PROSES VIDEO (Ekstrak 1 Frame) --
                        elif file_ext in ['mp4', 'mov', 'avi']:
                            # Simpan sementara di memori/disk
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                                tmp.write(file.read())
                                tmp_path = tmp.name
                                
                            cap = cv2.VideoCapture(tmp_path)
                            ret, frame = cap.read()
                            cap.release()
                            os.remove(tmp_path)
                            
                            if ret:
                                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(frame_rgb)
                                response = model.generate_content([prompt, img])
                                response_text = response.text
                            else:
                                raise Exception("Gagal membaca frame video.")
                                
                        # -- PROSES SVG (Teks) --
                        elif file_ext == 'svg':
                            svg_content = file.read().decode('utf-8')
                            # Batasi 5000 karakter agar token tidak meledak jika SVG rumit
                            prompt_svg = f"{prompt}\n\nBerikut adalah kodenya (visualisasikan bentuknya dari kode):\n{svg_content[:5000]}"
                            response = model.generate_content(prompt_svg)
                            response_text = response.text
                            
                        # Bersihkan balasan JSON
                        cleaned_json = response_text.replace("```json", "").replace("```", "").strip()
                        
                        try:
                            parsed = json.loads(cleaned_json)
                            title = parsed.get("title", file.name)
                            keywords = parsed.get("keywords", "canva, design")
                        except:
                            # Jika Gemini gagal menjawab dengan format JSON murni
                            title = file.name
                            keywords = "error_parsing, " + file_ext
                            
                        ai_data.append({
                            "filename": file.name,
                            "title": title,
                            "keywords": keywords
                        })
                        
                    except Exception as ex:
                        st.error(f"Gagal memproses {file.name}: {ex}")
                        ai_data.append({
                            "filename": file.name,
                            "title": f"ERROR: {file.name}",
                            "keywords": "error"
                        })
                    
                    # Update progress bar
                    progress = (idx + 1) / len(uploaded_files)
                    my_bar.progress(progress, text=f"Diproses: {file.name}")
                
                my_bar.empty()
                st.success("✅ Pemrosesan AI Selesai!")
                
                # Tampilkan tabel preview
                df_ai = pd.DataFrame(ai_data)
                st.dataframe(df_ai, use_container_width=True)
                
                csv_ai = df_ai.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV (Hasil AI)",
                    data=csv_ai,
                    file_name="canva_ai_upload.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"Gagal melakukan koneksi AI: {e}. Periksa kembali API Key Anda.")

st.markdown("---")
st.caption("Universal - Ready for Cloud | Keamanan Terjamin: API Key TIDAK disimpan di sistem, aman 100%.")
