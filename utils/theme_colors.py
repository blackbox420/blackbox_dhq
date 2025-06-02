# utils/theme_colors.py
class DarkThemeColors:
    BACKGROUND_PRIMARY = "#1A1B26"  # Tamnija pozadina aplikacije
    BACKGROUND_SECONDARY = "#292A3D" # Za Sidebar, okvire, malo svjetlije elemente
    BACKGROUND_CONTENT = "#202130"   # Pozadina glavnog radnog prostora pogleda

    TEXT_PRIMARY = "#EAEAEA" # Svjetliji tekst za dobru čitljivost
    TEXT_SECONDARY = "#A9A9B8" # Sivkasta za sporedni tekst, opise
    TEXT_ACCENT = "#A082F6"    # Svjetlija ljubičasta za naslove ili istaknuti tekst

    ACCENT_PRIMARY = "#7A52F4" # Glavna ljubičasta (aktivni elementi, gumbi)
    ACCENT_SECONDARY = "#6A42E4" # Tamnija/zasićenija za hover na akcentima

    BORDER_PRIMARY = "#3A3B5A" # Za suptilne obrube

    BUTTON_FG_COLOR = ACCENT_PRIMARY
    BUTTON_HOVER_COLOR = ACCENT_SECONDARY
    BUTTON_TEXT_COLOR = TEXT_PRIMARY

    SIDEBAR_BACKGROUND = BACKGROUND_SECONDARY 
    SIDEBAR_TEXT = "#D0D0E0" 
    SIDEBAR_ICON_COLOR = SIDEBAR_TEXT 
    SIDEBAR_ACTIVE_BACKGROUND = ACCENT_PRIMARY
    SIDEBAR_ACTIVE_TEXT = TEXT_PRIMARY
    SIDEBAR_HOVER_BACKGROUND = "#3A3B5A" 

    INPUT_BG = "#2B2B3B" # Malo drugačija pozadina za unosna polja
    INPUT_BORDER = BORDER_PRIMARY
    INPUT_TEXT = TEXT_PRIMARY
    PLACEHOLDER_TEXT = TEXT_SECONDARY

    LIST_ITEM_BG = BACKGROUND_CONTENT
    LIST_ITEM_HOVER_BG = BACKGROUND_SECONDARY
    LIST_ITEM_SELECTED_BG = ACCENT_PRIMARY
    LIST_ITEM_SELECTED_FG_TEXT = TEXT_PRIMARY

    SUCCESS = "#2ECC71" # Zelena
    WARNING = "#F39C12" # Narančasta
    ERROR = "#E74C3C"   # Crvena

    # Boje za Treeview (primjer)
    TREEVIEW_BG = BACKGROUND_CONTENT
    TREEVIEW_TEXT = TEXT_PRIMARY
    TREEVIEW_SELECTED_BG = ACCENT_PRIMARY
    TREEVIEW_SELECTED_FG = TEXT_PRIMARY
    TREEVIEW_HEADING_BG = BACKGROUND_SECONDARY
    TREEVIEW_HEADING_FG = TEXT_PRIMARY