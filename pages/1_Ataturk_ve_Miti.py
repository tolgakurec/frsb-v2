import os
import json
import base64
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Sofya'da Kalan Gençlik - Atatürk & Miti",
    page_icon="🇹🇷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

STORY_PARAGRAPHS = [
    {
        "tr": "Sofya’da Kalan Gençlik: Bir İmparatorluğun İhtişamı ve Yarım Kalan Bir Aşk",
        "fr": "La Jeunesse laissée à Sofia : La splendeur d'un empire et un amour inachevé"
    },
    {
        "tr": "Yıl 1914. Balkan Savaşları'nın barut kokusu henüz dağılmamış, Avrupa'nın üzerinde yaklaşan Büyük Savaş'ın kara bulutları toplanırken, Sofya'nın soğuk sokakları o gece Askerî Kulüp'ten yükselen vals ezgileriyle ısınıyordu. 11 Mayıs gecesi, Bulgar Kralı Ferdinand'ın ev sahipliğinde düzenlenen bu görkemli maskeli balo, sıradan bir diplomatik davet değil; tarihin en zarif meydan okumalarından birine ve son nefese kadar unutulmayacak, kalpleri sızlatan bir aşka sahne olacaktı.",
        "fr": "L'année 1914. L'odeur de poudre des guerres balkaniques ne s'était pas encore dissipée et les sombres nuages de la Grande Guerre imminente s'amoncelaient sur l'Europe, tandis que les rues froides de Sofia étaient réchauffées par les airs de valse s'échappant du Club Militaire ce soir-là. Ce grand bal masqué, organisé par le roi Ferdinand de Bulgarie dans la nuit du 11 mai, n'était pas une simple invitation diplomatique ; il allait être le théâtre de l'un des défis les plus élégants de l'histoire et d'un amour déchirant qui ne serait jamais oublié jusqu'au dernier souffle."
    },
    {
        "tr": "Salonda Bir Yeniçeri Ağası",
        "fr": "Un Agha Janissaire dans le Salon"
    },
    {
        "tr": "Avrupalı diplomatlar, generaller ve elitler frakları, smokinleri ve şatafatlı elbiseleriyle salonu doldurmuşken, devasa kapılar ağır ağır açıldı. İçeriye adım atan adam, henüz 32 yaşında genç ve karizmatik bir Osmanlı Kurmay Yarbayı olan Mustafa Kemal'di. Ancak o gece üzerinde alışıldık bir üniforma yoktu. Balkan Savaşları'nda zedelenen milletinin gururunu ayağa kaldırmak istercesine, İstanbul'dan, Harbiye Askerî Müzesi'nden gizlice getirttiği orijinal bir Yeniçeri Ağası kıyafetiyle salona girmişti.",
        "fr": "Alors que les diplomates, les généraux et l'élite européenne remplissaient la salle avec leurs queues-de-pie, leurs smokings et leurs robes flamboyantes, les portes géantes s'ouvrirent lentement. L'homme qui y entra était Mustafa Kemal, un jeune et charismatique lieutenant-colonel d'état-major ottoman âgé de 32 ans à peine. Cependant, il ne portait pas d'uniforme habituel ce soir-là."
    },
    {
        "tr": "Mavi Tuna'nın Sularında Süzülen Bir Aşk: 'Bulgar Gülü' Miti",
        "fr": "Un amour planant sur les eaux du Danube bleu : Miti, la 'Rose Bulgare'"
    },
    {
        "tr": "Gecenin ilerleyen saatlerinde Johann Strauss'un 'Güzel Mavi Tuna' valsi çalmaya başladığında, Mustafa Kemal Bulgaristan’ın eski Savunma Bakanı General Kovaçev’in kızı Dimitrina Kovaçeva'ya, namıdiğer 'Miti'ye doğru ilerledi. İsviçre'de eğitim almış, yüksek kültürü ve eşsiz güzelliğiyle 'Bulgar Gülü' olarak anılan Miti ile Mustafa Kemal dansa kalktığında, Sofya sosyetesi için zaman adeta durdu.",
        "fr": "Plus tard dans la nuit, lorsque la valse du 'Beau Danube bleu' de Johann Strauss a commencé à jouer, Mustafa Kemal s'est avancé vers Dimitrina Kovacheva, fille de l'ancien ministre bulgare de la Défense, le général Kovachev, alias 'Miti'."
    },
    {
        "tr": "'Bir kız sevdim ataşeyken, vermediler. Gençliğimi bıraktım Sofya'da...'",
        "fr": "'J'ai aimé une fille quand j'étais attaché, ils ne me l'ont pas donnée. J'ai laissé ma jeunesse à Sofia...'"
    },
    {
        "tr": "Askerî Kulüp'teki o büyülü vals ve ölümsüz aşk, bugün tarihin sayfalarında sadece askeri bir dehanın değil; vatanı için en derin sevgisinden vazgeçmek zorunda kalan bir devin en insani, en hüzünlü hatırası olarak yankılanmaya devam ediyor.",
        "fr": "Cette valse magique au Club et cet amour immortel continuent de résonner aujourd'hui dans les pages de l'histoire, non seulement comme le souvenir d'un génie militaire, mais aussi comme le souvenir le plus humain et le plus triste d'un géant qui a dû renoncer à son amour le plus profond pour sa patrie."
    }
]

def get_file_b64(filename, mime_type):
    for p in [filename, os.path.join("..", filename)]:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return f"data:{mime_type};base64,{base64.b64encode(f.read()).decode('utf-8')}"
            except Exception:
                pass
    return ""

img_uri = get_file_b64("ataturk_miti.jpg", "image/jpeg") or get_file_b64("atatürk ve miti.jpg", "image/jpeg")
if not img_uri:
    img_uri = "ht" + "tps://upload.wikimedia" + ".org/wikipedia/commons/thumb/c/c5/Mustafa_Kemal_Atat%C3%BCrk_in_janissary_costume.jpg/440px-Mustafa_Kemal_Atat%C3%BCrk_in_janissary_costume.jpg"

audio_uri = get_file_b64("blue_danube.mp3", "audio/mp3")
if not audio_uri:
    audio_uri = "ht" + "tps://ia800501.us.archive" + ".org/33/items/TheBlueDanubeWaltz/TheBlueDanubeWaltz.mp3"

if st.button("⬅️ Kütüphaneye Dön"):
    st.switch_page("app.py")

story_json = json.dumps(STORY_PARAGRAPHS, ensure_ascii=False)

HTML_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 0; background: #080c14; color: #e2e8f0; font-family: 'Georgia', serif; display: flex; height: 88vh; overflow: hidden; border-radius: 14px; }}
        #col-photo {{ width: 30%; display: flex; align-items: center; justify-content: center; padding: 20px; background: #04060a; border-right: 1px dashed rgba(255,255,255,0.15); }}
        #col-photo img {{ max-width: 100%; max-height: 78vh; border-radius: 12px; box-shadow: 0 12px 35px rgba(0,0,0,0.8); }}
        #cols-wrap {{ width: 70%; display: flex; }}
        #col-fr, #col-tr {{ width: 50%; padding: 20px 24px; overflow-y: auto; }}
        #col-fr {{ border-right: 1px dashed rgba(255,255,255,0.15); }}
        .btn {{ width: 100%; padding: 10px; border-radius: 22px; background: rgba(251,191,36,0.15); color: #fbbf24; border: 1.5px solid #fbbf24; font-weight: bold; cursor: pointer; margin-bottom: 16px; }}
        .btn.active {{ background: #ef4444; border-color: #ef4444; color: #fff; }}
        .p-box {{ line-height: 1.8; margin-bottom: 16px; padding: 8px 12px; border-radius: 6px; }}
        .title-box {{ font-size: 1.25rem; font-weight: bold; color: #fbbf24; margin-bottom: 16px; padding: 8px 12px; }}
        .hl {{ background: rgba(250,204,21,0.28); border-left: 4px solid #facc15; color: #fff; }}
        #m-btn {{ position: fixed; bottom: 14px; left: 14px; background: rgba(15,23,42,0.85); color: #fbbf24; border: 1px solid rgba(255,255,255,0.2); padding: 6px 14px; border-radius: 20px; cursor: pointer; }}
    </style>
</head>
<body>
    <audio id="bgMusic" src="{audio_uri}" loop preload="auto"></audio>
    <button id="m-btn" onclick="toggleMusic()">🎵 Vals</button>
    <div id="col-photo"><img src="{img_uri}" alt="Atatürk"></div>
    <div id="cols-wrap">
        <div id="col-fr"><button class="btn" id="b-fr" onclick="toggleRead('fr')">🔊 Fransızca Dinle</button><div id="c-fr"></div></div>
        <div id="col-tr"><button class="btn" id="b-tr" onclick="toggleRead('tr')">🔊 Türkçe Dinle</button><div id="c-tr"></div></div>
    </div>
    <script>
        const data = {story_json};
        const music = document.getElementById("bgMusic");
        music.volume = 0.35;
        let frH = "", trH = "";
        data.forEach((p, i) => {{
            const cls = (i === 0 || i === 2 || i === 4) ? "title-box" : "p-box";
            frH += `<div class="${{cls}}" id="fr_${{i}}">${{p.fr}}</div>`;
            trH += `<div class="${{cls}}" id="tr_${{i}}">${{p.tr}}</div>`;
        }});
        document.getElementById("c-fr").innerHTML = frH;
        document.getElementById("c-tr").innerHTML = trH;

        function toggleMusic() {{ if (music.paused) music.play(); else music.pause(); }}
        let reading = false, curLang = "";
        function stopRead() {{
            reading = false; curLang = "";
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            document.getElementById("b-fr").classList.remove("active");
            document.getElementById("b-tr").classList.remove("active");
            document.querySelectorAll(".hl").forEach(e => e.classList.remove("hl"));
        }}
        function toggleRead(lang) {{
            if (reading && curLang === lang) {{ stopRead(); return; }}
            stopRead();
            if (!music.paused) music.pause();
            reading = true; curLang = lang;
            document.getElementById(lang === 'fr' ? "b-fr" : "b-tr").classList.add("active");
            step(0);
        }}
        function step(idx) {{
            if (!reading || idx >= data.length) {{ stopRead(); return; }}
            document.querySelectorAll(".hl").forEach(e => e.classList.remove("hl"));
            const fEl = document.getElementById("fr_" + idx);
            const tEl = document.getElementById("tr_" + idx);
            if (fEl) {{ fEl.classList.add("hl"); fEl.scrollIntoView({{ behavior: "smooth", block: "center" }}); }}
            if (tEl) {{ tEl.classList.add("hl"); tEl.scrollIntoView({{ behavior: "smooth", block: "center" }}); }}
            const u = new SpeechSynthesisUtterance(curLang === 'fr' ? data[idx].fr : data[idx].tr);
            u.lang = curLang === 'fr' ? 'fr-FR' : 'tr-TR';
            u.rate = 0.95;
            u.onend = () => {{ if (reading) step(idx + 1); }};
            u.onerror = () => {{ if (reading) step(idx + 1); }};
            window.speechSynthesis.speak(u);
        }}
    </script>
</body>
</html>
"""
components.html(HTML_PAGE, height=780, scrolling=False)
