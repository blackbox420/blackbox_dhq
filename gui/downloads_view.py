# gui/downloads_view.py

import customtkinter as ctk

class DownloadsView(ctk.CTkFrame):
    def __init__(self, parent, app_context, **kwargs):
        super().__init__(parent, **kwargs)
        self.app_context = app_context
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text=f"DOWNLOADS VIEW ({self.cget('fg_color')})", font=ctk.CTkFont(size=30)).pack(expand=True)
