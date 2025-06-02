# core/settings_handler.py
import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".blackbox_dhq_phoenix_v3")
APP_SETTINGS_FILE = os.path.join(CONFIG_DIR, "app_settings.json")

DEFAULT_QUALITY_PROFILES_KEYS_PLACEHOLDER = [
     "Video - 1080p MP4", "Video - 720p MP4", "Video - Najbolji MP4", 
     "Audio - Najbolji MP3", "Audio - Najbolji M4A/AAC", "Općenito - Najbolje Moguće"
]

DEFAULT_SETTINGS = {
    "output_directory": os.path.join(os.path.expanduser("~"), "Desktop", "BlackBox_Phoenix_Downloads"),
    "default_quality": "Video - 1080p MP4",
    "theme": "blue", 
    "appearance_mode": "dark",
    "window_geometry": "1280x780",
    "ask_open_folder": True,
    "auto_paste_clipboard": False,
    "max_concurrent_downloads": 1,
    "prefer_hw_acceleration": False,
    "embed_thumbnail_audio": True,
    "add_metadata_video": True,
    "sidebar_width": 240,
}

def _ensure_output_dir_exists(output_dir_path, settings_ref_to_update_on_fallback):
    if not os.path.isabs(output_dir_path):
         logger.warning(f"Putanja izlaznog direktorija '{output_dir_path}' nije apsolutna, konvertiram.")
         output_dir_path = os.path.abspath(output_dir_path)
         settings_ref_to_update_on_fallback["output_directory"] = output_dir_path

    if not os.path.isdir(output_dir_path):
        logger.info(f"Izlazni direktorij '{output_dir_path}' ne postoji, pokušavam kreirati.")
        try:
            os.makedirs(output_dir_path, exist_ok=True)
            logger.info(f"Uspješno kreiran izlazni direktorij: {output_dir_path}")
        except OSError as e_mkdir:
            logger.error(f"Nije moguće kreirati izlazni direktorij '{output_dir_path}': {e_mkdir}. Koristim fallback.")
            fallback_dir = os.path.join(CONFIG_DIR, "Downloads_Fallback_Safe")
            try:
                os.makedirs(fallback_dir, exist_ok=True)
                settings_ref_to_update_on_fallback["output_directory"] = fallback_dir
                logger.info(f"Postavljen fallback izlazni direktorij: {fallback_dir}")
            except OSError as e_fallback_mkdir:
                logger.critical(f"Nije moguće kreirati ni fallback direktorij '{fallback_dir}': {e_fallback_mkdir}")

def load_settings():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    current_settings = DEFAULT_SETTINGS.copy()

    if not os.path.exists(APP_SETTINGS_FILE):
        logger.info(f"Fajl s postavkama ne postoji ({APP_SETTINGS_FILE}). Kreiram s defaultnim vrijednostima.")
        _ensure_output_dir_exists(current_settings["output_directory"], current_settings)
        _save_settings(current_settings)
        return current_settings
    
    try:
        with open(APP_SETTINGS_FILE, "r", encoding='utf-8') as f:
            loaded_settings = json.load(f)
        
        settings_changed_during_load = False
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in loaded_settings:
                loaded_settings[key] = default_value
                settings_changed_during_load = True
        
        current_settings = loaded_settings
        _ensure_output_dir_exists(current_settings["output_directory"], current_settings)

        if settings_changed_during_load :
             _save_settings(current_settings)
        return current_settings
    except (json.JSONDecodeError, IOError, TypeError) as e:
        logger.error(f"Greška pri čitanju postavki ({APP_SETTINGS_FILE}): {e}. Vraćam na defaultne i spremam.")
        current_settings = DEFAULT_SETTINGS.copy()
        _ensure_output_dir_exists(current_settings["output_directory"], current_settings)
        _save_settings(current_settings)
        return current_settings

def save_settings(settings_data):
    if "output_directory" in settings_data:
        settings_data["output_directory"] = os.path.abspath(settings_data["output_directory"])
        _ensure_output_dir_exists(settings_data["output_directory"], settings_data)
    _save_settings(settings_data)

def _save_settings(settings_data_to_save):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(APP_SETTINGS_FILE, "w", encoding='utf-8') as f:
            json.dump(settings_data_to_save, f, indent=4, ensure_ascii=False)
        logger.info(f"Postavke spremljene u {APP_SETTINGS_FILE}")
    except IOError as e:
        logger.error(f"Greška: Nije moguće sačuvati postavke u {APP_SETTINGS_FILE}: {e}")

initial_settings = load_settings()