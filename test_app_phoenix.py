import unittest
from unittest.mock import patch, MagicMock

# Patch customtkinter, tkinter, and cryptography before importing app_phoenix
with patch.dict('sys.modules', {
    'customtkinter': MagicMock(),
    'tkinter': MagicMock(),
    'tkinter.messagebox': MagicMock(),
    'cryptography': MagicMock(),
    'cryptography.fernet': MagicMock(),
    'cryptography.hazmat': MagicMock(),
    'cryptography.hazmat.primitives': MagicMock(),
    'cryptography.hazmat.primitives.kdf': MagicMock(),
    'cryptography.hazmat.primitives.kdf.pbkdf2': MagicMock(),
    'cryptography.hazmat.backends': MagicMock(),
}):
    import app_phoenix

class TestAppPhoenix(unittest.TestCase):
    @patch('app_phoenix.settings_handler')
    @patch('app_phoenix.downloader_engine')
    @patch('app_phoenix.LicenseManager')
    @patch('app_phoenix.ctk')
    @patch('app_phoenix.tk')
    def test_app_initialization(self, _mock_tk, _mock_ctk, mock_LicenseManager, mock_downloader_engine, mock_settings_handler):
        # Mock settings
        mock_settings_handler.load_settings.return_value = {
            "appearance_mode": "dark",
            "theme": "blue",
            "window_geometry": "800x600",
            "sidebar_width": 200,
            "max_concurrent_downloads": 2
        }
        mock_downloader = MagicMock()
        mock_downloader_engine.Downloader.return_value = mock_downloader
        mock_license_manager = MagicMock()
        mock_LicenseManager.return_value = mock_license_manager
        # License is valid
        mock_license_manager.is_license_valid.return_value = (True, {"type": "standard"})
        # Patch MainWindow to avoid GUI
        with patch('app_phoenix.MainWindow') as mock_MainWindow:
            app = app_phoenix.App()
            self.assertTrue(hasattr(app, 'root'))
            self.assertEqual(app.settings["appearance_mode"], "dark")
            mock_ctk.set_appearance_mode.assert_called_with("dark")
            mock_ctk.set_default_color_theme.assert_called_with("blue")
            mock_downloader_engine.Downloader.assert_called()
            mock_LicenseManager.assert_called()
            mock_MainWindow.assert_called()
            self.assertIn("download_manager", app.root.app_context)
            self.assertIn("settings", app.root.app_context)
            self.assertIn("status_bar_var", app.root.app_context)

    @patch('app_phoenix.settings_handler')
    @patch('app_phoenix.downloader_engine')
    @patch('app_phoenix.LicenseManager')
    @patch('app_phoenix.ctk')
    @patch('app_phoenix.tk')
    def test_app_license_activation_flow(self, _mock_tk, _mock_ctk, mock_LicenseManager, mock_downloader_engine, mock_settings_handler):
        mock_settings_handler.load_settings.return_value = {}
        mock_downloader_engine.Downloader.return_value = MagicMock()
        mock_license_manager = MagicMock()
        mock_LicenseManager.return_value = mock_license_manager
        # License is invalid
        mock_license_manager.is_license_valid.return_value = (False, "No license")
        with patch('app_phoenix.LicenseActivationWindow') as mock_LicenseActivationWindow:
            with patch('app_phoenix.MainWindow'):
                app = app_phoenix.App()
                mock_LicenseActivationWindow.assert_called()
                self.assertIn("license_manager", app.root.app_context)

    @patch('app_phoenix.settings_handler')
    @patch('app_phoenix.downloader_engine')
    @patch('app_phoenix.LicenseManager')
    @patch('app_phoenix.ctk')
    @patch('app_phoenix.tk')
    def test_on_app_quit_saves_settings_and_stops_downloader(self, _mock_tk, _mock_ctk, mock_LicenseManager, mock_downloader_engine, mock_settings_handler):
        mock_settings_handler.load_settings.return_value = {}
        mock_downloader = MagicMock()
        mock_downloader_engine.Downloader.return_value = mock_downloader
        mock_license_manager = MagicMock()
        mock_LicenseManager.return_value = mock_license_manager
        with patch('app_phoenix.MainWindow'):
            app = app_phoenix.App()
            app.root.geometry.return_value = "1024x768"
            app.download_manager = mock_downloader
            app._on_app_quit()
            mock_settings_handler.save_settings.assert_called()
            mock_downloader.stop_worker.assert_called()
            app.root.destroy.assert_called()

if __name__ == "__main__":
    unittest.main()
