# utils/theme_colors.py
class DarkThemeColors:
    BACKGROUND_PRIMARY = "#1A1B26"
    BACKGROUND_SECONDARY = "#292A3D" # Za Sidebar, okvire panela
    BACKGROUND_CONTENT = "#202130"   # Za glavni sadržajni panel
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#A9A9B8" # Malo svjetlija siva za sporedni tekst
    TEXT_ACCENT = "#A082F6"    # Svjetlija ljubičasta za akcente (npr. logo)

    ACCENT_PRIMARY = "#7A52F4" # Glavna ljubičasta (npr. aktivni gumb, progress bar)
    ACCENT_SECONDARY = "#6A42E4" # Tamnija/zasićenija za hover

    BORDER_PRIMARY = "#3A3B5A" # Za suptilne obrube između sekcija

    BUTTON_FG_COLOR = ACCENT_PRIMARY
    BUTTON_HOVER_COLOR = ACCENT_SECONDARY
    BUTTON_TEXT_COLOR = TEXT_PRIMARY

    SIDEBAR_BACKGROUND = BACKGROUND_SECONDARY # Iz slike, sidebar je malo drugačije nijanse
    SIDEBAR_TEXT = "#D0D0E0" # Malo svjetliji tekst za bolju čitljivost na tamnijoj pozadini
    SIDEBAR_ICON_COLOR = SIDEBAR_TEXT # Ikone prate boju teksta
    SIDEBAR_ACTIVE_BACKGROUND = ACCENT_PRIMARY
    SIDEBAR_ACTIVE_TEXT = TEXT_PRIMARY
    SIDEBAR_HOVER_BACKGROUND = "#3A3B5A" # Tamniji hover za suptilnost

    # Dodatne boje prema potrebi
    INPUT_BG = "#202130"
    INPUT_BORDER = BORDER_PRIMARY
    INPUT_TEXT = TEXT_PRIMARY
    PLACEHOLDER_TEXT = TEXT_SECONDARY

    LIST_ITEM_BG = BACKGROUND_CONTENT
    LIST_ITEM_HOVER_BG = BACKGROUND_SECONDARY
    LIST_ITEM_SELECTED_BG = ACCENT_PRIMARY
    LIST_ITEM_SELECTED_FG_TEXT = TEXT_PRIMARY # Tekst na selektiranom itemu

    SUCCESS = "#2ECC71"
    WARNING = "#F39C12"
    ERROR = "#E74C3C"