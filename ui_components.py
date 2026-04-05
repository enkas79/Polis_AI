import re
import os
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QLineEdit, QMessageBox, QWidget, QComboBox, QGridLayout,
    QTabWidget, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QClipboard


class ReportDialog(QDialog):
    def __init__(self, date_str: str, report_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Rapporto Globale - {date_str}")
        self.resize(750, 550)

        layout = QVBoxLayout(self)

        header = QLabel(f"<b>REPORT INTELLIGENCE GLOBALE</b><br>Data di stesura: {date_str}")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 16px; color: #2c3e50; padding: 10px; border-bottom: 2px solid #bdc3c7;")
        layout.addWidget(header)

        formatted_html = self.parse_markdown_to_html(report_text)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setHtml(formatted_html)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #fdfdfd; 
                color: #333333; 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 15px; 
                padding: 15px; 
                border: 1px solid #dcdde1;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.text_display)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Ricevuto (Chiudi Rapporto)")
        btn_close.setMinimumWidth(200)
        btn_close.setMinimumHeight(40)
        btn_close.setStyleSheet(
            "background-color: #34495e; color: white; font-weight: bold; font-size: 14px; border-radius: 5px;")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def parse_markdown_to_html(self, text: str) -> str:
        text = text.replace('*[DATI]', '[DATI]').replace('[DATI]*', '[DATI]')
        text = text.replace('*[DIPLOMAZIA]', '[DIPLOMAZIA]').replace('[DIPLOMAZIA]*', '[DIPLOMAZIA]')
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'^\* (.*)', r'• \1', text, flags=re.MULTILINE)
        text = text.replace('\n', '<br>')
        return text


class ApiDialog(QDialog):
    def __init__(self, current_key: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurazione API Key")
        self.setFixedSize(400, 150)
        self.new_key: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Inserisci la tua Google Gemini API Key:"))

        self.key_input = QLineEdit()
        self.key_input.setText(current_key)
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Salva")
        btn_save.clicked.connect(self.accept_key)
        btn_cancel = QPushButton("Annulla")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def accept_key(self) -> None:
        self.new_key = self.key_input.text().strip()
        self.accept()


class InfoDialog(QMessageBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Legge la versione dinamicamente
        versione = "Sconosciuta"
        try:
            with open("version.txt", "r", encoding="utf-8") as f:
                versione = f.read().strip()
        except FileNotFoundError:
            pass

        self.setWindowTitle("Informazioni su Polis_AI")
        self.setText("<b>Polis_AI Simulator</b>")
        self.setInformativeText(
            f"Autore: Enrico Martini\nVersione: {versione}\n\nMotore AI: Gemini (Attivo)\nMappa: Leaflet.js con GeoJSON"
        )
        self.setIcon(QMessageBox.Icon.Information)


class GuideDialog(QMessageBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guida al Gioco")
        self.setText("<b>Come giocare:</b>")
        self.setInformativeText(
            "0. <b>Setup:</b> Inserisci la API Key di Gemini da Impostazioni.\n"
            "1. <b>Nazione:</b> Clicca con il TASTO SINISTRO su una nazione per giocarla.\n"
            "2. <b>Intelligence:</b> Clicca con il TASTO DESTRO per visualizzare risorse, alleanze ed eseguire azioni mirate.\n"
            "3. <b>Auto-Apprendimento:</b> Usa il tasto destro su una nazione vuota e clicca 'Censisci' per farla analizzare all'IA e salvarla nello scenario.\n"
            "4. <b>Scorciatoie:</b> Usa Ctrl+N (Nuova), Ctrl+S (Salva) e Ctrl+L (Carica)."
        )


class ScenarioSelectionDialog(QDialog):
    def __init__(self, scenarios: list, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Seleziona Scenario Iniziale")
        self.setFixedSize(450, 180)
        self.selected_filename: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Benvenuto in Polis_AI. Seleziona l'epoca storica:</b>"))

        self.scenario_combo = QComboBox()
        if not scenarios:
            self.scenario_combo.addItem("Nessun file scenario trovato (Cartella 'scenarios' vuota).", "")
        else:
            for sc in scenarios:
                self.scenario_combo.addItem(f"{sc['name']} (Anno: {sc['year']})", sc['filename'])

        self.scenario_combo.setStyleSheet("padding: 5px; font-size: 14px;")
        layout.addWidget(self.scenario_combo)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        btn_start = QPushButton("Inizia Simulazione")
        btn_start.setMinimumHeight(35)
        btn_start.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_start.clicked.connect(self.accept_selection)

        btn_cancel = QPushButton("Modalità Sandbox (Senza Scenario)")
        btn_cancel.setMinimumHeight(35)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def accept_selection(self) -> None:
        self.selected_filename = self.scenario_combo.currentData()
        self.accept()


class CountryIntelDialog(QDialog):
    def __init__(self, country_name: str, intel_data: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Fascicolo Intelligence: {country_name}")
        self.setFixedSize(450, 360)
        self.selected_action: str = ""

        layout = QVBoxLayout(self)

        header = QLabel(f"<b>Dipartimento di Spionaggio ed Esteri</b><br>Dossier: {country_name.upper()}")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 15px; color: #2c3e50; padding-bottom: 5px; border-bottom: 1px solid #bdc3c7;")
        layout.addWidget(header)

        layout.addSpacing(5)

        if intel_data.get("is_player"):
            rel_text = "<b>Questa è la tua Nazione.</b>"
        else:
            rel_val = intel_data.get("relation", 0)
            rel_status = "Alleato" if rel_val >= 50 else "Amichevole" if rel_val > 10 else "Ostilità" if rel_val <= -50 else "Tensioni" if rel_val < -10 else "Neutrale"
            rel_color = "green" if rel_val > 10 else "red" if rel_val < -10 else "black"
            rel_text = f"Relazione Diplomatica: <b style='color:{rel_color};'>{rel_val} ({rel_status})</b>"

        layout.addWidget(QLabel(rel_text))

        factions = intel_data.get("factions", [])
        fac_text = ", ".join(factions) if factions else "Nessuna alleanza nota o Non allineato."
        fac_label = QLabel(f"<b>Blocchi / Alleanze:</b> {fac_text}")
        fac_label.setStyleSheet("color: #2980b9;")
        layout.addWidget(fac_label)

        res_text = intel_data.get("resources", "Dati classificati o nazione minore. (Nessuna risorsa nel JSON)")
        res_label = QLabel(f"Risorse e Settori Chiave:<br><i>{res_text}</i>")
        res_label.setWordWrap(True)
        res_label.setStyleSheet("padding: 10px; background-color: #ecf0f1; border-radius: 5px; margin-top: 5px;")
        layout.addWidget(res_label)

        if not intel_data.get("is_preloaded"):
            btn_learn = QPushButton("🌐 Censisci Nazione (Salva nello Scenario)")
            btn_learn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; margin-top: 5px;")
            btn_learn.clicked.connect(lambda: self.set_action("[CENSISCI]"))
            layout.addWidget(btn_learn)

        layout.addStretch()

        if not intel_data.get("is_player"):
            layout.addWidget(QLabel("<b>Azioni Rapide (Auto-compila Ministero Esteri):</b>"))

            grid = QGridLayout()

            btn_ally = QPushButton("🤝 Proponi Alleanza")
            btn_ally.clicked.connect(
                lambda: self.set_action(f"Proponi un'alleanza strategica e commerciale formale a {country_name}."))

            btn_fund = QPushButton("💰 Invia Aiuti Finanziari")
            btn_fund.clicked.connect(
                lambda: self.set_action(f"Invia un massiccio pacchetto di aiuti finanziari a {country_name}."))

            btn_embargo = QPushButton("⛔ Imponi Embargo")
            btn_embargo.clicked.connect(
                lambda: self.set_action(f"Imponi un embargo commerciale severo contro {country_name}."))

            btn_war = QPushButton("⚔️ Minaccia Militare")
            btn_war.setStyleSheet("color: #c0392b; font-weight: bold;")
            btn_war.clicked.connect(lambda: self.set_action(
                f"Avvia provocazioni militari e minaccia apertamente il governo di {country_name}."))

            grid.addWidget(btn_ally, 0, 0)
            grid.addWidget(btn_fund, 0, 1)
            grid.addWidget(btn_embargo, 1, 0)
            grid.addWidget(btn_war, 1, 1)

            layout.addLayout(grid)

        btn_close = QPushButton("Chiudi Fascicolo")
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close)

    def set_action(self, action_text: str) -> None:
        self.selected_action = action_text
        self.accept()


class SupportHubDialog(QDialog):
    """L'Hub centrale per le Guide, le API e le Donazioni."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hub di Supporto e Documentazione Polis_AI")
        self.setFixedSize(750, 550)  # Ingrandita per leggere meglio i manuali

        layout = QVBoxLayout(self)

        header = QLabel("<b>Centro Operativo Polis_AI</b>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)

        tabs = QTabWidget()

        # ---------------------------------------------------------
        # TAB 1: DONAZIONI
        # ---------------------------------------------------------
        tab_donate = QWidget()
        donate_layout = QVBoxLayout(tab_donate)
        donate_lbl = QLabel(
            "Polis_AI è sviluppato in modo indipendente. Se il simulatore ti appassiona, considera di supportare lo sviluppo!")
        donate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        donate_layout.addWidget(donate_lbl)

        qr_layout = QHBoxLayout()

        paypal_box = QVBoxLayout()
        lbl_pp = QLabel("<b>Supporta tramite PayPal</b><br>Offrimi un caffè! ☕")
        lbl_pp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        paypal_box.addWidget(lbl_pp)

        pic_pp = QLabel()
        if os.path.exists("assets/paypal_qr.jpg"):
            pixmap = QPixmap("assets/paypal_qr.jpg").scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
            pic_pp.setPixmap(pixmap)
        else:
            pic_pp.setText("[Nessun QR PayPal in assets/]")
        pic_pp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        paypal_box.addWidget(pic_pp)
        qr_layout.addLayout(paypal_box)

        ton_box = QVBoxLayout()
        lbl_ton = QLabel("<b>Supporta tramite Toncoin</b><br>Dona crypto (TON) 💎")
        lbl_ton.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ton_box.addWidget(lbl_ton)

        pic_ton = QLabel()
        if os.path.exists("assets/ton_qr.jpg"):
            pixmap = QPixmap("assets/ton_qr.jpg").scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
            pic_ton.setPixmap(pixmap)
        else:
            pic_ton.setText("[Nessun QR Toncoin in assets/]")
        pic_ton.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ton_box.addWidget(pic_ton)

        ton_address = "UQD40vFmVJj7mZAuw1Fji9EwrPGXaAziInYBb6mw0nyInIrj"
        ton_addr_lbl = QLineEdit(ton_address)
        ton_addr_lbl.setReadOnly(True)
        ton_addr_lbl.setStyleSheet("font-size: 11px;")
        ton_box.addWidget(ton_addr_lbl)

        btn_copy = QPushButton("Copia Indirizzo TON")
        btn_copy.clicked.connect(lambda: self.copy_to_clipboard(ton_address))
        ton_box.addWidget(btn_copy)

        qr_layout.addLayout(ton_box)
        donate_layout.addLayout(qr_layout)
        tabs.addTab(tab_donate, "❤️ Supporta il Progetto")

        # ---------------------------------------------------------
        # TAB 2: GUIDA API (Esaustiva)
        # ---------------------------------------------------------
        tab_api = QWidget()
        api_layout = QVBoxLayout(tab_api)
        api_text = """
        <h2 style='color: #2980b9;'>Guida Completa all'API di Google Gemini</h2>
        <p>Polis_AI non usa algoritmi pre-programmati, ma si appoggia all'Intelligenza Artificiale Generativa di Google (Gemini 2.5-Flash) per simulare un mondo vivo, reagire alle tue scelte e calcolare l'impatto economico delle tue manovre politiche. Per funzionare, il gioco ha bisogno della tua chiave di accesso personale (API Key).</p>

        <h3>🛠️ Passo 1: Ottenere la Chiave (Gratis)</h3>
        <ol>
            <li>Assicurati di avere un account Google (Gmail).</li>
            <li>Visita il sito per sviluppatori: <b><a href="https://aistudio.google.com">aistudio.google.com</a></b>.</li>
            <li>Accetta i termini di servizio iniziali se è la tua prima volta.</li>
            <li>Nel menu laterale sinistro, clicca sul pulsante azzurro <b>"Get API Key"</b>.</li>
            <li>Clicca sul bottone <b>"Create API key"</b> e seleziona "Create API key in new project".</li>
            <li>Apparirà una finestra con una lunga stringa di lettere e numeri. <b>Copiala</b>.</li>
        </ol>

        <h3>⚙️ Passo 2: Inserimento in Polis_AI</h3>
        <ul>
            <li>Nel menu in alto del gioco, clicca su <b>Impostazioni > Configura API Key</b>.</li>
            <li>Incolla la chiave precedentemente copiata e clicca su "Salva".</li>
            <li>La chiave viene salvata localmente in modo sicuro sul tuo PC nel file <i>polis_ai_config.json</i>.</li>
        </ul>

        <h3>⚠️ Limiti e Costi (Il Livello Gratuito)</h3>
        <p>Utilizzare Gemini tramite l'API è <b>completamente gratuito</b> se si resta entro determinati limiti (Free Tier). Attualmente Google consente fino a <b>15 richieste al minuto</b> e 1.500 richieste al giorno per il modello Flash. Questo è più che sufficiente per giocare a Polis_AI senza spendere un centesimo. Se giochi troppo velocemente inviando decine di comandi in pochi secondi, il gioco potrebbe restituire un errore di "Quota Exceeded". In tal caso, basta aspettare un minuto.</p>

        <h3>🔧 Risoluzione Problemi</h3>
        <ul>
            <li><b>Errore 403 (Permission Denied):</b> La chiave è incollata male (controlla gli spazi) oppure non hai accettato i termini su AI Studio.</li>
            <li><b>L'IA risponde con errori strani:</b> A volte l'IA può "allucinare" e sbagliare a formattare il testo. Il motore del gioco ha dei sistemi di sicurezza (fallback) che manterranno l'economia stabile, ma ti basterà fare un altro turno per ricalibrare il sistema.</li>
        </ul>
        """
        api_lbl = QTextEdit()
        api_lbl.setHtml(api_text)
        api_lbl.setReadOnly(True)
        api_lbl.setStyleSheet("background-color: #fdfdfd; padding: 10px; font-size: 13px;")
        api_layout.addWidget(api_lbl)
        tabs.addTab(tab_api, "🔑 Guida API Gemini")

        # ---------------------------------------------------------
        # TAB 3: MANUALE DI GIOCO (Esaustivo)
        # ---------------------------------------------------------
        tab_manual = QWidget()
        manual_layout = QVBoxLayout(tab_manual)
        manual_text = """
        <h2 style='color: #27ae60;'>Manuale Operativo del Game Master</h2>
        <p>Benvenuto in Polis_AI, un simulatore geopolitico asimmetrico e "Data-Driven". Tu sei il Capo di Stato. Non ci sono percorsi predefiniti: ogni azione che scriverai avrà conseguenze valutate in tempo reale dall'intelligenza artificiale.</p>

        <h3>🌍 1. La Mappa e l'Intelligence (I Due Click)</h3>
        <ul>
            <li><b>Tasto Sinistro (Presa di Potere):</b> Clicca su una nazione per diventarne il leader. Attenzione: la scelta è irreversibile per la durata della partita.</li>
            <li><b>Tasto Destro (Spionaggio e Diplomazia):</b> Clicca col destro su <i>qualsiasi</i> nazione per aprire il suo <b>Fascicolo Intelligence</b>. Qui vedrai le sue risorse economiche chiave, a quali alleanze appartiene (es. NATO, BRICS) e le tue relazioni diplomatiche con essa. Da questo fascicolo puoi usare i pulsanti per auto-compilare dichiarazioni di guerra, embarghi o alleanze.</li>
            <li><b>Il Pulsante "Censisci" (Auto-Apprendimento):</b> Se una nazione non ha dati nel database dello scenario, nel suo fascicolo apparirà il tasto dorato "Censisci Nazione". Cliccandolo, l'IA analizzerà la storia di quel paese e lo scriverà in modo permanente nei file di gioco.</li>
        </ul>

        <h3>📊 2. Economia e Cruscotto Nazionale</h3>
        <p>Non si governa solo con i discorsi. L'economia reale del tuo paese è misurata in miliardi di dollari.</p>
        <ul>
            <li><b>Tesoro (Riserve/PIL):</b> Sono i soldi a tua disposizione. Più l'economia è florida, più il tesoretto cresce. Puoi usarlo per finanziare manovre titaniche, ma se esageri dovrai emettere debito.</li>
            <li><b>Debito Pubblico:</b> Il nemico silenzioso. Fare deficit spending (spendere soldi che non hai) farà aumentare il debito. Se il debito diventa insostenibile rispetto al tuo Tesoro e alla tua Salute Economica, i mercati internazionali ti taglieranno fuori, causando default e crollo della stabilità.</li>
            <li><b>Popolazione:</b> Misurata in milioni. Impatta la tua forza militare e la produzione. Cambierà lentamente in base alle tue riforme interne e alle crisi.</li>
        </ul>

        <h3>📝 3. Come Impartire Direttive (I Prompt)</h3>
        <p>Puoi giocare in due modi: usando i pulsanti rapidi dal Fascicolo Intelligence (Tasto Destro), oppure scrivendo di tuo pugno nei tre ministeri.</p>
        <ul>
            <li><b>Interni:</b> Gestione della polizia, riforme sanitarie, diritti civili, tassazione locale. Es: <i>"Aumenta la spesa sanitaria del 5% e instaura la legge marziale nelle capitali."</i></li>
            <li><b>Economia:</b> Infrastrutture, accordi commerciali, nazionalizzazioni, sussidi. Es: <i>"Costruisci una rete ferroviaria ad alta velocità e aumenta le tasse sulle multinazionali straniere."</i></li>
            <li><b>Esteri/Difesa:</b> Spostamento truppe, minacce, spionaggio. Es: <i>"Invia navi da guerra al confine navale con la nazione X come atto di forza."</i></li>
        </ul>
        <p><b>Il Salto Temporale:</b> Dopo aver scritto, scegli se far passare 1 Giorno, 1 Settimana o 1 Mese. Salto breve = tattica militare. Salto lungo = riforme economiche a lungo termine.</p>

        <h3>💀 4. Condizioni di Game Over</h3>
        <p>Il governo può cadere. Assicurati che la tua <b>Stabilità Interna</b> non crolli mai a zero a causa di proteste o guerre civili, e che il tuo <b>Debito</b> non scateni una bancarotta sovrana. (Le meccaniche di sconfitta verranno espanse nei prossimi aggiornamenti).</p>
        """
        manual_lbl = QTextEdit()
        manual_lbl.setHtml(manual_text)
        manual_lbl.setReadOnly(True)
        manual_lbl.setStyleSheet("background-color: #fdfdfd; padding: 10px; font-size: 13px;")
        manual_layout.addWidget(manual_lbl)
        tabs.addTab(tab_manual, "📖 Manuale del Giocatore")

        layout.addWidget(tabs)

        btn_close = QPushButton("Chiudi Hub Operativo")
        btn_close.setMinimumHeight(35)
        btn_close.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; border-radius: 4px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def copy_to_clipboard(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copiato", "Indirizzo Toncoin copiato negli appunti!")