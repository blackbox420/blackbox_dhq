# core/downloader_engine.py
import subprocess
import os
import threading
import queue
import logging
import re
import time
from typing import Callable, Any, Dict, List
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

def determine_content_type_and_suggest_quality(url: str) -> str: # Ostaje ista
    url_lower = url.lower()
    if any(domain in url_lower for domain in ["music.youtube.com", "spotify.com", "soundcloud.com", "deezer.com"]): return "Audio - Najbolji MP3"
    if re.search(r"\.(mp3|m4a|aac|ogg|opus|flac|wav)(\?|$)", url_lower): return "Audio - Najbolji MP3"
    if "youtube.com/watch" in url_lower or "youtu.be/" in url_lower or "vimeo.com/" in url_lower: return "Video - 1080p MP4"
    if re.search(r"\.(mp4|mkv|webm|mov|avi|flv)(\?|$)", url_lower): return "Video - 1080p MP4"
    if "thepornbang.org" in url_lower : return "Video - Najbolji MP4" # Tvoj primjer
    current_settings = settings_handler.load_settings()
    return current_settings.get("default_quality", QUALITY_PROFILE_KEYS[0])

class DownloadTask: # Ostaje ista
    def __init__(self, url: str, quality_profile_key: str, output_dir: str, item_id: str):
        self.url = url; self.quality_profile_key = quality_profile_key; self.output_dir = output_dir
        self.item_id: str = item_id; self.status: str = "Čeka"; self.progress_str: str = "0.0%"
        self.progress_val: float = 0.0; self.final_filename: str | None = None
        self.error_message: str | None = None; self.speed_str: str = ""; self.eta_str: str = ""
        self.process: subprocess.Popen | None = None; self.added_time = time.time()

class Downloader:
    def __init__(self, update_callback: Callable, max_concurrent_downloads: int = 1):
        self.download_queue = queue.Queue()
        self.active_downloads_count = 0
        self.max_concurrent_downloads = max_concurrent_downloads
        self.update_callback = update_callback
        self.stop_event = threading.Event() # Za zaustavljanje workera
        self.cancel_flags: Dict[str, threading.Event] = {} # Za otkazivanje pojedinačnih taskova
        self.worker_thread: threading.Thread | None = None
        self.current_settings = settings_handler.load_settings()
        self.active_tasks: Dict[str, DownloadTask] = {}
        self.all_tasks_map: Dict[str, DownloadTask] = {}

    def add_to_queue(self, task: DownloadTask):
        logger.info(f"Dodajem task u red: {task.item_id} - {task.url[:70]}...")
        self.all_tasks_map[task.item_id] = task
        self.cancel_flags[task.item_id] = threading.Event() # Kreiraj cancel flag za ovaj task
        self.download_queue.put(task)
        task.status = "U redu"
        self.update_callback(task, "status_update")
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.start_worker()

    def get_all_tasks_snapshot(self) -> List[DownloadTask]:
        return sorted(list(self.all_tasks_map.values()), key=lambda t: t.added_time, reverse=True)

    def remove_task_completely(self, task_item_id: str):
        if task_item_id in self.all_tasks_map: del self.all_tasks_map[task_item_id]
        if task_item_id in self.active_tasks: del self.active_tasks[task_item_id]
        if task_item_id in self.cancel_flags: del self.cancel_flags[task_item_id]
        logger.info(f"Task {task_item_id} potpuno uklonjen iz DownloadManagera.")
        # Ako je bio u queue.Queue, bit će preskočen u _process_queue ako više nije u all_tasks_map

    def start_worker(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            logger.info("Download worker je već aktivan."); return
        self.current_settings = settings_handler.load_settings(); self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start(); logger.info("Download worker pokrenut.")
        if not self.download_queue.empty():
             status_task = DownloadTask("Red", "N/A", "", f"status_q_info_{time.time()}"); status_task.status = f"{self.download_queue.qsize()} zadataka u redu..."
             self.update_callback(status_task, "general_status_update", status_task.status)

    def stop_worker(self):
        self.stop_event.set(); logger.info("Zahtjev za zaustavljanje SVIH preuzimanja...")
        for task_id in list(self.active_tasks.keys()): self.cancel_task(task_id, by_system=True)
        drained_tasks = []; _empty_queue_while_draining(self.download_queue, drained_tasks)
        for task in drained_tasks: task.status = "Otkazano (gašenje)"; self.update_callback(task, "status_update")
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Čekam da se download worker nit završi..."); self.worker_thread.join(timeout=2)
        logger.info("Download worker nit zaustavljena." if not (self.worker_thread and self.worker_thread.is_alive()) else "Download worker se nije ugasio na vrijeme.")
        self.worker_thread = None; self.active_downloads_count = 0

    def cancel_task(self, task_item_id: str, by_system: bool = False):
         task = self.all_tasks_map.get(task_item_id)
         if not task:
             logger.warning(f"Pokušaj otkazivanja nepostojećeg taska: {task_item_id}")
             return False

         logger.info(f"Zahtjev za otkazivanje taska: {task_item_id}, trenutni status: {task.status}")
         cancel_event = self.cancel_flags.get(task_item_id)
         if cancel_event:
             cancel_event.set() # Signaliziraj niti _execute_download da treba prekinuti

         if task.process and task.process.poll() is None: # Ako proces postoji i radi
             logger.info(f"Pokušavam terminirati proces za task {task_item_id} (PID: {task.process.pid})")
             try:
                 task.process.terminate()
                 task.process.wait(timeout=1) # Daj mu sekundu da se ugasi
                 logger.info(f"Proces za task {task_item_id} poslan SIGTERM.")
             except subprocess.TimeoutExpired:
                 logger.warning(f"Proces za task {task_item_id} SIGTERM timeout, šaljem SIGKILL.")
                 task.process.kill()
                 logger.info(f"Proces za task {task_item_id} poslan SIGKILL.")
             except Exception as e:
                 logger.error(f"Greška pri otkazivanju procesa za task {task_item_id}: {e}")
         
         task.status = "Otkazano (sistem)" if by_system else "Otkazano (korisnik)"
         task.error_message = "Preuzimanje otkazano."
         task.speed_str = ""; task.eta_str = "" # Očisti info o brzini/ETA
         self.update_callback(task, "download_error") # Javi GUI-ju (koristi error za bojenje)
         
         if task_item_id in self.active_tasks:
             del self.active_tasks[task_item_id]
             self.active_downloads_count = max(0, self.active_downloads_count - 1)
         
         # Ukloni iz queue.Queue ako je tamo
         _remove_task_from_queue_obj(self.download_queue, task_item_id)
         return True

    def _process_queue(self):
        while not self.stop_event.is_set():
            if self.active_downloads_count < self.max_concurrent_downloads:
                try:
                    task = self.download_queue.get(block=True, timeout=0.2) # Kraći timeout
                    
                    if task.item_id not in self.all_tasks_map or self.cancel_flags.get(task.item_id, threading.Event()).is_set():
                        logger.info(f"Preskačem task {task.item_id} jer je uklonjen ili već otkazan.")
                        self.download_queue.task_done(); continue
                    if task.item_id in self.active_tasks:
                        logger.warning(f"Task {task.item_id} je već aktivan, preskačem."); self.download_queue.task_done(); continue

                    self.active_downloads_count += 1; self.active_tasks[task.item_id] = task
                    logger.info(f"Započinjem obradu taska: {task.item_id} (aktivno: {self.active_downloads_count})")
                    threading.Thread(target=self._execute_download, args=(task,), daemon=True).start()
                    self.download_queue.task_done()
                except queue.Empty:
                    if self.active_downloads_count == 0 and self.download_queue.empty(): logger.debug("Red prazan, worker čeka.")
                except Exception as e: logger.error(f"Greška u _process_queue: {e}", exc_info=True)
            else: self.stop_event.wait(timeout=0.1) # Još kraći wait
        logger.info("Download worker _process_queue petlja završena."); self.active_downloads_count = 0

    def _execute_download(self, task: DownloadTask):
         cancel_flag_for_task = self.cancel_flags.get(task.item_id)
         try:
             if not cancel_flag_for_task or cancel_flag_for_task.is_set():
                 logger.info(f"[{task.item_id}] Preuzimanje preskočeno jer je već otkazano prije pokretanja.")
                 task.status = "Otkazano"; task.error_message = "Otkazano prije pokretanja."
                 self.update_callback(task, "download_error"); return

             task.status = "Priprema..."; task.progress_str = "0.0%"; task.progress_val = 0.0; task.speed_str = ""; task.eta_str = ""
             self.update_callback(task, "status_update")
             os.makedirs(task.output_dir, exist_ok=True)
             profile = QUALITY_PROFILES.get(task.quality_profile_key, QUALITY_PROFILES["Općenito - Najbolje Moguće"])
             
             command = [YT_DLP_EXECUTABLE, task.url, "--no-check-certificates", "--no-mtime", "--ignore-errors",
                        "--retries", "2", "--fragment-retries", "2",
                        "--output", os.path.join(task.output_dir, "%(title)s.%(ext)s"), # Jednostavnije ime, yt-dlp će paziti na duplikate
                        "--format", profile["format_selector"],
                        "--progress-template", "download-cli:%(progress._percent_str)s ETA:%(progress.eta)s Speed:%(progress.speed)s Filename:%(info.filename)s", # Dodajemo Filename
                        # Uklanjamo --print filepath jer ćemo parsirati iz progress template-a ili Destination linije
                        # "--no-simulate", "--dump-json" # Za napredno dohvaćanje info prije downloada
                        ]
             # Opcionalno: Dodaj User-Agent
             # command.extend(["--user-agent", "Mozilla/5.0 ..."])


             if profile["type"] == "audio":
                 command.extend(["--extract-audio", "--audio-format", profile.get("extract_audio_format", "mp3")])
                 if "audio_quality" in profile: command.extend(["--audio-quality", profile["audio_quality"]])
                 if self.current_settings.get("embed_thumbnail_audio", True): command.append("--embed-thumbnail")
                 # Ukloni --merge-output-format za audio
                 command = [arg for arg in command if arg not in ("--merge-output-format", "mp4")]
             elif profile["type"] == "video":
                 command.append("--merge-output-format"); command.append("mp4")
                 if self.current_settings.get("add_metadata_video", True): command.append("--add-metadata")
             
             if self.current_settings.get("prefer_hw_acceleration", False): command.append("--prefer-ffmpeg-hw-dl")

             logger.info(f"[{task.item_id}] Pokrećem: {' '.join(command)}")
             task.status = "Preuzimanje..."
             self.update_callback(task, "status_update")
             
             process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                        text=True, encoding='utf-8', errors='replace',
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
             task.process = process
             
             temp_final_filename = None # Privremena varijabla za ime fajla

             for line in iter(process.stdout.readline, ''):
                 if cancel_flag_for_task.is_set():
                     logger.info(f"[{task.item_id}] Detektiran signal za otkazivanje, prekidam proces.")
                     if process.poll() is None: process.terminate()
                     break 
                 line = line.strip()
                 if not line: continue
                 logger.debug(f"[{task.item_id}] yt-dlp: {line}")
                 self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] {line}")

                 if line.startswith("download-cli:"):
                     match_progress = re.match(r"download-cli:\s*(?P<percent>[\d\.\s]+%).*ETA:(?P<eta>[^ ]+).*Speed:(?P<speed>[^ ]+)(.*Filename:(?P<filename>.+))?", line)
                     if match_progress:
                         pd = match_progress.groupdict()
                         task.progress_str = pd.get("percent", task.progress_str).strip()
                         try: task.progress_val = float(task.progress_str.replace('%','').strip())
                         except ValueError: pass
                         task.eta_str = pd.get("eta", task.eta_str); task.speed_str = pd.get("speed", task.speed_str)
                         if pd.get("filename") and not temp_final_filename: # Ako yt-dlp javi ime fajla kroz progress
                             temp_final_filename = pd.get("filename").strip()
                             logger.info(f"[{task.item_id}] Ime fajla detektirano iz progressa: {temp_final_filename}")
                         self.update_callback(task, "progress_update")
                 else: # Pokušaj naći ime fajla i iz drugih linija (manje pouzdano)
                     dest_match = re.search(r"\[(?:download|ffmpeg|ExtractAudio)\] Destination:\s*(.+)", line)
                     merge_match = re.search(r"\[Merger\] Merging formats into\s*\"?([^\"]+)\"?", line) # Opcija navodnika
                     if dest_match: temp_final_filename = dest_match.group(1).strip()
                     elif merge_match: temp_final_filename = merge_match.group(1).strip()

             stdout_rem, stderr_rem = "", ""
             if process: stdout_rem, stderr_rem = process.communicate(timeout=10)
             
             # Ponovno parsiranje stdout_rem za slučaj da je ime fajla bilo na kraju
             if stdout_rem:
                 for line_out in stdout_rem.strip().splitlines():
                     logger.debug(f"[{task.item_id}] yt-dlp stdout_rem: {line_out}")
                     self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] {line_out}")
                     if not temp_final_filename: # Traži ime samo ako već nije nađeno
                         dest_match = re.search(r"\[(?:download|ffmpeg|ExtractAudio)\] Destination:\s*(.+)", line_out); merge_match = re.search(r"\[Merger\] Merging formats into\s*\"?([^\"]+)\"?", line_out)
                         if dest_match: temp_final_filename = dest_match.group(1).strip()
                         elif merge_match: temp_final_filename = merge_match.group(1).strip()
             if stderr_rem:
                 for line_err in stderr_rem.strip().splitlines():
                     logger.error(f"[{task.item_id}] yt-dlp stderr_rem: {line_err}")
                     self.update_callback(task, "log_message", f"[{os.path.basename(task.url)[:20]}] GREŠKA: {line_err}")

             if cancel_flag_for_task.is_set() or task.status.startswith("Otkaz"): # Provjeri još jednom
                 task.status = "Otkazano" # Postavi konačni status ako je bio "Otkazivanje..."
                 if not task.error_message: task.error_message = "Preuzimanje otkazano."
                 self.update_callback(task, "download_error")
                 logger.info(f"[{task.item_id}] Preuzimanje potvrđeno kao otkazano nakon završetka procesa.")
                 return

             return_code = process.returncode if process else -100
             if return_code == 0:
                 task.status = "Završeno"; task.progress_str = "100.0%"; task.progress_val = 100.0; task.speed_str = ""; task.eta_str = ""
                 if temp_final_filename:
                     # Ponekad yt-dlp daje apsolutnu putanju, ponekad relativnu na output folder
                     if not os.path.isabs(temp_final_filename):
                         task.final_filename = os.path.join(task.output_dir, os.path.basename(temp_final_filename))
                     else:
                         task.final_filename = temp_final_filename # Već je apsolutna
                     
                     if not os.path.exists(task.final_filename): 
                         logger.warning(f"[{task.item_id}] Detektirano ime fajla '{task.final_filename}' ne postoji.")
                         task.final_filename = None 
                 if not task.final_filename: logger.warning(f"[{task.item_id}] Konačno ime fajla nije uspješno detektirano.")
                 self.update_callback(task, "download_complete")
             else:
                 task.status = "Greška"; task.error_message = stderr_rem.strip() if stderr_rem else f"yt-dlp greška (kod: {return_code})"
                 self.update_callback(task, "download_error")
         except FileNotFoundError:
             task.status = "Kritična Greška"; task.error_message = f"{YT_DLP_EXECUTABLE} ili {FFMPEG_EXECUTABLE} nije pronađen."
             logger.critical(task.error_message); self.update_callback(task, "download_error")
         except Exception as e:
             task.status = "Greška Programa"; task.error_message = str(e)
             logger.error(f"[{task.item_id}] Neočekivana greška u _execute_download: {e}", exc_info=True); self.update_callback(task, "download_error")
         finally:
             if task.item_id in self.active_tasks: del self.active_tasks[task.item_id]
             self.active_downloads_count = max(0, self.active_downloads_count - 1)
             task.process = None 
             if task.status not in ["Završeno", "Greška", "Kritična Greška", "Greška Programa"] and not task.status.startswith("Otkazano"):
                 task.status = "Završeno (?)"; logger.warning(f"Task {task.item_id} završen s nejasnim statusom: {task.status}")
             self.update_callback(task, "status_update")
             logger.info(f"Obrada taska {task.item_id} završena ({task.status}). Aktivno: {self.active_downloads_count}")
             if self.active_downloads_count == 0 and self.download_queue.empty() and not self.stop_event.is_set():
                 logger.info("Svi zadaci obrađeni, worker čeka."); status_task = DownloadTask("Red", "N/A", "", f"status_q_empty_{time.time()}"); status_task.status = "Red je prazan."
                 self.update_callback(status_task, "general_status_update", status_task.status)

# Pomoćne funkcije za red
def _empty_queue_while_draining(q, drained_list):
 while not q.empty():
     try: drained_list.append(q.get_nowait())
     except queue.Empty: break

def _remove_task_from_queue_obj(q_obj, task_item_id_to_remove):
 temp_list = []
 _empty_queue_while_draining(q_obj, temp_list)
 removed = False
 for item in temp_list:
     if item.item_id == task_item_id_to_remove: removed = True
     else: q_obj.put(item)
 return removed