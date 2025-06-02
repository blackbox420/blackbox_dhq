# core/downloader_engine.py
import subprocess
import os
import threading
import queue
import logging
import re
import time # Za jedinstvenije ID-eve taskova i sortiranje
from typing import Callable, Any, Dict # Dodan Dict
from . import settings_handler

logger = logging.getLogger(__name__)

YT_DLP_EXECUTABLE = "yt-dlp"
FFMPEG_EXECUTABLE = "ffmpeg"

QUALITY_PROFILES = {
    "Video - Najbolji MP4": {"format_selector": "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "type": "video", "description": "Najbolja MP4 (H.264) + AAC audio."},
    "Video - 1080p MP4": {"format_selector": "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]", "type": "video", "description": "Do 1080p MP4 (H.264) + AAC audio."},
    "Video - 720p MP4": {"format_selector": "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]", "type": "video", "description": "Do 720p MP4 (H.264) + AAC audio."},
    "Audio - Najbolji MP3": {"format_selector": "bestaudio/best", "type": "audio", "extract_audio_format": "mp3", "audio_quality": "0", "description": "Najbolji audio, konvertiran u MP3."},
    "Audio - Najbolji M4A/AAC": {"format_selector": "bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio", "type": "audio", "extract_audio_format": "m4a", "description": "Najbolji audio u M4A (AAC) formatu."},
    "Općenito - Najbolje Moguće": {"format_selector": "bestvideo*+bestaudio*/best", "type": "video", "description": "Najbolji video i audio, bilo koji format."}
}
QUALITY_PROFILE_KEYS = list(QUALITY_PROFILES.keys())

def determine_content_type_and_suggest_quality(url: str) -> str:
    url_lower = url.lower()
    if any(domain in url_lower for domain in ["spotify.com", "soundcloud.com", "deezer.com", "music.youtube.com"]): return "Audio - Najbolji MP3"
    if "youtube.com/watch?v=" in url_lower or "youtu.be/" in url_lower : return "Video - 1080p MP4" # Default za YouTube video
    if "music.youtube.com" in url_lower: return "Audio - Najbolji MP3" # Tvoj primjer
    if re.search(r"\.(mp3|m4a|aac|ogg|opus|flac|wav)(\?|$)", url_lower): return "Audio - Najbolji MP3"
    if "youtube.com" in url_lower: return "Video - 1080p MP4" # Tvoj primjer
    if re.search(r"\.(mp4|mkv|webm|mov|avi|flv)(\?|$)", url_lower): return "Video - 1080p MP4"
    if "thepornbang.org" in url_lower : return "Video - Najbolji MP4"
    # Fallback na default iz postavki ako nema specifičnog pravila
    return settings_handler.load_settings().get("default_quality", QUALITY_PROFILE_KEYS[0])

class DownloadTask:
    def __init__(self, url: str, quality_profile_key: str, output_dir: str, item_id: str):
        self.url = url
        self.quality_profile_key = quality_profile_key
        self.output_dir = output_dir
        self.item_id: str = item_id
        self.status: str = "Čeka"
        self.progress_str: str = "0.0%" # Precizniji prikaz
        self.progress_val: float = 0.0
        self.final_filename: str | None = None
        self.error_message: str | None = None
        self.speed_str: str = ""
        self.eta_str: str = ""
        self.process: subprocess.Popen | None = None
        self.added_time = time.time()

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
        self.all_tasks_map: Dict[str, DownloadTask] = {}

    def add_to_queue(self, task: DownloadTask):
        logger.info(f"Dodajem task u red: {task.item_id} - {task.url[:70]}...")
        self.all_tasks_map[task.item_id] = task
        self.download_queue.put(task)
        task.status = "U redu"
        self.update_callback(task, "status_update")
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.start_worker()

    def get_all_tasks_snapshot(self) -> list[DownloadTask]:
        # Vrati sortirano po vremenu dodavanja (najnoviji prvo) ili kako želiš
        return sorted(list(self.all_tasks_map.values()), key=lambda t: t.added_time, reverse=True)

    def remove_task_completely(self, task_item_id: str):
        if task_item_id in self.all_tasks_map:
            del self.all_tasks_map[task_item_id]
            logger.info(f"Task {task_item_id} potpuno uklonjen iz DownloadManagera.")
        if task_item_id in self.active_tasks:
             del self.active_tasks[task_item_id]
             # active_downloads_count se smanjuje u finally od _execute_download

    def start_worker(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            logger.info("Download worker je već aktivan.")
            return
        self.current_settings = settings_handler.load_settings()
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Download worker pokrenut.")
        if not self.download_queue.empty():
             status_task = DownloadTask("Red", "N/A", "", "status_q_info") # Dummy task
             status_task.status = f"{self.download_queue.qsize()} zadataka u redu..."
             self.update_callback(status_task, "general_status_update", status_task.status) # Novi tip callbacka


    def stop_worker(self):
        self.stop_event.set()
        logger.info("Zahtjev za zaustavljanje download workera...")
        active_task_ids = list(self.active_tasks.keys())
        for task_id in active_task_ids:
            self.cancel_task(task_id, by_system=True)
        
        # Isprazni red (taskovi će dobiti status otkazano)
        drained_tasks = []
        while not self.download_queue.empty():
            try: 
                task = self.download_queue.get_nowait()
                drained_tasks.append(task)
            except queue.Empty: break
        
        for task in drained_tasks:
             task.status = "Otkazano (gašenje)"
             self.update_callback(task, "status_update")
        
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Čekam da se download worker nit završi...")
            self.worker_thread.join(timeout=3) # Smanjen timeout
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Download worker se nije ugasio na vrijeme.")
        else:
             logger.info("Download worker nit uspješno zaustavljena.")
        self.worker_thread = None
        self.active_downloads_count = 0

    def cancel_task(self, task_item_id: str, by_system: bool = False):
         task = self.active_tasks.get(task_item_id)
         if task: # Ako je task aktivan (ima process)
             if task.process and task.process.poll() is None: # Ako proces postoji i radi
                 logger.info(f"Pokušavam otkazati aktivni task ID: {task_item_id} (PID: {task.process.pid})")
                 try:
                     task.process.terminate()
                     task.process.wait(timeout=1) 
                 except subprocess.TimeoutExpired:
                     logger.warning(f"Proces za task {task_item_id} SIGTERM timeout, šaljem SIGKILL.")
                     task.process.kill()
                 except Exception as e:
                     logger.error(f"Greška pri otkazivanju procesa za task {task_item_id}: {e}")
                 task.status = "Otkazivanje..." # Privremeni status dok se ne potvrdi
                 self.update_callback(task, "status_update")
             else: # Proces ne postoji ili je već završen
                 logger.info(f"Proces za task {task_item_id} nije aktivan ili ne postoji.")
             # Konačni status postavlja _execute_download finally blok ili ovaj dio
             final_status = "Otkazano (sistem)" if by_system else "Otkazano (korisnik)"
             task.status = final_status
             task.error_message = "Preuzimanje otkazano."
             self.update_callback(task, "download_error") # Koristi download_error za prikaz greške/otkazivanja
             if task_item_id in self.active_tasks: del self.active_tasks[task_item_id]
             # active_downloads_count se smanjuje u finally bloku _execute_download
             return True
         else: # Task nije aktivan, provjeri da li je u redu čekanja
             task_in_queue = self.all_tasks_map.get(task_item_id)
             if task_in_queue and task_in_queue.status in ["Čeka", "U redu"]:
                 # Ukloni iz queue.Queue (teško bez iteriranja cijelog reda)
                 # Najlakše je samo ažurirati status u all_tasks_map, a _process_queue će ga preskočiti
                 task_in_queue.status = "Otkazano" if not by_system else "Otkazano (sistem)"
                 self.update_callback(task_in_queue, "status_update")
                 logger.info(f"Task {task_item_id} označen kao otkazan u redu čekanja.")
                 return True
         logger.warning(f"Task {task_item_id} nije pronađen ili nije u stanju za otkazivanje.")
         return False

    def _process_queue(self):
        # ... (logika ostaje ista kao u prethodnom odgovoru) ...
        while not self.stop_event.is_set():
            if self.active_downloads_count < self.max_concurrent_downloads:
                try:
                    task = self.download_queue.get(block=True, timeout=1)
                    
                    if task.status.startswith("Otkazano"): # Ako je task već otkazan dok je bio u redu
                        logger.info(f"Preskačem otkazani task {task.item_id} iz reda.")
                        self.download_queue.task_done()
                        # Ažuriraj GUI da se osigura konačni status ako treba
                        self.update_callback(task, "status_update") 
                        continue

                    if task.item_id in self.active_tasks:
                        logger.warning(f"Task {task.item_id} je već aktivan, preskačem.")
                        self.download_queue.task_done()
                        continue

                    self.active_downloads_count += 1
                    self.active_tasks[task.item_id] = task
                    logger.info(f"Započinjem obradu taska: {task.item_id}")
                    threading.Thread(target=self._execute_download, args=(task,), daemon=True).start()
                    # download_queue.task_done() se poziva nakon što je thread startan
                    # ili čak nakon što _execute_download završi, ovisno o željenoj logici.
                    # Za sada, odmah nakon startanja niti:
                    self.download_queue.task_done()

                except queue.Empty:
                    if self.active_downloads_count == 0 and self.download_queue.empty():
                        logger.debug("Red prazan, worker čeka nove zadatke ili stop signal.")
                    continue 
                except Exception as e:
                    logger.error(f"Greška u _process_queue pri dohvaćanju taska: {e}", exc_info=True)
            else:
                self.stop_event.wait(timeout=0.5)
        logger.info("Download worker _process_queue petlja završena.")
        self.active_downloads_count = 0 # Osiguraj resetiranje ako petlja izađe


    def _execute_download(self, task: DownloadTask):
         # ... (Ostatak metode _execute_download ostaje isti kao u prethodnom odgovoru,
         # s logikom za parsiranje progresa, detekciju imena fajla, i pozivanje update_callback)
         # VAŽNO: Unutar finally bloka _execute_download, osiguraj da se uklanja iz self.active_tasks:
         #   finally:
         #       if task.item_id in self.active_tasks:
         #           del self.active_tasks[task.item_id]
         #       self.active_downloads_count = max(0, self.active_downloads_count - 1)
         #       task.process = None 
         #       # ... ostatak ...
         # --- KOD _execute_download PREUZET IZ PRETHODNOG ODGOVORA S MANJIM ISPRAVKAMA ---
         process_ref = None 
         try:
             task.status = "Priprema..."; task.progress_str = "0.0%"; task.progress_val = 0.0; task.speed_str = ""; task.eta_str = ""
             self.update_callback(task, "status_update")
             os.makedirs(task.output_dir, exist_ok=True)
             profile = QUALITY_PROFILES.get(task.quality_profile_key, QUALITY_PROFILES["Općenito - Najbolje Moguće"])
             
             command = [YT_DLP_EXECUTABLE, task.url, "--no-check-certificates", "--no-mtime", "--ignore-errors",
                        "--retries", "3", "--fragment-retries", "3",
                        "--output", os.path.join(task.output_dir, "%(title)s.%(id)s.%(ext)s"), # Dodaj ID da se izbjegnu konflikti imena
                        "--format", profile["format_selector"],
                        "--progress-template", "download-cli:%(progress._percent_str)s ETA:%(progress.eta)s Speed:%(progress.speed)s"]

             if profile["type"] == "audio":
                 command.extend(["--extract-audio", "--audio-format", profile.get("extract_audio_format", "mp3")])
                 if "audio_quality" in profile: command.extend(["--audio-quality", profile["audio_quality"]])
                 if self.current_settings.get("embed_thumbnail_audio", True): command.append("--embed-thumbnail")
                 # Ukloni --merge-output-format ako je samo audio
                 if "--merge-output-format" in command:
                     idx = command.index("--merge-output-format")
                     command.pop(idx); command.pop(idx) 
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
             task.process = process; process_ref = process
             final_filepath_detected = None

             for line in iter(process.stdout.readline, ''):
                 if self.stop_event.is_set() or task.status.startswith("Otkaz"):
                     logger.info(f"[{task.item_id}] Prekidam čitanje outputa (stop/otkaz). Status: {task.status}")
                     if process.poll() is None: process.terminate(); process.wait(timeout=0.5)
                     break
                 line = line.strip()
                 if not line: continue
                 logger.debug(f"[{task.item_id}] yt-dlp: {line}")
                 self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] {line}")

                 if line.startswith("download-cli:"):
                     match_progress = re.match(r"download-cli:\s*(?P<percent>[\d\.]+%).*ETA:(?P<eta>[^ ]+).*Speed:(?P<speed>[^ ]+)", line)
                     if match_progress:
                         pd = match_progress.groupdict()
                         task.progress_str = pd.get("percent", task.progress_str)
                         try: task.progress_val = float(task.progress_str.replace('%','').strip())
                         except ValueError: pass
                         task.eta_str = pd.get("eta", task.eta_str)
                         task.speed_str = pd.get("speed", task.speed_str)
                         self.update_callback(task, "progress_update")
                 
                 dest_match = re.search(r"\[(?:download|ffmpeg|ExtractAudio)\] Destination:\s*(.+)", line)
                 merge_match = re.search(r"\[Merger\] Merging formats into\s*\"([^\"]+)\"", line)
                 if dest_match: final_filepath_detected = dest_match.group(1).strip()
                 elif merge_match: final_filepath_detected = merge_match.group(1).strip()

             stdout_rem, stderr_rem = process.communicate()
             if stdout_rem:
                 for line_out in stdout_rem.strip().splitlines():
                     logger.debug(f"[{task.item_id}] yt-dlp stdout_rem: {line_out}")
                     self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] {line_out}")
                     dest_match = re.search(r"\[(?:download|ffmpeg|ExtractAudio)\] Destination:\s*(.+)", line_out); merge_match = re.search(r"\[Merger\] Merging formats into\s*\"([^\"]+)\"", line_out)
                     if dest_match: final_filepath_detected = dest_match.group(1).strip()
                     elif merge_match: final_filepath_detected = merge_match.group(1).strip()
             if stderr_rem:
                 for line_err in stderr_rem.strip().splitlines():
                     logger.error(f"[{task.item_id}] yt-dlp stderr_rem: {line_err}")
                     self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] GREŠKA: {line_err}")
             
             # Ako je task otkazan od strane korisnika ili sistema, status je već postavljen
             if task.status.startswith("Otkazano"):
                 logger.info(f"[{task.item_id}] Preuzimanje je već bilo označeno kao: {task.status}")
                 # error_message je postavljen u cancel_task
                 self.update_callback(task, "status_update") # Pošalji konačni otkazani status
                 return

             if process.returncode == 0:
                 task.status = "Završeno"; task.progress_str = "100%"; task.progress_val = 100.0; task.speed_str = ""; task.eta_str = ""
                 if final_filepath_detected:
                     task.final_filename = os.path.join(task.output_dir, os.path.basename(final_filepath_detected))
                     if not os.path.exists(task.final_filename): task.final_filename = None # Resetiraj ako ne postoji
                 if not task.final_filename: logger.warning(f"[{task.item_id}] Ime fajla nije detektirano.")
                 self.update_callback(task, "download_complete")
             else:
                 task.status = "Greška"; task.error_message = stderr_rem.strip() if stderr_rem else f"yt-dlp greška (kod: {process.returncode})"
                 self.update_callback(task, "download_error")
         
         except FileNotFoundError:
             task.status = "Kritična Greška"; task.error_message = f"{YT_DLP_EXECUTABLE} ili {FFMPEG_EXECUTABLE} nije pronađen."
             logger.critical(task.error_message); self.update_callback(task, "download_error")
         except Exception as e:
             task.status = "Greška Programa"; task.error_message = str(e)
             logger.error(f"[{task.item_id}] Neočekivana greška: {e}", exc_info=True); self.update_callback(task, "download_error")
         finally:
             if task.item_id in self.active_tasks: del self.active_tasks[task.item_id]
             self.active_downloads_count = max(0, self.active_downloads_count - 1)
             task.process = None 
             if task.status not in ["Završeno", "Greška", "Kritična Greška", "Greška Programa", "Otkazano", "Otkazano (sistem)", "Otkazivanje..."]:
                 task.status = "Završeno (?)"; logger.warning(f"Task {task.item_id} završen s nejasnim statusom.")
             self.update_callback(task, "status_update")
             logger.info(f"Obrada taska {task.item_id} završena sa statusom: {task.status}")
             if self.active_downloads_count == 0 and self.download_queue.empty() and not self.stop_event.is_set():
                 logger.info("Svi zadaci obrađeni, worker čeka.")
                 status_task = DownloadTask("Red", "N/A", "", "status_q_empty")
                 status_task.status = "Red je prazan."
                 self.update_callback(status_task, "general_status_update", status_task.status)