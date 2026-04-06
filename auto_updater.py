import urllib.request
import os
import time
import webbrowser
from PyQt6.QtWidgets import QMessageBox


class AutoUpdater:
    """Gestisce il controllo degli aggiornamenti e reindirizza a GitHub."""

    # ⚠️ IL TUO USERNAME E I LINK
    GITHUB_USERNAME = "enkas79"
    BASE_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/Polis_AI/master/"
    RELEASES_URL = f"https://github.com/{GITHUB_USERNAME}/Polis_AI/releases/latest"

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
        """Controlla se c'è una versione più recente online."""
        local_version = cls.get_local_version()

        try:
            # 1. Controlla la versione online (con Cache-Buster)
            version_url = cls.BASE_RAW_URL + f"version.txt?t={time.time()}"
            req = urllib.request.Request(version_url, headers={'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=5) as response:
                online_version = response.read().decode('utf-8').strip()

            # 2. Confronta le versioni
            if online_version > local_version:
                reply = QMessageBox.question(
                    parent_window,
                    "Aggiornamento Disponibile!",
                    f"È uscita la nuova versione <b>{online_version}</b>! (La tua: {local_version}).\n\nVuoi aprire la pagina di download per scaricare il nuovo Installer?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Apre il browser predefinito del PC dell'utente direttamente sulla pagina delle tue Release!
                    webbrowser.open(cls.RELEASES_URL)

                    QMessageBox.information(
                        parent_window,
                        "Download",
                        "Il tuo browser si sta aprendo sulla pagina ufficiale di Polis_AI.\nScarica il nuovo file di Setup e installalo. Sovrascriverà automaticamente la versione vecchia senza farti perdere i salvataggi!"
                    )
            else:
                QMessageBox.information(parent_window, "Aggiornato",
                                        f"Polis_AI è aggiornato all'ultima versione disponibile ({local_version}).")

        except Exception as e:
            QMessageBox.warning(parent_window, "Errore di Connessione",
                                f"Impossibile controllare gli aggiornamenti.\nControlla la connessione internet.\nErrore: {e}")