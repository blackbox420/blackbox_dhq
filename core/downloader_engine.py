import subprocess
import os
import threading
import queue
import logging
import re # Za detekciju tipa URL-a
from typing import Callable, Dict, Any
from . import settings_handler # Koristi postavke za neke yt-dlp opcije

logger = logging.getLogger(__name__)

YT_DLP_EXECUTABLE = "yt-dlp"
FFMPEG_EXECUTABLE = "ffmpeg" # Potreban za audio ekstrakciju i spajanje

# Detaljniji profili kvalitete
QUALITY_PROFILES = {
    "Video - Najbolji MP4": {
        "format_selector": "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "type": "video",
        "description": "Najbolja dostupna MP4 video kvaliteta s H.264 kodekom i AAC audiom."
    },
    "Video - 1080p MP4": {
        "format_selector": "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
        "type": "video",
        "description": "Do 1080p MP4 video (H.264) s AAC audiom."
    },
    "Video - 720p MP4": {
        "format_selector": "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "type": "video",
        "description": "Do 720p MP4 video (H.264) s AAC audiom."
    },
    "Audio - Najbolji MP3": {
        "format_selector": "bestaudio/best", # yt-dlp bira najbolji audio stream
        "type": "audio",
        "extract_audio_format": "mp3",
        "audio_quality": "0", # Najbolji VBR za MP3
        "description": "Najbolja dostupna audio kvaliteta, konvertirana u MP3."
    },
    "Audio - Najbolji M4A/AAC": {
        "format_selector": "bestaudio[ext=m4a]/bestaudio",
        "type": "audio",
        "extract_audio_format": "m4a", # Ili ostaviti da yt-dlp odluči, ali onda specificirati ekstenziju
        "description": "Najbolja dostupna audio kvaliteta u M4A (AAC) formatu."
    },
    "Općenito - Najbolje Moguće": { # Fallback ako ništa drugo ne odgovara
        "format_selector": "bestvideo*+bestaudio*/best",
        "type": "video", # Pretpostavljamo video ako nije specificirano
        "description": "Najbolji dostupni video i audio, bilo koji format (yt-dlp odlučuje)."
    }
}
# Ključevi za GUI Combobox
QUALITY_PROFILE_KEYS = list(QUALITY_PROFILES.keys())


def determine_content_type_and_suggest_quality(url: str) -> str:
    """
    Osnovna detekcija tipa sadržaja na osnovu URL-a i prijedlog profila kvalitete.
    """
    url_lower = url.lower()
    if "music.youtube.com" in url_lower or \
       "spotify.com" in url_lower or \
       re.search(r"\.(mp3|m4a|aac|ogg|opus|flac|wav)(\?|$)", url_lower): # Direktni audio linkovi
        return "Audio - Najbolji MP3"
    
    # googleusercontent.com/youtube.com/ - ovo je vjerojatno direktan video link
    if "googleusercontent.com/youtube.com" in url_lower or \
       "youtu.be" in url_lower or "youtube.com/watch" in url_lower or \
       re.search(r"\.(mp4|mkv|webm|mov|avi|flv)(\?|$)", url_lower): # Direktni video linkovi
        return "Video - 1080p MP4" # Default za video
        
    # Za općenite stranice (npr. thepornbang), default na video
    # Korisnik će moći promijeniti ako želi drugačije
    if "thepornbang.org" in url_lower : # Primjer eksplicitne stranice
         return "Video - Najbolji MP4"

    return settings_handler.load_settings().get("default_quality", QUALITY_PROFILE_KEYS[0])


class DownloadTask:
    # ... (isto kao prije, samo osiguraj da quality_profile_key odgovara novim ključevima)
    def __init__(self, url: str, quality_profile_key: str, output_dir: str, item_id: Any):
        self.url = url
        self.quality_profile_key = quality_profile_key
        self.output_dir = output_dir
        self.item_id = item_id
        self.status = "Čeka"
        self.progress_str = "0%" # Za prikaz u GUI
        self.progress_val = 0.0   # Za numeričke operacije
        self.final_filename = None
        self.error_message = None
        self.speed_str = ""
        self.eta_str = ""


class Downloader:
    # ... (većina __init__, add_to_queue, start_worker, stop_worker ista)
    def __init__(self, update_callback: Callable, max_concurrent_downloads: int = 1):
        self.download_queue = queue.Queue()
        self.active_downloads = 0
        self.max_concurrent_downloads = max_concurrent_downloads
        self.update_callback = update_callback
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.current_settings = settings_handler.load_settings() # Učitaj postavke

    def add_to_queue(self, task: DownloadTask): # Bez izmjena
        self.download_queue.put(task)
        task.status = "U redu"
        self.update_callback(task, "status_update")
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.start_worker()

    def start_worker(self): # Bez izmjena
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.current_settings = settings_handler.load_settings() # Osvježi postavke pri startu workera
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Download worker pokrenut.")

    def stop_worker(self): # Bez izmjena
        self.stop_event.set()
        while not self.download_queue.empty():
            try: self.download_queue.get_nowait()
            except queue.Empty: break
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Čekam da se download worker zaustavi...")
            self.worker_thread.join(timeout=5)
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Download worker se nije zaustavio u predviđenom vremenu.")
        else:
             logger.info("Download worker zaustavljen.")
        self.worker_thread = None


    def _process_queue(self): # Bez izmjena (logika je ista)
        while not self.stop_event.is_set():
            if self.active_downloads < self.max_concurrent_downloads:
                try:
                    task = self.download_queue.get(timeout=1)
                    self.active_downloads += 1
                    threading.Thread(target=self._execute_download, args=(task,), daemon=True).start()
                except queue.Empty:
                    if self.active_downloads == 0 and self.download_queue.empty():
                        logger.info("Red prazan, worker ide na spavanje.")
                        self.stop_worker()
                        break
                    continue
                except Exception as e:
                    logger.error(f"Greška u _process_queue: {e}")
                    self.active_downloads = max(0, self.active_downloads -1)
            else:
                self.stop_event.wait(timeout=1)

    def _execute_download(self, task: DownloadTask):
        try:
            task.status = "Priprema..."
            task.progress_str = "0%"
            task.progress_val = 0.0
            self.update_callback(task, "status_update")
            
            os.makedirs(task.output_dir, exist_ok=True)
            
            profile = QUALITY_PROFILES.get(task.quality_profile_key, QUALITY_PROFILES["Općenito - Najbolje Moguće"])
            
            command = [
                YT_DLP_EXECUTABLE,
                task.url,
                "--no-check-certificates",
                # "--ignore-config", # Može biti korisno, ali pažljivo
                "--no-mtime",
                "--output", os.path.join(task.output_dir, "%(title)s.%(ext)s"),
                "--format", profile["format_selector"],
                # Koristi --progress-template za detaljnije informacije
                # npr. "[download]  ETA 0:01:23 स्पीड 1.23MiB/s  10.5% of 100.00MiB"
                # yt-dlp ima kompleksan output za progress, parsiranje može biti izazovno.
                # Jednostavniji template za početak:
                "--progress-template", "download:%(progress._percent_str)s ETA:%(progress.eta)s Speed:%(progress.speed)s",
                # Za dohvaćanje imena fajla nakon obrade:
                # '--print', 'after_video:%(filepath)q', # q za quoted string, sigurno
                # Ili direktno ispisati filename:
                # '--print', 'filename', # Ispisuje samo sirovo ime, bez putanje
            ]

            if profile["type"] == "audio":
                command.extend([
                    "--extract-audio",
                    "--audio-format", profile.get("extract_audio_format", "mp3"),
                ])
                if "audio_quality" in profile: # Neki formati nemaju quality (npr. wav)
                     command.extend(["--audio-quality", profile["audio_quality"]])
                if self.current_settings.get("embed_thumbnail_audio", True):
                    command.append("--embed-thumbnail") # yt-dlp će pokušati naći thumbnail
                # Ukloni video-specifične format opcije ako postoje
                # (npr. --merge-output-format, iako za audio ovo obično nije problem)
            elif profile["type"] == "video":
                command.extend(["--merge-output-format", "mp4"]) # Osiguraj MP4 kontejner za video
                if self.current_settings.get("add_metadata_video", True):
                    command.append("--add-metadata")
            
            if self.current_settings.get("prefer_hw_acceleration", False):
                command.append("--prefer-ffmpeg-hw-dl") # Ako ffmpeg podržava

            logger.info(f"Pokrećem komandu za {task.url} ({task.quality_profile_key}): {' '.join(command)}")
            task.status = "Preuzimanje..."
            self.update_callback(task, "status_update")
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                       text=True, encoding='utf-8', errors='replace',
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            final_filepath_from_yt_dlp = None # Za --print after_video:%(filepath)q

            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line: continue
                logger.debug(f"yt-dlp out ({os.path.basename(task.url)}): {line}")
                self.update_callback(task, "log_message", line)

                # Parsiranje progresa, brzine, ETA
                # Primjer linije: "download: 10.5% ETA:0:01:23 Speed:1.23MiB/s"
                if line.startswith("download:"):
                    parts = line.split(" ")
                    try:
                        task.progress_str = parts[0].split(':')[1] # "10.5%"
                        task.progress_val = float(task.progress_str.replace('%','').strip())
                        if len(parts) > 1 and "ETA:" in parts[1]:
                            task.eta_str = parts[1].split(':')[1]
                        if len(parts) > 2 and "Speed:" in parts[2]:
                            task.speed_str = parts[2].split(':')[1]
                        self.update_callback(task, "progress_update")
                    except (IndexError, ValueError) as e_parse:
                        logger.warning(f"Nepoznat format progress linije: '{line}', greška: {e_parse}")
                # Parsiranje imena fajla ako koristimo --print after_video:%(filepath)q
                # (za sada ne koristimo, ali ostavljam logiku)
                # elif line.startswith("after_video:"):
                #     final_filepath_from_yt_dlp = line.split("after_video:", 1)[1].strip().strip('"')

            stdout, stderr = process.communicate()

            if stdout:
                for line_out in stdout.strip().splitlines():
                    logger.debug(f"yt-dlp stdout_rem ({task.url}): {line_out}")
                    self.update_callback(task, "log_message", line_out)
                    # Ako smo koristili '--print', 'filename', ime bi bilo ovdje
                    # if not final_filepath_from_yt_dlp and process.returncode == 0:
                    #     # Provjeri da li je linija samo ime fajla
                    #     potential_fn = line_out.strip()
                    #     # Ovo je vrlo gruba provjera, --print after_video je bolji
                    #     if not any(c in potential_fn for c in ['[', ']', ' ', ':']): 
                    #         final_filepath_from_yt_dlp = os.path.join(task.output_dir, potential_fn)


            if stderr:
                for line_err in stderr.strip().splitlines():
                    logger.error(f"yt-dlp stderr ({task.url}): {line_err}")
                    self.update_callback(task, "log_message", f"GREŠKA: {line_err}")

            if process.returncode == 0:
                task.status = "Završeno"
                task.progress_str = "100%"
                task.progress_val = 100.0
                task.speed_str = "" # Resetiraj brzinu/ETA
                task.eta_str = ""
                
                # Određivanje imena fajla - ovo je i dalje najteži dio
                # Ako smo koristili --print after_video:%(filepath)q, imamo ga
                if final_filepath_from_yt_dlp and os.path.exists(final_filepath_from_yt_dlp):
                    task.final_filename = final_filepath_from_yt_dlp
                else: # Pokušaj naći iz standardnog outputa yt-dlp-a
                     # yt-dlp obično ispisuje nešto poput:
                     # [download] Destination: My Video.mp4
                     # [Merger] Merging formats into "My Video.mp4"
                     # [ExtractAudio] Destination: My Audio.mp3
                     # Tražimo zadnju takvu liniju iz kombiniranog outputa
                     combined_output = stdout + "\n" + stderr 
                     destination_line_content = None
                     search_patterns = [
                         r"\[download\] Destination:\s*(.+)",
                         r"\[Merger\] Merging formats into\s*\"([^\"]+)\"",
                         r"\[ExtractAudio\] Destination:\s*(.+)",
                         r"\[ffmpeg\] Destination:\s*(.+)" # Ponekad ffmpeg ispisuje destinaciju
                     ]
                     for line_out in reversed(combined_output.splitlines()):
                         for pattern in search_patterns:
                             match = re.search(pattern, line_out)
                             if match:
                                 destination_line_content = match.group(1).strip()
                                 break
                         if destination_line_content:
                             break
                     
                     if destination_line_content:
                         # Osiguraj da je putanja relativna na output_dir ako nije već apsolutna
                         if not os.path.isabs(destination_line_content):
                             task.final_filename = os.path.join(task.output_dir, destination_line_content)
                         else: # yt-dlp je možda dao apsolutnu putanju
                             task.final_filename = destination_line_content
                         
                         if not os.path.exists(task.final_filename):
                             logger.warning(f"Detektirano ime fajla '{task.final_filename}' ne postoji. Provjeravam output direktorij.")
                             # Kao fallback, uzmi najnoviji fajl u direktoriju (nije idealno)
                             list_of_files = [os.path.join(task.output_dir, f) for f in os.listdir(task.output_dir)]
                             if list_of_files:
                                 latest_file = max(list_of_files, key=os.path.getctime)
                                 task.final_filename = latest_file # Pretpostavka
                                 logger.info(f"Fallback na najnoviji fajl: {task.final_filename}")
                             else:
                                 task.final_filename = None
                     else:
                         logger.warning(f"Nije bilo moguće automatski detektirati ime preuzetog fajla za {task.url}")
                         task.final_filename = None
                
                self.update_callback(task, "download_complete")
            else:
                task.status = "Greška"
                task.error_message = stderr.strip() if stderr else f"yt-dlp greška (kod: {process.returncode})"
                self.update_callback(task, "download_error")
        
        except FileNotFoundError:
             task.status = "Kritična Greška"
             task.error_message = f"{YT_DLP_EXECUTABLE} ili {FFMPEG_EXECUTABLE} (ako je potreban) nije pronađen."
             logger.critical(task.error_message)
             self.update_callback(task, "download_error")
        except Exception as e:
            task.status = "Greška Programa"
            task.error_message = str(e)
            logger.error(f"Neočekivana greška tijekom preuzimanja {task.url}: {e}", exc_info=True)
            self.update_callback(task, "download_error")
        finally:
            self.active_downloads -= 1
            # Zadnji update da se osigura da je sve u GUI-ju konzistentno
            if task.status not in ["Završeno", "Greška", "Kritična Greška", "Greška Programa"]:
                task.status = "Završeno s problemima" # Default ako nije eksplicitno postavljeno
            self.update_callback(task, "status_update")