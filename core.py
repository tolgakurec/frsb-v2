import os
import io
import re
import json
import time
import base64
import gc
import uuid
import urllib.request
import urllib.parse
import urllib.error
import concurrent.futures
from datetime import datetime
from PIL import Image, ImageOps
import streamlit as st

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSHEETS_INSTALLED = True
except ImportError:
    GSHEETS_INSTALLED = False

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

SHEET_ID = "1Ec0v2Oo-7BlILvb35TGgo5j-SOGivJwmf5xpF85oGoU"

LANGUAGES = {
    "tr": {"name": "Türkçe", "flag": "🇹🇷"},
    "en": {"name": "English", "flag": "🇬🇧"},
    "bg": {"name": "Български", "flag": "🇧🇬"}
}

UI_TRANSLATIONS = {
    "tr": {
        "title": "📚 Fransızca Hikaye Kütüphanesi",
        "subtitle": "Timuçin ve Teoman İçin İnteraktif Fransızca Okuma Dünyası",
        "created_by": "Tolga Küreç tarafından Timuçin ve Teoman için hazırlanmıştır",
        "email_label": "Aile E-posta Adresiniz:",
        "pin_label": "Yönetici PIN Kodu:",
        "login_btn": "Giriş Yap",
        "email_warn": "Lütfen geçerli bir e-posta adresi girin.",
        "pin_warn": "Hatalı Yönetici PIN kodu!",
        "logout": "🚪 Çıkış",
        "lib_title": "📖 Görsel Kitaplık Rafı",
        "add_tab": "➕ Yeni Kitap Yükle (Gemini Vision)",
        "empty_lib": "Kütüphanede henüz kitap bulunmuyor.",
        "open_read": "🚀 Oku",
        "edit_book": "✏️ Düzenle",
        "delete_book": "🗑️ Sil",
        "save_changes": "💾 Değişiklikleri Kaydet",
        "save_and_read": "🚀 Kaydet & Oku",
        "exit_editor": "✕ Kapat",
        "split_page_btn": "✂️ Çift Sayfayı Böl",
        "merge_page_btn": "🔗 Sonrakiyle Birleştir",
        "rescan_page_btn": "✨ Gemini ile Yeniden Tara",
        "ocr_processing": "Kitap hazırlanıyor...",
        "zen_close": "✕ Kapat",
        "zen_page": "Sayfa",
        "zen_listen": "Dinle",
        "zen_stop": "Durdur",
        "zen_page_trans": "Sayfa Çevirisi",
        "zen_loading_trans": "Çeviri hazırlanıyor...",
        "zen_quiz": "Mini Quiz",
        "zen_rec": "Sesim",
        "word_bank_title": "🎒 Kelime Kumbaram",
        "badges_title": "🏅 Okuma Rozetlerim"
    },
    "en": {
        "title": "📚 French Storybook Library",
        "subtitle": "Interactive French Reading World for Timuçin & Teoman",
        "created_by": "Created by Tolga Küreç for Timuçin & Teoman",
        "email_label": "Family Email Address:",
        "pin_label": "Admin PIN Code:",
        "login_btn": "Sign In",
        "email_warn": "Please enter a valid email address.",
        "pin_warn": "Invalid Admin PIN code!",
        "logout": "🚪 Sign Out",
        "lib_title": "📖 Visual Bookshelf",
        "add_tab": "➕ Upload New Book (Gemini Vision)",
        "empty_lib": "No books in the library yet.",
        "open_read": "🚀 Read",
        "edit_book": "✏️ Edit",
        "delete_book": "🗑️ Delete",
        "save_changes": "💾 Save Changes",
        "save_and_read": "🚀 Save & Read",
        "exit_editor": "✕ Close",
        "split_page_btn": "✂️ Split Double Page",
        "merge_page_btn": "🔗 Merge Next",
        "rescan_page_btn": "✨ Re-scan with Gemini",
        "ocr_processing": "Preparing book...",
        "zen_close": "✕ Close",
        "zen_page": "Page",
        "zen_listen": "Listen",
        "zen_stop": "Stop",
        "zen_page_trans": "Translation",
        "zen_loading_trans": "Preparing translation...",
        "zen_quiz": "Mini Quiz",
        "zen_rec": "My Voice",
        "word_bank_title": "🎒 My Word Bank",
        "badges_title": "🏅 Reading Badges"
    },
    "bg": {
        "title": "📚 Френска библиотека с приказки",
        "subtitle": "Интерактивен свят за четене на френски за Тимучин и Теоман",
        "created_by": "Създадено от Толга Кюреч за Тимучин и Теоман",
        "email_label": "Имейл адрес:",
        "pin_label": "Админ ПИН код:",
        "login_btn": "Вход",
        "email_warn": "Моля, въведете валиден имейл адрес.",
        "pin_warn": "Грешен админ ПИН код!",
        "logout": "🚪 Изход",
        "lib_title": "📖 Библиотека",
        "add_tab": "➕ Качи нова книга (Gemini Vision)",
        "empty_lib": "Все още няма книги в библиотеката.",
        "open_read": "🚀 Чети",
        "edit_book": "✏️ Редактирай",
        "delete_book": "🗑️ Изтрий",
        "save_changes": "💾 Запази",
        "save_and_read": "🚀 Запази и чети",
        "exit_editor": "✕ Затвори",
        "split_page_btn": "✂️ Раздели страницата",
        "merge_page_btn": "🔗 Обедини със следващата",
        "rescan_page_btn": "✨ Сканирай с Gemini",
        "ocr_processing": "Подготовка на книгата...",
        "zen_close": "✕ Затвори",
        "zen_page": "Страница",
        "zen_listen": "Слушай",
        "zen_stop": "Спри",
        "zen_page_trans": "Превод",
        "zen_loading_trans": "Подготвя се превод...",
        "zen_quiz": "Мини Куиз",
        "zen_rec": "Моят глас",
        "word_bank_title": "🎒 Моята касичка с думи",
        "badges_title": "🏅 Моите значки"
    }
}

def T(key):
    lang = st.session_state.get("app_lang", "tr")
    if lang not in UI_TRANSLATIONS:
        lang = "tr"
    return UI_TRANSLATIONS[lang].get(key, UI_TRANSLATIONS["tr"].get(key, key))

def sanitize_gemini_key(raw_key):
    if not raw_key:
        return ""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "", str(raw_key)).strip()

def get_active_gemini_key():
    if hasattr(st, "secrets"):
        for name in ["GEMINI_API_KEY", "gemini_api_key", "GEMINI_KEY"]:
            if name in st.secrets:
                val = sanitize_gemini_key(st.secrets[name])
                if val:
                    return val
    return None

def get_admin_pin():
    if hasattr(st, "secrets") and "ADMIN_PIN" in st.secrets:
        return str(st.secrets["ADMIN_PIN"]).strip()
    return "1923"

def get_gemini_endpoint(model_name="gemini-2.5-flash"):
    proto = "ht" + "tps" + "://"
    domain = "generativelanguage" + "." + "googleapis" + "." + "com"
    return f"{proto}{domain}/v1beta/models/{model_name}:generateContent"

def clean_private_key(key_str):
    if not key_str or not isinstance(key_str, str):
        return key_str
    return key_str.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n").strip()

def get_service_account_dict():
    creds_dict = None
    if hasattr(st, "secrets"):
        if "gcp_json" in st.secrets:
            raw = st.secrets["gcp_json"]
            creds_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
    if not creds_dict:
        for fname in ["google_secret.json", "secrets.json", "service_account.json"]:
            if os.path.exists(fname):
                try:
                    with open(fname, "r", encoding="utf-8") as f:
                        creds_dict = json.load(f)
                        break
                except Exception:
                    pass
    if creds_dict and "private_key" in creds_dict:
        creds_dict["private_key"] = clean_private_key(creds_dict["private_key"])
    return creds_dict

@st.cache_resource
def get_gsheet_client():
    if not GSHEETS_INSTALLED:
        return None, "gspread veya oauth2client eksik."
    creds_dict = get_service_account_dict()
    if not creds_dict:
        return None, "Google kimlik anahtarı bulunamadı!"
    try:
        scope = [
            "ht" + "tps://spreadsheets.google" + ".com/feeds",
            "ht" + "tps://www.googleapis" + ".com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client, None
    except Exception as e:
        return None, f"Yetkilendirme Hatası: {str(e)}"

def get_sheet(sheet_name):
    client, err = get_gsheet_client()
    if not client:
        return None, err
    try:
        doc = client.open_by_key(SHEET_ID)
        return doc.worksheet(sheet_name), None
    except Exception as e:
        return None, f"Google Sheets erişim hatası ({sheet_name}): {str(e)}"

def login_user(email, is_admin_attempt=False, pin_input=""):
    email = email.lower().strip()
    if is_admin_attempt:
        if pin_input.strip() != get_admin_pin():
            return False, None, T("pin_warn")
        return True, {"Email": email, "Role": "admin"}, "Yönetici girişi başarılı."
    if email == "tolgakurec@gmail.com":
        return True, {"Email": email, "Role": "family"}, "Aile girişi başarılı."
    sheet, _ = get_sheet("Users")
    if not sheet:
        return True, {"Email": email, "Role": "user"}, "Aile girişi."
    try:
        records = sheet.get_all_records()
        for r in records:
            if str(r.get("Email", "")).lower().strip() == email:
                return True, {"Email": email, "Role": "user"}, "Giriş başarılı."
        sheet.append_row([email, "user"])
        return True, {"Email": email, "Role": "user"}, "Kayıt edildi."
    except Exception:
        return True, {"Email": email, "Role": "user"}, "Giriş yapıldı."

def format_short_date(date_str):
    if not date_str:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(date_str).strip())
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return str(date_str).strip()[:10]

@st.cache_data(ttl=120, show_spinner=False)
def get_library_with_covers():
    lib_sheet, err1 = get_sheet("Library")
    if not lib_sheet:
        return [], err1
    try:
        records = lib_sheet.get_all_records()
        books_list, seen_ids = [], set()
        for idx, r in enumerate(records):
            b_id = str(r.get("BookID", "")).strip()
            if not b_id or b_id in seen_ids:
                continue
            seen_ids.add(b_id)
            date_val = ""
            for k, v in r.items():
                k_low = str(k).lower()
                if any(w in k_low for w in ["date", "tarih", "time", "created", "eklenme", "yukleme"]):
                    date_val = str(v).strip()
                    break
            if not date_val:
                vals = list(r.values())
                if len(vals) >= 3 and re.match(r"^\d{4}-\d{2}-\d{2}", str(vals[2]).strip()):
                    date_val = str(vals[2]).strip()
            books_list.append({
                "book_id": b_id,
                "title": r.get("BookName", "İsimsiz"),
                "page_count": r.get("PageCount", 0),
                "date": date_val,
                "row_idx": idx,
                "cover_b64": ""
            })
        books_list.sort(key=lambda x: (x["date"], x["row_idx"]), reverse=True)

        pages_sheet, _ = get_sheet("Pages")
        if pages_sheet and books_list:
            p_records = pages_sheet.get_all_records()
            cover_map = {}
            for pr in p_records:
                if int(pr.get("PageNo", 0)) == 1:
                    bid = str(pr.get("BookID", "")).strip()
                    if bid and bid not in cover_map:
                        cover_map[bid] = pr.get("ImageBase64", "")
            for b in books_list:
                b["cover_b64"] = cover_map.get(b["book_id"], "")
        return books_list, None
    except Exception as e:
        return [], str(e)

@st.cache_data(ttl=300, show_spinner=False)
def load_book_content(book_id):
    sheet, err = get_sheet("Pages")
    if not sheet:
        return None, err
    try:
        records = sheet.get_all_records()
        pages = []
        for r in records:
            if str(r.get("BookID", "")).strip() == str(book_id).strip():
                try:
                    boxes = json.loads(r.get("OCRText", "[]"))
                except Exception:
                    boxes = []
                pages.append({
                    "page_no": int(r.get("PageNo", 0)),
                    "img_b64": r.get("ImageBase64", ""),
                    "boxes": boxes
                })
        if not pages:
            return None, "Sayfa verisi bulunamadı."
        return sorted(pages, key=lambda x: x["page_no"]), None
    except Exception as e:
        return None, str(e)

def save_hybrid_book(title, pages, old_book_id=None):
    lib_sheet, _ = get_sheet("Library")
    pages_sheet, _ = get_sheet("Pages")
    if not lib_sheet or not pages_sheet:
        return None, "Google Sheets veritabanına bağlanılamadı."
    try:
        if old_book_id:
            book_id = old_book_id
            for i, r in enumerate(lib_sheet.get_all_records()):
                if str(r.get("BookID", "")).strip() == str(book_id).strip():
                    lib_sheet.delete_rows(i + 2)
                    break
            page_records = pages_sheet.get_all_records()
            rows_to_del = [i + 2 for i, r in enumerate(page_records) if str(r.get("BookID", "")).strip() == str(book_id).strip()]
            for row_idx in reversed(rows_to_del):
                pages_sheet.delete_rows(row_idx)
                time.sleep(0.1)
        else:
            book_id = str(uuid.uuid4())[:8]

        lib_sheet.append_row([book_id, title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(pages)])
        all_page_rows = [
            [book_id, idx + 1, page["img_b64"], json.dumps(page["boxes"], ensure_ascii=False)]
            for idx, page in enumerate(pages)
        ]
        for i in range(0, len(all_page_rows), 10):
            pages_sheet.append_rows(all_page_rows[i:i + 10])
            time.sleep(0.4)

        get_library_with_covers.clear()
        load_book_content.clear()
        return book_id, "Kitap başarıyla kaydedildi!"
    except Exception as e:
        return None, str(e)

def delete_hybrid_book(book_id):
    lib_sheet, _ = get_sheet("Library")
    pages_sheet, _ = get_sheet("Pages")
    if lib_sheet:
        for i, r in enumerate(lib_sheet.get_all_records()):
            if str(r.get("BookID", "")).strip() == str(book_id).strip():
                lib_sheet.delete_rows(i + 2)
                break
    if pages_sheet:
        rows_to_delete = [i + 2 for i, r in enumerate(pages_sheet.get_all_records()) if str(r.get("BookID", "")).strip() == str(book_id).strip()]
        for row_idx in reversed(rows_to_delete):
            pages_sheet.delete_rows(row_idx)
            time.sleep(0.1)
    get_library_with_covers.clear()
    load_book_content.clear()

def clean_word_key(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", text).strip().lower())

def tokenize_french_line(text):
    raw_tokens = [t for t in text.split() if t]
    merged = []
    for tok in raw_tokens:
        if merged and re.fullmatch(r"[!?;:.,…»”)]+", tok):
            merged[-1] = merged[-1] + " " + tok
        else:
            merged.append(tok)
    return merged

def split_phrase_boxes_to_words(raw_boxes):
    word_boxes = []
    for b in raw_boxes:
        text = str(b.get("text", "")).strip()
        if not text:
            continue
        left = float(b.get("left", 5.0))
        top = float(b.get("top", 5.0))
        width = float(b.get("width", 30.0))
        height = float(b.get("height", 8.0))

        tr_full = str(b.get("tr", "")).strip()
        en_full = str(b.get("en", "")).strip()
        bg_full = str(b.get("bg", "")).strip()
        word_map = b.get("words", {}) if isinstance(b.get("words"), dict) else {}

        tokens = tokenize_french_line(text)
        if len(tokens) <= 1:
            clean_k = clean_word_key(text)
            w_info = word_map.get(clean_k, {}) if isinstance(word_map.get(clean_k), dict) else {}
            word_boxes.append({
                "id": f"b_{len(word_boxes)}",
                "text": text,
                "clean": clean_k,
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(max(width, 2.0), 2),
                "height": round(max(height, 2.5), 2),
                "tr": w_info.get("tr") or tr_full,
                "en": w_info.get("en") or en_full,
                "bg": w_info.get("bg") or bg_full,
                "line_tr": tr_full,
                "line_en": en_full,
                "line_bg": bg_full
            })
        else:
            total_chars = sum(len(t) for t in tokens) + (len(tokens) - 1) * 0.6
            curr_left = left
            for tok in tokens:
                tok_ratio = len(tok) / max(total_chars, 1.0)
                space_ratio = 0.6 / max(total_chars, 1.0)
                tok_w = width * tok_ratio
                clean_k = clean_word_key(tok)
                w_info = word_map.get(clean_k, {}) if isinstance(word_map.get(clean_k), dict) else {}
                word_boxes.append({
                    "id": f"b_{len(word_boxes)}",
                    "text": tok,
                    "clean": clean_k,
                    "left": round(curr_left, 2),
                    "top": round(top, 2),
                    "width": round(max(tok_w, 1.8), 2),
                    "height": round(max(height, 2.5), 2),
                    "tr": w_info.get("tr") or tr_full,
                    "en": w_info.get("en") or en_full,
                    "bg": w_info.get("bg") or bg_full,
                    "line_tr": tr_full,
                    "line_en": en_full,
                    "line_bg": bg_full
                })
                curr_left += tok_w + (width * space_ratio)
    return word_boxes

def encode_image_single_pass(img_fixed):
    img_s = img_fixed.copy()
    img_s.thumbnail((850, 1100), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_s.save(buf, format="JPEG", quality=55)
    raw_bytes = buf.getvalue()
    if len(raw_bytes) > 35000:
        buf = io.BytesIO()
        img_s.save(buf, format="JPEG", quality=38)
        raw_bytes = buf.getvalue()
    b64 = base64.b64encode(raw_bytes).decode("utf-8")
    del img_s, buf
    return b64

def call_gemini_vision_oneshot(base64_image, api_key):
    clean_key = sanitize_gemini_key(api_key)
    if not clean_key:
        return None, "GEMINI_API_KEY bulunamadı! Streamlit Secrets ayarlarını kontrol edin."

    prompt = (
        "You are an expert OCR and translation engine for French children's picture books. "
        "Read all visible French text in this image with 100% precision, including cursive handwriting (écriture cursive). "
        "Return STRICTLY a JSON array of objects (no markdown, no backticks) sorted top-to-bottom. "
        "Each object represents one line or distinct phrase and must have:\n"
        "- 'text': Exact French text with accents and punctuation.\n"
        "- 'left': Float percentage (0-100) from left edge.\n"
        "- 'top': Float percentage (0-100) from top edge.\n"
        "- 'width': Float percentage (0-100) width.\n"
        "- 'height': Float percentage (0-100) height.\n"
        "- 'tr': Natural Turkish translation of this line.\n"
        "- 'en': Natural English translation of this line.\n"
        "- 'bg': Natural Bulgarian translation of this line.\n"
        "- 'words': An object mapping each lowercase French word (without punctuation) in this line to "
        "{'tr': 'Turkish meaning', 'en': 'English meaning', 'bg': 'Bulgarian meaning'}."
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    req_data = json.dumps(payload).encode("utf-8")
    last_error = "Bilinmeyen API hatası"

    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        url = get_gemini_endpoint(model_name)
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": clean_key,
                "User-Agent": "Mozilla/5.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=28) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = "Gemini boş yanıt döndürdü."
                    continue
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "[]").strip()
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text).strip()
                parsed = json.loads(raw_text)
                items = parsed if isinstance(parsed, list) else []
                if isinstance(parsed, dict):
                    for v in parsed.values():
                        if isinstance(v, list):
                            items = v
                            break
                if items:
                    word_boxes = split_phrase_boxes_to_words(items)
                    return word_boxes, None
                return [], None
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8", errors="ignore")
            last_error = f"{model_name} HTTP {he.code}: {err_msg[:160]}"
        except Exception as e:
            last_error = f"{model_name} Bağlantı Hatası: {str(e)}"

    return None, last_error

def process_single_image(img):
    img_fixed = ImageOps.exif_transpose(img).convert("RGB")
    img_c = img_fixed.copy()
    img_c.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_c.save(buf, format="JPEG", quality=80)
    b64_gemini = base64.b64encode(buf.getvalue()).decode("utf-8")
    del img_c, buf

    gemini_key = get_active_gemini_key()
    boxes, err = call_gemini_vision_oneshot(b64_gemini, gemini_key)
    if boxes is None:
        boxes = []

    final_b64 = encode_image_single_pass(img_fixed)
    del img_fixed
    gc.collect()
    return {"img_b64": final_b64, "boxes": boxes}, err

def merge_two_pages(page1, page2):
    im1 = Image.open(io.BytesIO(base64.b64decode(page1["img_b64"]))).convert("RGB")
    im2 = Image.open(io.BytesIO(base64.b64decode(page2["img_b64"]))).convert("RGB")
    target_h = max(im1.height, im2.height)
    if im1.height != target_h:
        im1 = im1.resize((int(im1.width * (target_h / im1.height)), target_h), Image.Resampling.LANCZOS)
    if im2.height != target_h:
        im2 = im2.resize((int(im2.width * (target_h / im2.height)), target_h), Image.Resampling.LANCZOS)
    merged_img = Image.new("RGB", (im1.width + im2.width, target_h), (255, 255, 255))
    merged_img.paste(im1, (0, 0))
    merged_img.paste(im2, (im1.width, 0))
    new_obj, _ = process_single_image(merged_img)
    del im1, im2, merged_img
    gc.collect()
    return new_obj

def translate_legacy_page_via_gemini(boxes, target_lang):
    api_key = get_active_gemini_key()
    words = [b.get("text", "").strip() for b in boxes if b.get("text", "").strip()]
    if not words:
        return "", {}
    full_fr = " ".join(words)
    if target_lang == "fr" or not api_key:
        return full_fr, {}

    lang_name = {"tr": "Turkish", "en": "English", "bg": "Bulgarian"}.get(target_lang, "Turkish")
    prompt = (
        f"Translate the following French children's book page into natural {lang_name}, "
        f"and provide a word-by-word {lang_name} dictionary for the words. "
        f"Return STRICTLY JSON: {{\"full_trans\": \"...\", \"dict\": {{\"lowercase_word\": \"meaning\"}}}}.\n"
        f"French text: {full_fr}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}
    }
    url = get_gemini_endpoint("gemini-2.5-flash")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key, "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}").strip()
            parsed = json.loads(raw)
            return str(parsed.get("full_trans", full_fr)), parsed.get("dict", {})
    except Exception:
        return full_fr, {}

def _prepare_page_task(page, target_lang):
    boxes = page.get("boxes", [])
    for b in boxes:
        if "clean" not in b:
            b["clean"] = clean_word_key(b.get("text", ""))

    if target_lang == "fr":
        page["full_trans"] = " ".join([b.get("text", "") for b in boxes])
        page["dictionary"] = {}
        page["current_lang"] = "fr"
        return page

    has_precomputed = any(bool(b.get(target_lang)) for b in boxes)
    if has_precomputed:
        word_dict = {}
        line_translations = []
        seen_lines = set()
        line_key = f"line_{target_lang}"
        for b in boxes:
            ck = b.get("clean", "")
            val = str(b.get(target_lang, "")).strip()
            if ck and val:
                word_dict[ck] = val
            l_val = str(b.get(line_key) or val).strip()
            if l_val and l_val not in seen_lines:
                seen_lines.add(l_val)
                line_translations.append(l_val)
        page["dictionary"] = word_dict
        page["full_trans"] = " ".join(line_translations)
        page["current_lang"] = target_lang
        return page

    if page.get("current_lang") != target_lang or "full_trans" not in page:
        f_trans, w_dict = translate_legacy_page_via_gemini(boxes, target_lang)
        page["full_trans"] = f_trans
        page["dictionary"] = {clean_word_key(k): v for k, v in w_dict.items()}
        page["current_lang"] = target_lang
    return page

def ensure_reading_ready(pages, target_lang):
    if not pages:
        return pages
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_prepare_page_task, p, target_lang) for p in pages]
        concurrent.futures.wait(futures)
    return pages
