import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QMessageBox, QGroupBox, QScrollArea
)

from main_017 import AppWindow as AppWindow017, ensure_company_schema
from main_016 import ensure_fatturapa_schema, ensure_users_schema
from main_015 import AppWindow as AppWindow015
from core import GlassFrame, RED
from fatturapa_017 import PAYMENT_METHODS, PAYMENT_TERMS, digits, alnum

APP_VERSION = '0.1.8'


class AppWindow(AppWindow017):
    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")
        self._add_company_nav_button()

    def _add_company_nav_button(self):
        """Insert Dati Azienda directly below Impostazioni in the existing sidebar."""
        if 'Dati Azienda' in self.nav:
            return
        settings_btn = self.nav.get('Impostazioni')
        if settings_btn is None:
            return
        layout = settings_btn.parentWidget().layout()
        if layout is None:
            return
        button = QPushButton('▣   Dati Azienda')
        button.setObjectName('CompanyDataNavButton')
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(43)
        button.setStyleSheet(
            f'QPushButton{{text-align:left;padding-left:22px;color:white;background:transparent;'
            f'border:0;border-radius:7px;font-size:14px;font-weight:650;}} '
            f'QPushButton:hover{{background:#1C3C57;}} QPushButton:checked{{background:{RED};}}'
        )
        button.clicked.connect(self.show_company_data)
        insert_index = layout.indexOf(settings_btn) + 1
        layout.insertWidget(insert_index, button)
        self.nav['Dati Azienda'] = button

    def show_settings(self):
        """Keep general settings clean: company fiscal data lives only in Dati Azienda."""
        AppWindow015.show_settings(self)
        self.set_nav('Impostazioni')

    def show_company_data(self):
        self.set_nav('Dati Azienda')

        page = QWidget()
        page.setStyleSheet('background:transparent;')
        outer = QVBoxLayout(page)
        outer.setContentsMargins(22, 18, 22, 22)
        outer.setSpacing(12)

        title = QLabel('Dati Azienda')
        title.setStyleSheet('font-size:30px;font-weight:900;color:white;')
        subtitle = QLabel('Dati dell’officina utilizzati per PDF, FatturaPA e XML destinato allo SDI')
        subtitle.setStyleSheet('font-size:12px;color:#EFF4F8;')
        outer.addWidget(title)
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet('QScrollArea{background:transparent;border:0;}')
        content = QWidget()
        content.setStyleSheet('background:transparent;')
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 10, 10)
        root.setSpacing(14)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        card = GlassFrame(228)
        box = QVBoxLayout(card)
        box.setContentsMargins(20, 18, 20, 20)
        box.setSpacing(14)

        intro = QLabel(
            'Compila questi dati una sola volta. Verranno salvati nel database attualmente in uso '
            'e richiamati automaticamente quando generi una fattura elettronica XML FatturaPA.'
        )
        intro.setWordWrap(True)
        intro.setStyleSheet('color:#405468;font-size:12px;')
        box.addWidget(intro)

        self._company_widgets = {}

        fiscal = QGroupBox('Anagrafica fiscale azienda')
        fiscal.setStyleSheet('QGroupBox{font-weight:800;color:#20364C;margin-top:10px;} QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}')
        ff = QFormLayout(fiscal)
        ff.setLabelAlignment(Qt.AlignRight)
        fields = [
            ('sdi_business_name', 'Ragione sociale / Denominazione'),
            ('sdi_vat_number', 'Partita IVA'),
            ('sdi_tax_code', 'Codice Fiscale'),
            ('sdi_tax_regime', 'Regime fiscale'),
            ('sdi_address', 'Indirizzo sede'),
            ('sdi_street_number', 'Numero civico'),
            ('sdi_zip_code', 'CAP'),
            ('sdi_city', 'Comune'),
            ('sdi_province', 'Provincia'),
            ('sdi_country', 'Nazione'),
            ('sdi_phone', 'Telefono'),
            ('sdi_email', 'Email'),
            ('sdi_pec', 'PEC aziendale'),
        ]
        for key, label in fields:
            w = QLineEdit(self.db.setting(key))
            w.setObjectName('Company_' + key)
            self._company_widgets[key] = w
            ff.addRow(label, w)
        self._company_widgets['sdi_vat_number'].setPlaceholderText('11 cifre')
        self._company_widgets['sdi_tax_regime'].setPlaceholderText('es. RF01')
        self._company_widgets['sdi_country'].setText(self._company_widgets['sdi_country'].text() or 'IT')
        self._company_widgets['sdi_country'].setMaxLength(2)
        self._company_widgets['sdi_province'].setMaxLength(2)
        self._company_widgets['sdi_zip_code'].setMaxLength(5)
        box.addWidget(fiscal)

        rea = QGroupBox('Registro Imprese / REA (se applicabile)')
        rea.setStyleSheet(fiscal.styleSheet())
        rf = QFormLayout(rea)
        for key, label in [
            ('sdi_rea_office', 'Ufficio REA / Provincia'),
            ('sdi_rea_number', 'Numero REA'),
            ('sdi_share_capital', 'Capitale sociale'),
        ]:
            w = QLineEdit(self.db.setting(key))
            w.setObjectName('Company_' + key)
            self._company_widgets[key] = w
            rf.addRow(label, w)
        self._company_widgets['sdi_rea_office'].setMaxLength(2)

        sole = QComboBox()
        sole.setObjectName('Company_sdi_sole_member')
        sole.addItem('Non indicato', '')
        sole.addItem('Socio unico', 'SU')
        sole.addItem('Più soci', 'SM')
        sole.setCurrentIndex(max(0, sole.findData(self.db.setting('sdi_sole_member'))))
        self._company_widgets['sdi_sole_member'] = sole
        rf.addRow('Assetto societario', sole)

        liq = QComboBox()
        liq.setObjectName('Company_sdi_liquidation_status')
        liq.addItem('Non in liquidazione', 'LN')
        liq.addItem('In liquidazione', 'LS')
        liq.setCurrentIndex(max(0, liq.findData(self.db.setting('sdi_liquidation_status') or 'LN')))
        self._company_widgets['sdi_liquidation_status'] = liq
        rf.addRow('Stato liquidazione', liq)
        box.addWidget(rea)

        payment = QGroupBox('Pagamenti predefiniti')
        payment.setStyleSheet(fiscal.styleSheet())
        pf = QFormLayout(payment)
        iban = QLineEdit(self.db.setting('sdi_iban'))
        iban.setObjectName('Company_sdi_iban')
        bank = QLineEdit(self.db.setting('sdi_bank_name'))
        bank.setObjectName('Company_sdi_bank_name')
        self._company_widgets['sdi_iban'] = iban
        self._company_widgets['sdi_bank_name'] = bank
        pf.addRow('IBAN aziendale', iban)
        pf.addRow('Banca', bank)

        terms = QComboBox()
        terms.setObjectName('Company_sdi_default_payment_terms')
        for code, label in PAYMENT_TERMS.items():
            terms.addItem(f'{code} - {label}', code)
        terms.setCurrentIndex(max(0, terms.findData(self.db.setting('sdi_default_payment_terms') or 'TP02')))
        self._company_widgets['sdi_default_payment_terms'] = terms
        pf.addRow('Condizioni predefinite', terms)

        method = QComboBox()
        method.setObjectName('Company_sdi_default_payment_method')
        for code, label in PAYMENT_METHODS.items():
            method.addItem(f'{code} - {label}', code)
        method.setCurrentIndex(max(0, method.findData(self.db.setting('sdi_default_payment_method') or 'MP05')))
        self._company_widgets['sdi_default_payment_method'] = method
        pf.addRow('Modalità predefinita', method)
        box.addWidget(payment)

        actions = QHBoxLayout()
        save = QPushButton('Salva Dati Azienda')
        save.setObjectName('SaveCompanyDataButton')
        save.setStyleSheet(f'background:{RED};color:white;font-weight:800;padding:11px 18px;border-radius:7px;')
        verify = QPushButton('Verifica dati obbligatori')
        verify.setObjectName('VerifyCompanyDataButton')
        verify.setStyleSheet('background:#E7EDF2;color:#20364C;font-weight:700;padding:11px 18px;border-radius:7px;')
        actions.addWidget(save)
        actions.addWidget(verify)
        actions.addStretch()
        box.addLayout(actions)

        status = QLabel('Le modifiche vengono salvate solo quando premi “Salva Dati Azienda”.')
        status.setObjectName('CompanySaveStatus')
        status.setWordWrap(True)
        status.setStyleSheet('color:#607487;font-size:11px;')
        box.addWidget(status)

        root.addWidget(card)
        root.addStretch()

        def value_of(widget):
            return widget.currentData() if isinstance(widget, QComboBox) else widget.text().strip()

        def save_company(show_message=True):
            for key, widget in self._company_widgets.items():
                self.db.set_setting(key, value_of(widget))
            status.setText('Dati Azienda salvati correttamente nel database in uso.')
            status.setStyleSheet('color:#087A52;font-size:11px;font-weight:700;')
            if show_message:
                QMessageBox.information(self, 'Dati Azienda', 'Dati aziendali salvati correttamente.')

        def verify_company():
            errors = []
            vat = digits(self._company_widgets['sdi_vat_number'].text())
            cf = alnum(self._company_widgets['sdi_tax_code'].text())
            if len(vat) != 11:
                errors.append('Partita IVA: servono 11 cifre')
            if cf and not (11 <= len(cf) <= 16):
                errors.append('Codice Fiscale non valido')
            if not self._company_widgets['sdi_business_name'].text().strip():
                errors.append('Ragione sociale mancante')
            if not re.fullmatch(r'RF\d{2}', self._company_widgets['sdi_tax_regime'].text().strip().upper()):
                errors.append('Regime fiscale non valido (es. RF01)')
            if not self._company_widgets['sdi_address'].text().strip():
                errors.append('Indirizzo mancante')
            if len(digits(self._company_widgets['sdi_zip_code'].text())) != 5:
                errors.append('CAP: servono 5 cifre')
            if not self._company_widgets['sdi_city'].text().strip():
                errors.append('Comune mancante')
            if (self._company_widgets['sdi_country'].text().strip() or 'IT').upper() == 'IT' and len(self._company_widgets['sdi_province'].text().strip()) != 2:
                errors.append('Provincia: servono 2 lettere')
            if errors:
                QMessageBox.warning(self, 'Dati Azienda incompleti', 'Completa questi campi prima di generare FatturaPA:\n\n• ' + '\n• '.join(errors))
            else:
                QMessageBox.information(self, 'Dati Azienda', 'I dati aziendali obbligatori di base risultano compilati correttamente.')

        save.clicked.connect(save_company)
        verify.clicked.connect(verify_company)
        self._set_page(page)


__all__ = ['AppWindow', 'APP_VERSION', 'ensure_company_schema', 'ensure_fatturapa_schema', 'ensure_users_schema']
