import urllib.request
import os
import time
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import Qt


class AutoUpdater:
    """Gestisce il controllo e il download degli aggiornamenti da GitHub."""

    # ⚠️ INSERISCI QUI IL TUO USERNAME DI GITHUB
    GITHUB_USERNAME = "enkas79"

    # URL di base per scaricare i file grezzi (Raw) da GitHub (Ramo MASTER)
    BASE_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/Polis_AI/master/"

    # Lista dei file fondamentali da aggiornare
    FILES_TO_UPDATE = [
        "main.py",
        "game_engine.py",
        "map_manager.py",
        "ui_components.py",
        "ui_menu.py",
        "config_manager.py",
        "auto_updater.py",
        "version.txt"
    ]

    @staticmethod
    def get_local_version() -> str:
        """Legge la versione attuale dal file version.txt sul PC."""
        try:
            with open("version.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"

    @classmethod
    def check_for_updates(cls, parent_window=None) -> None:
        """Controlla se c'è una versione più recente online e avvia l'aggiornamento."""
        local_version = cls.get_local_version()

        try:
            # 1. Controlla la versione online (con Cache-Buster!)
            version_url = cls.BASE_RAW_URL + f"version.txt?t={time.time()}"
            req = urllib.request.Request(version_url, headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=5) as response:
                online_version = response.read().decode('utf-8').strip()

            # 2. Confronta le versioni
            if online_version > local_version:
                reply = QMessageBox.question(
                    parent_window,
                    "Aggiornamento Disponibile!",
                    f"È disponibile la versione <b>{online_version}</b> (Attuale: {local_version}).\nVuoi scaricarla e installarla ora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    cls._download_and_install_update(parent_window)
            else:
                QMessageBox.information(parent_window, "Aggiornato",
                                        f"Polis_AI è aggiornato all'ultima versione disponibile ({local_version}).")

        except Exception as e:
            QMessageBox.warning(parent_window, "Errore di Connessione",
                                f"Impossibile controllare gli aggiornamenti.\nControlla la connessione o l'username GitHub.\nErrore: {e}")

    @classmethod
    def _download_and_install_update(cls, parent_window) -> None:
        """Scarica i file dal server e sovrascrive quelli locali."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            for filename in cls.FILES_TO_UPDATE:
                # Usa il Cache-Buster anche per scaricare i file nuovi!
                file_url = cls.BASE_RAW_URL + f"{filename}?t={time.time()}"
                req = urllib.request.Request(file_url, headers={'Cache-Control': 'no-cache'})

                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read()

                # Sovrascrive il file locale
                with open(filename, "wb") as f:
                    f.write(content)

            QApplication.restoreOverrideCursor()
            QMessageBox.information(
                parent_window,
                "Aggiornamento Completato",
                "Il simulatore è stato aggiornato con successo!\nIl programma verrà ora chiuso per applicare le modifiche. Riavviarlo manualmente."
            )
            QApplication.quit()  # Chiude l'app per permettere il riavvio con i nuovi file

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(parent_window, "Errore Critico", f"Errore durante il download dell'aggiornamento: {e}")