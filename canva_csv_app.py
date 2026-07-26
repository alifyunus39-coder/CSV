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
# HELPER EXPORT MULTI-FORMAT
# ==========================================
def generate_csv_by_format(df_base, format_name):
    """
    df_base minimal memiliki kolom: filename, title, keywords
    Fungsi ini akan mentransformasi ke format header masing-masing platform.
    """
    if format_name == "Canva":
        df = df_base[['filename', 'title', 'keywords']].copy()
        return df.to_csv(index=False)
    
    elif format_name == "Adobe Stock":
        df = df_base[['filename', 'title', 'keywords']].copy()
        df.columns = ['Filename', 'Title', 'Keywords']
        return df.to_csv(index=False)
        
    elif format_name == "Shutterstock":
        df = df_base[['filename', 'title', 'keywords']].copy()
        df.columns = ['filename', 'Description', 'Keywords']
        return df.to_csv(index=False)
        
    elif format_name == "Envato":
        df = pd.DataFrame()
        df['Filename*'] = df_base['filename']
        df['Title*'] = df_base['title']
        df['Description*'] = df_base['title']
        df['Keywords*'] = df_base['keywords']
        df['Category*'] = "Nature"
        df['Price: Single Use License ($USD)*'] = "$12.00"
        df['Price: Multi-use License ($USD)*'] = "$36.00"
        df['Recognisable people?*'] = "N"
        df['Recognisable buildings?*'] = "N"
        df['Releases'] = ""
        df['Is Motion Graphics?'] = ""
        df['AudioJungle Track (IDs)'] = ""
        df['Color'] = ""
        df['Pace'] = ""
        df['Movement'] = ""
        df['Composition'] = ""
        df['Setting'] = ""
        df['No. of People'] = ""
        df['Gender'] = ""
        df['Age'] = ""
        df['Ethnicity'] = ""
        df['Alpha Channel'] = ""
        df['Looped'] = ""
        df['Source Audio'] = ""
        return df.to_csv(index=False)
        
    elif format_name in ["iStock", "Pond5"]:
        df = pd.DataFrame()
        df['filename'] = df_base['filename']
        df['title'] = df_base['title']
        df['description'] = df_base['title']
        return df.to_csv(index=False)
        
    else:
        # Default fallback
        return df_base.to_csv(index=False)

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
    st.markdown("Ubah teks atau daftar nama file biasa menjadi format CSV Canva atau format microstock lainnya. Sangat cepat, tanpa AI.")
    
    export_formats = st.multiselect(
        "Pilih Format Export CSV:",
        options=["Canva", "Adobe Stock", "Shutterstock", "Envato", "iStock", "Pond5"],
        default=["Canva"],
        key="manual_formats"
    )
    
    raw_text = st.text_area("Tempel teks atau daftar nama file di sini...", height=250, key="manual_input")

    if st.button("🚀 Proses Teks", type="primary", key="btn_manual"):
        if not raw_text.strip():
            st.warning("Teks masih kosong. Silakan tempel teks terlebih dahulu.")
        elif not export_formats:
            st.warning("Silakan pilih minimal 1 format export.")
        else:
            try:
                # Deteksi jika sudah CSV
                if "," in raw_text and len(raw_text.split('\n')) > 1:
                    # Parse as CSV to build df_base
                    df_base = pd.read_csv(io.StringIO(raw_text))
                    # Ensure basic columns exist
                    if 'filename' not in df_base.columns:
                        df_base['filename'] = df_base.iloc[:, 0]
                    if 'title' not in df_base.columns:
                        df_base['title'] = df_base.iloc[:, 1] if len(df_base.columns) > 1 else df_base['filename']
                    if 'keywords' not in df_base.columns:
                        df_base['keywords'] = df_base.iloc[:, 2] if len(df_base.columns) > 2 else "canva, design"
                    
                    st.success("✓ CSV Terdeteksi! (Data diproses ulang untuk format yang dipilih)")
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
                    
                    df_base = pd.DataFrame(data)
                    st.success("✓ Berhasil Konversi Teks!")

                st.markdown("### 📥 Download Hasil")
                cols = st.columns(min(len(export_formats), 4))
                for i, fmt in enumerate(export_formats):
                    csv_data = generate_csv_by_format(df_base, fmt)
                    filename = f"{fmt.lower().replace(' ', '_')}_manual.csv"
                    with cols[i % 4]:
                        st.download_button(
                            label=f"Unduh {fmt}",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            key=f"dl_manual_{fmt}"
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
    
    with st.expander("🛠️ Cek Status API Key (Troubleshooting)"):
        if st.button("Cek Model Tersedia"):
            if not api_key:
                st.warning("Masukkan API key dulu.")
            else:
                try:
                    genai.configure(api_key=api_key)
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    st.success("Model yang tersedia untuk API Key Anda:")
                    st.write(models)
                except Exception as e:
                    st.error(f"Gagal mengecek: {e}")
                    
    export_formats_ai = st.multiselect(
        "Pilih Format Export CSV:",
        options=["Canva", "Adobe Stock", "Shutterstock", "Envato", "iStock", "Pond5"],
        default=["Canva"],
        key="ai_formats"
    )
    
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
        elif not export_formats_ai:
            st.warning("Silakan pilih minimal 1 format export.")
        else:
            try:
                # Inisialisasi Gemini
                genai.configure(api_key=api_key)
                # Siapkan kandidat model generasi terbaru yang didukung oleh API Key Anda
                models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.0-flash']
                
                ai_data = []
                my_bar = st.progress(0, text="Mempersiapkan...")
                
                for idx, file in enumerate(uploaded_files):
                    file_ext = file.name.split('.')[-1].lower()
                    
                    try:
                        # Prompt sistem yang disuruh membalas dalam format JSON
                        prompt = f"""
                        You are a Canva graphic design expert. Create metadata for this file: "{file.name}".
                        Your Task:
                        1. Provide a short "title" (3-8 words maximum) relevant to the image/video content. MUST BE IN ENGLISH. The title should describe dominant colors first, then form/shape. Use natural readable sentence-style title.
                        2. Provide "keywords" (Exactly 45-50 relevant keywords) separated by commas, suitable for Canva search. MUST BE IN ENGLISH.
                        
                        You MUST reply in pure JSON format WITHOUT any markdown blocks.
                        The format must be exactly like this: {{"title": "Title Here", "keywords": "word1, word2, word3"}}
                        """
                        
                        response_text = ""
                        
                        def try_generate(content):
                            last_err = None
                            for m_name in models_to_try:
                                try:
                                    model = genai.GenerativeModel(m_name)
                                    resp = model.generate_content(content)
                                    return resp.text
                                except Exception as e:
                                    last_err = e
                            raise Exception(f"Semua model gagal (termasuk fallback). Error terakhir: {last_err}")
                        
                        # -- PROSES GAMBAR --
                        if file_ext in ['png', 'jpg', 'jpeg', 'webp']:
                            img = Image.open(file)
                            # Perkecil gambar agar sangat ringan (maksimal 512x512 pixel)
                            # Ini akan mengubah gambar 3MB+ menjadi preview kecil hanya puluhan KB
                            img.thumbnail((512, 512))
                            
                            response_text = try_generate([prompt, img])
                            
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
                                response_text = try_generate([prompt, img])
                            else:
                                raise Exception("Gagal membaca frame video.")
                                
                        # -- PROSES SVG (Teks) --
                        elif file_ext == 'svg':
                            svg_content = file.read().decode('utf-8')
                            # Batasi 5000 karakter agar token tidak meledak jika SVG rumit
                            prompt_svg = f"{prompt}\n\nBerikut adalah kodenya (visualisasikan bentuknya dari kode):\n{svg_content[:5000]}"
                            response_text = try_generate(prompt_svg)
                            
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
                
                st.markdown("### 📥 Download Hasil AI")
                cols = st.columns(min(len(export_formats_ai), 4))
                for i, fmt in enumerate(export_formats_ai):
                    csv_data = generate_csv_by_format(df_ai, fmt)
                    filename = f"{fmt.lower().replace(' ', '_')}_ai.csv"
                    with cols[i % 4]:
                        st.download_button(
                            label=f"Unduh {fmt}",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            key=f"dl_ai_{fmt}"
                        )
                
            except Exception as e:
                st.error(f"Gagal melakukan koneksi AI: {e}. Periksa kembali API Key Anda.")

st.markdown("---")
st.caption("Universal - Ready for Cloud | Keamanan Terjamin: API Key TIDAK disimpan di sistem, aman 100%.")
