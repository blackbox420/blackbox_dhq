# core/downloader_engine.py
import subprocess
import os
import threading
import queue
import logging
import re
import time # Za jedinstvenije ID-eve taskova
from typing import Callable, Any # Izbrisan Dict, Any jer DownloadTask nije Dict
from . import settings_handler

logger = logging.getLogger(__name__) # Koristi __name__ za logger specifičan za modul

YT_DLP_EXECUTABLE = "yt-dlp"
FFMPEG_EXECUTABLE = "ffmpeg"

QUALITY_PROFILES = {
    "Video - Najbolji MP4": {
        "format_selector": "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "type": "video", "description": "Najbolja MP4 (H.264) + AAC audio."
    },
    "Video - 1080p MP4": {
        "format_selector": "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
        "type": "video", "description": "Do 1080p MP4 (H.264) + AAC audio."
    },
    "Video - 720p MP4": {
        "format_selector": "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "type": "video", "description": "Do 720p MP4 (H.264) + AAC audio."
    },
    "Audio - Najbolji MP3": {
        "format_selector": "bestaudio/best", "type": "audio",
        "extract_audio_format": "mp3", "audio_quality": "0", # 0 za VBR najbolji
        "description": "Najbolji audio, konvertiran u MP3."
    },
    "Audio - Najbolji M4A/AAC": {
        "format_selector": "bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio", # Preferiraj m4a ili aac eksplicitno
        "type": "audio", "extract_audio_format": "m4a",
        "description": "Najbolji audio u M4A (AAC) formatu."
    },
    "Općenito - Najbolje Moguće": {
        "format_selector": "bestvideo*+bestaudio*/best", "type": "video",
        "description": "Najbolji video i audio, bilo koji format."
    }
}
QUALITY_PROFILE_KEYS = list(QUALITY_PROFILES.keys())

def determine_content_type_and_suggest_quality(url: str) -> str:
    # ... (ova funkcija ostaje ista kao prije) ...
    url_lower = url.lower()
    # Jednostavne provjere, mogu se proširiti
    if any(domain in url_lower for domain in ["spotify.com", "soundcloud.com", "deezer.com"]):
        return "Audio - Najbolji MP3"
    if "music.youtube.com" in url_lower:
        return "Audio - Najbolji MP3"
    if re.search(r"\.(mp3|m4a|aac|ogg|opus|flac|wav)(\?|$)", url_lower):
        return "Audio - Najbolji MP3"
    
    if "youtube.com/watch" in url_lower or "youtu.be/" in url_lower or \
       "vimeo.com/" in url_lower or \
       re.search(r"\.(mp4|mkv|webm|mov|avi|flv)(\?|$)", url_lower):
        return "Video - 1080p MP4"
    
    if "thepornbang.org" in url_lower: # Primjer
         return "Video - Najbolji MP4"

    return settings_handler.load_settings().get("default_quality", QUALITY_PROFILE_KEYS[0])


class DownloadTask:
    def __init__(self, url: str, quality_profile_key: str, output_dir: str, item_id: str):
        self.url = url
        self.quality_profile_key = quality_profile_key
        self.output_dir = output_dir
        self.item_id: str = item_id 
        self.status: str = "Čeka"
        self.progress_str: str = "0%"
        self.progress_val: float = 0.0
        self.final_filename: str | None = None
        self.error_message: str | None = None
        self.speed_str: str = ""
        self.eta_str: str = ""
        self.process: subprocess.Popen | None = None
        self.added_time = time.time() # Vrijeme dodavanja, za sortiranje ako treba

class Downloader:
    def __init__(self, update_callback: Callable, max_concurrent_downloads: int = 1):
        self.download_queue = queue.Queue()
        self.active_downloads_count = 0
        self.max_concurrent_downloads = max_concurrent_downloads
        self.update_callback = update_callback
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.current_settings = settings_handler.load_settings()
        self.active_tasks: Dict[str, DownloadTask] = {} 
        self.all_tasks_map: Dict[str, DownloadTask] = {} # <<<< NOVO: Rječnik za sve taskove (item_id -> Task)

    def add_to_queue(self, task: DownloadTask):
        logger.info(f"Dodajem task u red: {task.item_id} - {task.url[:50]}...")
        self.all_tasks_map[task.item_id] = task # <<<< NOVO: Dodaj u mapu svih taskova
        self.download_queue.put(task)
        task.status = "U redu" # Inicijalni status kad se doda u DM-ov red
        self.update_callback(task, "status_update")
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.start_worker()
    def get_all_tasks_snapshot(self) -> list[DownloadTask]: # <<<< NOVA METODA
        """Vraća listu svih poznatih zadataka (kopiju)."""
        return list(self.all_tasks_map.values())
    def remove_task_completely(self, task_item_id: str): # <<<< NOVA METODA
        """Uklanja task iz svih internih struktura (npr. nakon što ga korisnik obriše iz GUI-ja)."""
        if task_item_id in self.all_tasks_map:
            del self.all_tasks_map[task_item_id]
            logger.info(f"Task {task_item_id} potpuno uklonjen iz DownloadManagera.")
        if task_item_id in self.active_tasks: # Također ukloni iz aktivnih ako je tamo
             del self.active_tasks[task_item_id]

    def start_worker(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            logger.info("Download worker je već aktivan.")
            return
        self.current_settings = settings_handler.load_settings()
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Download worker pokrenut.")
        # Odmah pošalji statusnu poruku ako ima nešto u redu
        if not self.download_queue.empty():
             dummy_task_for_status = DownloadTask("Red", "N/A", "", "status_queue")
             dummy_task_for_status.status = f"{self.download_queue.qsize()} zadataka u redu..."
             self.update_callback(dummy_task_for_status, "status_update")


    def stop_worker(self): # Logika otkazivanja aktivnih taskova treba ovdje
        self.stop_event.set()
        logger.info("Zahtjev za zaustavljanje download workera...")
        
        # Otkaži sve aktivne taskove
        for task_id, task in list(self.active_tasks.items()): # Iteriraj preko kopije
            self.cancel_task(task_id, by_system=True) # Interno otkazivanje

        while not self.download_queue.empty():
            try: 
                task = self.download_queue.get_nowait()
                task.status = "Otkazano (gašenje)"
                self.update_callback(task, "status_update")
            except queue.Empty: break
        
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Čekam da se download worker nit završi...")
            self.worker_thread.join(timeout=5) # Daj mu vremena da završi
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Download worker se nije ugasio na vrijeme.")
        else:
             logger.info("Download worker nit uspješno zaustavljena.")
        self.worker_thread = None
        self.active_downloads_count = 0 # Resetiraj brojač

    def cancel_task(self, task_item_id: str, by_system: bool = False):
        task = self.active_tasks.get(task_item_id)
        if task and task.process:
            logger.info(f"Pokušavam otkazati task ID: {task_item_id} (PID: {task.process.pid})")
            try:
                task.process.terminate() # Pošalji SIGTERM
                task.process.wait(timeout=2) # Pričekaj malo da se ugasi
                logger.info(f"Proces za task {task_item_id} poslan SIGTERM.")
            except subprocess.TimeoutExpired:
                logger.warning(f"Proces za task {task_item_id} se nije ugasio nakon SIGTERM, šaljem SIGKILL.")
                task.process.kill() # Prisili gašenje
                logger.info(f"Proces za task {task_item_id} poslan SIGKILL.")
            except Exception as e:
                logger.error(f"Greška pri otkazivanju procesa za task {task_item_id}: {e}")
            
            task.status = "Otkazano" if not by_system else "Otkazano (sistem)"
            task.error_message = "Preuzimanje otkazano od strane korisnika." if not by_system else "Preuzimanje otkazano od strane sistema."
            self.update_callback(task, "download_error") # Koristi isti tip za ažuriranje GUI-ja
            if task_item_id in self.active_tasks:
                del self.active_tasks[task_item_id]
                self.active_downloads_count = max(0, self.active_downloads_count - 1)
            return True
        # Ako task nije aktivan ali je u redu čekanja
        elif not task:
             new_queue = queue.Queue()
             found_and_removed = False
             while not self.download_queue.empty():
                 t = self.download_queue.get_nowait()
                 if t.item_id == task_item_id:
                     t.status = "Otkazano" if not by_system else "Otkazano (sistem)"
                     self.update_callback(t, "status_update")
                     found_and_removed = True
                     logger.info(f"Task {task_item_id} uklonjen iz reda čekanja.")
                 else:
                     new_queue.put(t)
             self.download_queue = new_queue
             return found_and_removed
             
        logger.warning(f"Task {task_item_id} nije pronađen među aktivnima za otkazivanje.")
        return False


    def _process_queue(self):
        while not self.stop_event.is_set():
            if self.active_downloads_count < self.max_concurrent_downloads:
                try:
                    task = self.download_queue.get(block=True, timeout=1) # Blokiraj s timeoutom
                    if task.item_id in self.active_tasks: # Izbjegni duplo procesiranje ako je greškom ostao
                        logger.warning(f"Task {task.item_id} je već aktivan, preskačem.")
                        self.download_queue.task_done() # Obavezno pozvati
                        continue

                    self.active_downloads_count += 1
                    self.active_tasks[task.item_id] = task # Dodaj u mapu aktivnih
                    logger.info(f"Započinjem obradu taska: {task.item_id}")
                    threading.Thread(target=self._execute_download, args=(task,), daemon=True).start()
                    self.download_queue.task_done() # Označi da je task uzet iz reda
                except queue.Empty:
                    if self.active_downloads_count == 0 and self.download_queue.empty():
                        logger.info("Red prazan i nema aktivnih preuzimanja. Worker čeka nove zadatke ili stop signal.")
                        # Ne zaustavljaj workera automatski, neka čeka ili ga GUI gumb zaustavi.
                        # Ako želiš da se sam ugasi nakon nekog vremena neaktivnosti, to je druga logika.
                    continue 
                except Exception as e:
                    logger.error(f"Greška u _process_queue pri dohvaćanju taska: {e}", exc_info=True)
                    # active_downloads_count se smanjuje u finally bloku _execute_download
            else:
                # Čekaj da se oslobodi mjesto
                self.stop_event.wait(timeout=0.5) # Provjeravaj češće stop_event
        logger.info("Download worker _process_queue petlja završena.")


    def _execute_download(self, task: DownloadTask):
         # ... (većina logike za _execute_download ostaje ista kao u tvom uploadanom fajlu,
         # s fokusom na ispravno slanje callbackova) ...
         # Osiguraj da se self.active_tasks[task.item_id] i self.active_downloads_count
         # ispravno ažuriraju u finally bloku.
         
         # --- POČETAK _execute_download ---
         process_ref = None # Za čuvanje reference na subprocess
         try:
             task.status = "Priprema..."
             task.progress_str = "0%"
             task.progress_val = 0.0
             task.speed_str = ""
             task.eta_str = ""
             self.update_callback(task, "status_update")
             
             os.makedirs(task.output_dir, exist_ok=True)
             
             profile = QUALITY_PROFILES.get(task.quality_profile_key, QUALITY_PROFILES["Općenito - Najbolje Moguće"])
             
             command = [
                 YT_DLP_EXECUTABLE, task.url,
                 "--no-check-certificates", "--no-mtime", "--ignore-errors",
                 "--retries", "3", "--fragment-retries", "3",
                 "--output", os.path.join(task.output_dir, "%(title)s.%(ext)s"),
                 "--format", profile["format_selector"],
                 "--progress-template", "download-cli:%(progress._percent_str)s ETA:%(progress.eta)s Speed:%(progress.speed)s TotalBytes:%(progress.total_bytes)s DownloadedBytes:%(progress.downloaded_bytes)s",
                 # Dodajemo --print filename da lakše dohvatimo ime fajla
                 # '--print', 'filename', # Ovo ispisuje samo ime, ne putanju
                 # Ili još bolje za konačnu putanju NAKON SVIH OPERACIJA (merge, recode):
                 # '--print', 'after_video:%(filepath)q', # 'q' za quoted, apsolutna putanja
                 # Za sada, oslanjamo se na parsiranje outputa
             ]

             if profile["type"] == "audio":
                 command.extend(["--extract-audio", "--audio-format", profile.get("extract_audio_format", "mp3")])
                 if "audio_quality" in profile: command.extend(["--audio-quality", profile["audio_quality"]])
                 if self.current_settings.get("embed_thumbnail_audio", True): command.append("--embed-thumbnail")
             elif profile["type"] == "video":
                 command.extend(["--merge-output-format", "mp4"])
                 if self.current_settings.get("add_metadata_video", True): command.append("--add-metadata")
             
             if self.current_settings.get("prefer_hw_acceleration", False): command.append("--prefer-ffmpeg-hw-dl")

             logger.info(f"[{task.item_id}] Pokrećem: {' '.join(command)}")
             task.status = "Preuzimanje..."
             self.update_callback(task, "status_update")
             
             process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                        text=True, encoding='utf-8', errors='replace',
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
             task.process = process # Spremi referencu za otkazivanje
             process_ref = process # Lokalna referenca za finally blok ako task.process postane None

             final_filepath_detected = None

             for line in iter(process.stdout.readline, ''):
                 if self.stop_event.is_set() or (task.status == "Otkazivanje..." or task.status == "Otkazano"): # Provjera za otkazivanje
                     logger.info(f"[{task.item_id}] Prekidam čitanje outputa zbog zaustavljanja ili otkazivanja.")
                     if process.poll() is None: # Ako proces još radi
                         logger.info(f"[{task.item_id}] Proces još radi, pokušavam ga terminirati.")
                         process.terminate()
                         try:
                             process.wait(timeout=1)
                         except subprocess.TimeoutExpired:
                             process.kill()
                             logger.info(f"[{task.item_id}] Proces ubijen.")
                     break # Izlaz iz petlje čitanja outputa

                 line = line.strip()
                 if not line: continue
                 
                 logger.debug(f"[{task.item_id}] yt-dlp: {line}")
                 self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] {line}")

                 if line.startswith("download-cli:"): # Naš custom progress template
                     parts = line.split(" ")
                     try:
                         task.progress_str = parts[0].split(':')[1] 
                         task.progress_val = float(task.progress_str.replace('%','').strip())
                         task.eta_str = parts[1].split('ETA:')[1] if "ETA:" in parts[1] else ""
                         task.speed_str = parts[2].split('Speed:')[1] if "Speed:" in parts[2] else ""
                         self.update_callback(task, "progress_update")
                     except (IndexError, ValueError) as e_parse:
                         logger.warning(f"[{task.item_id}] Nepoznat format progress linije: '{line}', greška: {e_parse}")
                 
                 # Detekcija imena fajla iz outputa
                 dest_match = re.search(r"\[(?:download|ffmpeg|ExtractAudio)\] Destination:\s*(.+)", line)
                 merge_match = re.search(r"\[Merger\] Merging formats into\s*\"([^\"]+)\"", line)
                 if dest_match:
                     final_filepath_detected = dest_match.group(1).strip()
                 elif merge_match:
                     final_filepath_detected = merge_match.group(1).strip()

             # Čekaj da se proces završi i dohvati preostali output
             stdout, stderr = process.communicate() 
             if stdout:
                 for line_out in stdout.strip().splitlines():
                     logger.debug(f"[{task.item_id}] yt-dlp stdout_rem: {line_out}")
                     self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] {line_out}")
                     # Ponovna provjera za ime fajla iz preostalog outputa
                     dest_match = re.search(r"\[(?:download|ffmpeg|ExtractAudio)\] Destination:\s*(.+)", line_out)
                     merge_match = re.search(r"\[Merger\] Merging formats into\s*\"([^\"]+)\"", line_out)
                     if dest_match: final_filepath_detected = dest_match.group(1).strip()
                     elif merge_match: final_filepath_detected = merge_match.group(1).strip()
             if stderr:
                 for line_err in stderr.strip().splitlines():
                     logger.error(f"[{task.item_id}] yt-dlp stderr: {line_err}")
                     self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] GREŠKA: {line_err}")

             if task.status.startswith("Otkazano"): # Ako je već otkazan
                 logger.info(f"[{task.item_id}] Preuzimanje je već bilo označeno kao otkazano.")
                 # error_message je već postavljen u cancel_task
                 self.update_callback(task, "download_error" if "korisnik" in task.status else "status_update")
                 return # Ne idi na provjeru returncode-a

             if process.returncode == 0:
                 task.status = "Završeno"
                 task.progress_str = "100%"
                 task.progress_val = 100.0
                 task.speed_str = ""; task.eta_str = ""
                 if final_filepath_detected:
                     task.final_filename = os.path.join(task.output_dir, os.path.basename(final_filepath_detected))
                     if not os.path.exists(task.final_filename):
                          logger.warning(f"[{task.item_id}] Detektirano ime fajla '{task.final_filename}' ne postoji.")
                          task.final_filename = None # Resetiraj ako ne postoji
                 if not task.final_filename: # Ako nije detektirano, probaj naći najnoviji (manje pouzdano)
                     logger.warning(f"[{task.item_id}] Ime fajla nije eksplicitno detektirano, tražim najnoviji u {task.output_dir}")
                     # Implementiraj logiku za traženje najnovijeg fajla ako je potrebno
                 self.update_callback(task, "download_complete")
             else:
                 task.status = "Greška"
                 task.error_message = stderr.strip() if stderr else f"yt-dlp greška (kod: {process.returncode})"
                 self.update_callback(task, "download_error")
         
         except FileNotFoundError:
             task.status = "Kritična Greška"; task.error_message = f"{YT_DLP_EXECUTABLE} ili {FFMPEG_EXECUTABLE} nije pronađen."
             logger.critical(task.error_message)
             self.update_callback(task, "download_error")
         except Exception as e:
             task.status = "Greška Programa"; task.error_message = str(e)
             logger.error(f"[{task.item_id}] Neočekivana greška: {e}", exc_info=True)
             self.update_callback(task, "download_error")
         finally:
             if task.item_id in self.active_tasks:
                 del self.active_tasks[task.item_id]
             self.active_downloads_count = max(0, self.active_downloads_count - 1)
             task.process = None # Očisti referencu na proces
             
             # Osiguraj da se pošalje konačni status ako nije već Završeno ili Greška
             if task.status not in ["Završeno", "Greška", "Kritična Greška", "Greška Programa", "Otkazano", "Otkazano (sistem)"]:
                 task.status = "Završeno (?)"; logger.warning(f"Task {task.item_id} završen s nejasnim statusom.")
             
             self.update_callback(task, "status_update") # Konačni update
             logger.info(f"Obrada taska {task.item_id} završena sa statusom: {task.status}")
             
             # Ako je red prazan i nema aktivnih downloada, worker može ići na spavanje
             # ili čekati. start_worker() će ga ponovno pokrenuti ako treba.
             if self.active_downloads_count == 0 and self.download_queue.empty():
                 logger.info("Svi zadaci obrađeni, worker čeka.")
                 # Ne zaustavljaj workera ovdje, neka ostane aktivan za nove taskove.
                 # Gui gumb za start/stop će upravljati njegovim životnim ciklusom.