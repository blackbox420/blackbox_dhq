
# 🔥 BlackBox DHQ Phoenix

**BlackBox DHQ Phoenix** je napredni desktop alat razvijen u Pythonu, osmišljen za brzo i pouzdano preuzimanje video i audio sadržaja visoke kvalitete sa podrškom za višestruke poglede, korisničke licence, i modularni dizajn.

---

## 🚀 Karakteristike

- 🧩 **Modularna arhitektura** (razvoj u fazama po 25%)
- 🎛️ Višestruki pogledi: `Downloads`, `Queue`, `Settings`, `About`, itd.
- 🖼️ Elegantno i responzivno GUI sučelje korišćenjem `CustomTkinter`
- 📥 Integrisan **yt-dlp** za preuzimanje video/audio sadržaja u najboljem mogućem kvalitetu
- 🧠 Globalni kontekst aplikacije za deljenje stanja između modula
- 🔐 Sistem klijentske licence (simulacija)
- ⚙️ Panel za podešavanja sa trajnim čuvanjem korisničkih opcija
- 🌙 Light/Dark teme

---

## 📦 Tehnologije i biblioteke

- [Python 3.10+](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
- `os`, `threading`, `json`, `time`, `platform`, i druge standardne Python biblioteke

---

## 🛠️ Instalacija

1. Kloniraj repozitorij:
   ```bash
   git clone https://github.com/blackbox420/blackbox_dhq.git
   cd blackbox_dhq
   ```

2. Instaliraj zavisnosti:
   ```bash
   pip install -r requirements.txt
   ```

3. Pokreni aplikaciju:
   ```bash
   python main.py
   ```

📌 **Napomena:** Za punu funkcionalnost yt-dlp, obavezno instaliraj i [FFmpeg](https://ffmpeg.org/download.html) i dodaj ga u PATH.

---

## 📂 Struktura projekta

```
blackbox_dhq/
├── main.py
├── core/
│   ├── app_context.py
│   ├── downloader.py
│   ├── queue_handler.py
│   └── ...
├── views/
│   ├── downloads_view.py
│   ├── settings_view.py
│   └── ...
├── assets/
│   ├── icons/
│   └── styles/
├── config/
│   └── settings.json
└── README_phoenix.md
```

---

## 🧪 Status razvoja

✅ Faza 1: Osnovna arhitektura + yt-dlp integracija  
🔄 Faza 2: Višestruki pogledi + kontekst aplikacije  
🔜 Faza 3: Napredna kontrola zadataka i podešavanja  
🔜 Faza 4: Validacija licence + automatizacija ažuriranja  

---

## 🧠 Cilj projekta

Cilj **BlackBox DHQ Phoenix** je stvoriti moćnu, stabilnu i proširivu aplikaciju za preuzimanje multimedije, uz moderan i intuitivan korisnički interfejs, pogodnu i za početnike i za napredne korisnike.

---

## 📫 Kontakt

Za prijavu grešaka, sugestije ili saradnju:

- GitHub Issues
- Email: `blackbox420.dev@proton.me`

---

## ⚖️ Licenca

Ovaj projekat je pod [MIT licencom](LICENSE).

---
