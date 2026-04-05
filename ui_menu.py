from PyQt6.QtWidgets import QMenuBar
from ui_components import GuideDialog, InfoDialog, SupportHubDialog


def setup_menu_bar(window):
    """Costruisce la barra dei menu superiore per la MainWindow."""
    menubar = window.menuBar()

    # --- MENU PARTITA ---
    game_menu = menubar.addMenu("Partita")

    action_new = game_menu.addAction("Nuova Partita")
    action_new.setShortcut("Ctrl+N")
    action_new.triggered.connect(window.start_new_game_dialog)

    game_menu.addSeparator()

    action_save = game_menu.addAction("Salva Partita...")
    action_save.setShortcut("Ctrl+S")
    action_save.triggered.connect(window.save_game_dialog)

    action_load = game_menu.addAction("Carica Partita...")
    action_load.setShortcut("Ctrl+L")
    action_load.triggered.connect(window.load_game_dialog)

    # --- MENU IMPOSTAZIONI E SISTEMA ---
    settings_menu = menubar.addMenu("Impostazioni")
    settings_menu.addAction("Configura API Key Gemini").triggered.connect(window.show_api_dialog)
    settings_menu.addSeparator()
    # Aggiungiamo il richiamo alla funzione del main per gli aggiornamenti
    settings_menu.addAction("🔄 Cerca Aggiornamenti").triggered.connect(window.check_updates)

    # --- MENU SUPPORTO E AIUTO ---
    help_menu = menubar.addMenu("Aiuto & Supporto")

    action_support = help_menu.addAction("❤️ Supporta il Progetto & Guide")
    action_support.triggered.connect(lambda: SupportHubDialog(window).exec())

    help_menu.addSeparator()
    help_menu.addAction("Info Versione").triggered.connect(lambda: InfoDialog(window).exec())