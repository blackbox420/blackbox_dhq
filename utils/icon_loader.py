# utils/icon_loader.py
import customtkinter as ctk
from PIL import Image, UnidentifiedImageError
import os
import logging

logger = logging.getLogger(__name__)
ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")
os.makedirs(ICON_PATH, exist_ok=True)

def load_icon(icon_name: str, size: tuple = (22, 22)):
    base_icon_name = icon_name.replace(".png", "")
    light_image_path = os.path.join(ICON_PATH, f"{base_icon_name}_light.png")
    dark_image_path = os.path.join(ICON_PATH, f"{base_icon_name}_dark.png")
    generic_image_path = os.path.join(ICON_PATH, f"{base_icon_name}.png")
    try:
        pil_light_image, pil_dark_image = None, None
        if os.path.exists(light_image_path): pil_light_image = Image.open(light_image_path)
        if os.path.exists(dark_image_path): pil_dark_image = Image.open(dark_image_path)
        if pil_light_image and pil_dark_image:
            logger.debug(f"Ikona '{base_icon_name}' učitana (light/dark).")
            return ctk.CTkImage(light_image=pil_light_image.resize(size, Image.LANCZOS),
                                dark_image=pil_dark_image.resize(size, Image.LANCZOS), size=size)
        elif os.path.exists(generic_image_path):
            img = Image.open(generic_image_path)
            logger.debug(f"Ikona '{base_icon_name}' učitana (generička).")
            return ctk.CTkImage(light_image=img.resize(size, Image.LANCZOS),
                                dark_image=img.resize(size, Image.LANCZOS), size=size)
        elif pil_light_image:
            logger.debug(f"Ikona '{base_icon_name}' učitana (samo light).")
            return ctk.CTkImage(light_image=pil_light_image.resize(size, Image.LANCZOS),
                                dark_image=pil_light_image.resize(size, Image.LANCZOS), size=size)
        elif pil_dark_image:
            logger.debug(f"Ikona '{base_icon_name}' učitana (samo dark).")
            return ctk.CTkImage(light_image=pil_dark_image.resize(size, Image.LANCZOS),
                                dark_image=pil_dark_image.resize(size, Image.LANCZOS), size=size)
        logger.warning(f"Ikona '{base_icon_name}.png' nije pronađena u {ICON_PATH}")
        return None
    except UnidentifiedImageError: logger.error(f"Fajl za ikonu '{base_icon_name}' nije validna slika."); return None
    except Exception as e: logger.error(f"Greška pri učitavanju ikone '{base_icon_name}': {e}"); return None