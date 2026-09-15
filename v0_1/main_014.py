import sys
from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog,
    QMessageBox, QLineEdit
)

import core
from db_selector import (
    ACTIVE_DB_PATH, DEFAULT_DB_PATH, SELECTION_WARNING,
    validate_la_prima_database, configure_database, clear_database_selection,
    configured_database_path,
)

# db_selector patches core.DB_PATH before the existing application modules are loaded.
from main_013_entry import AppWindow as AppWindow013
from core import GlassFrame, RED


class AppWindow(AppWindow013):
    def __init__(self):
        self._database_restart = False
        super().__init__()
        self.setWindowTitle('LA PRIMA Garage Manager 0.1.4')
        if SELECTION_WARNING:
            QTimer.singleShot(450, lambda: QMessageBox.warning(self, 'Database non disponibile', SELECTION_WARNING))

    def show_settings(self):
        super().show_settings()
        page = self.stack.currentWidget()
        if not page or not page.layout():
            return
        root = page.layout()

        card = GlassFrame(220)
        box = QVBoxLayout(card)
        title = QLabel('Database offline')
        title.setStyleSheet('font-size:19px;font-weight:800;color:#10233B;')
        box.addWidget(title)

        info = QLabel(
            'Puoi scegliere quale database LA PRIMA aprire. Il file può trovarsi nei Documenti, '
            'su un disco esterno o su una pennetta USB. Il programma usa il file direttamente '
            'nella posizione scelta: non viene copiato.'
        )
        info.setWordWrap(True)
        info.setStyleSheet('color:#405468;')
        box.addWidget(info)

        current_label = QLabel('Database attualmente in uso')
        current_label.setStyleSheet('font-weight:700;color:#20364C;')
        box.addWidget(current_label)

        current_path = QLineEdit(str(core.DB_PATH))
        current_path.setReadOnly(True)
        current_path.setObjectName('DatabasePathField')
        current_path.setStyleSheet('background:white;border:1px solid #C8D3DC;border-radius:6px;padding:7px;color:#20364C;')
        box.addWidget(current_path)

        pending = configured_database_path()
        pending_label = QLabel()
        pending_label.setObjectName('DatabasePendingLabel')
        pending_label.setWordWrap(True)
        pending_label.setStyleSheet('color:#5D6D7E;font-size:12px;')
        if pending and Path(pending) != Path(core.DB_PATH):
            pending_label.setText(f'Selezionato per il prossimo avvio: {pending}')
        elif Path(core.DB_PATH) == DEFAULT_DB_PATH:
            pending_label.setText('Modalità attuale: database predefinito nei Documenti.')
        else:
            pending_label.setText('Modalità attuale: database esterno selezionato.')
        box.addWidget(pending_label)

        row = QHBoxLayout()
        choose = QPushButton('Scegli database…')
        choose.setObjectName('ChooseDatabaseButton')
        choose.setStyleSheet(f'background:{RED};color:white;padding:9px 14px;border:0;border-radius:7px;font-weight:700;')
        default = QPushButton('Usa database predefinito')
        default.setObjectName('DefaultDatabaseButton')
        default.setStyleSheet('background:#E7EDF2;color:#20364C;padding:9px 14px;border:0;border-radius:7px;font-weight:700;')
        row.addWidget(choose)
        row.addWidget(default)
        row.addStretch()
        box.addLayout(row)

        note = QLabel(
            'Per evitare errori, il programma verifica che il file sia un database SQLite integro '
            'e che contenga le tabelle di LA PRIMA prima di accettarlo.'
        )
        note.setWordWrap(True)
        note.setStyleSheet('color:#607487;font-size:11px;')
        box.addWidget(note)

        def choose_database():
            start = str(Path(core.DB_PATH).parent if Path(core.DB_PATH).exists() else Path.home())
            filename, _ = QFileDialog.getOpenFileName(
                self,
                'Scegli il database LA PRIMA da caricare',
                start,
                'Database SQLite (*.db *.sqlite *.sqlite3);;Tutti i file (*.*)'
            )
            if not filename:
                return
            ok, error = validate_la_prima_database(filename)
            if not ok:
                QMessageBox.warning(self, 'Database non valido', error)
                return
            selected = configure_database(filename)
            pending_label.setText(f'Selezionato per il prossimo avvio: {selected}')
            answer = QMessageBox.question(
                self,
                'Database selezionato',
                f'Database selezionato:\n{selected}\n\nVuoi riavviare ora LA PRIMA e caricarlo?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if answer == QMessageBox.Yes:
                self._restart_for_database_change()

        def use_default_database():
            clear_database_selection()
            pending_label.setText(f'Selezionato per il prossimo avvio: {DEFAULT_DB_PATH}')
            if Path(core.DB_PATH) == DEFAULT_DB_PATH:
                QMessageBox.information(self, 'Database', 'Il database predefinito è già in uso.')
                return
            answer = QMessageBox.question(
                self,
                'Database predefinito',
                f'Al prossimo avvio verrà usato:\n{DEFAULT_DB_PATH}\n\nVuoi riavviare ora?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if answer == QMessageBox.Yes:
                self._restart_for_database_change()

        choose.clicked.connect(choose_database)
        default.clicked.connect(use_default_database)

        # The settings page ends with a stretch: insert the database card immediately before it.
        insert_at = max(0, root.count() - 1)
        root.insertWidget(insert_at, card)

    def _restart_for_database_change(self):
        if getattr(sys, 'frozen', False):
            program = sys.executable
            args = []
        else:
            program = sys.executable
            args = [str(Path(__file__).resolve())]
        ok = QProcess.startDetached(program, args)
        if not ok:
            QMessageBox.warning(
                self,
                'Riavvio',
                'Il database è stato selezionato, ma non sono riuscito a riavviare automaticamente. '
                'Chiudi e riapri il programma: verrà caricato al prossimo avvio.'
            )
            return
        self._database_restart = True
        self.close()

    def closeEvent(self, event):
        if self._database_restart:
            event.accept()
            return
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('LA PRIMA Garage Manager 0.1.4')
    w = AppWindow()
    w.show()
    sys.exit(app.exec())
