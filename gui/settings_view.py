# gui/settings_view.py

import customtkinter as ctk

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, app_context, **kwargs):
        super().__init__(parent, **kwargs)
        self.app_context = app_context
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text=f"SETTINGS VIEW ({self.cget('fg_color')})", font=ctk.CTkFont(size=30)).pack(expand=True)
