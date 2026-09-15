import sys

from PySide6.QtCore import Qt, QEvent, QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QStackedWidget, QSizePolicy, QLayout, QDialog, QTableWidget,
    QHeaderView, QAbstractItemView
)

import core
from main_011 import UserBackgroundWidget, UI_LOGO
from main_021 import (
    AppWindow as AppWindow021, UserLoginDialog, ensure_recovery_schema,
    ensure_final_schema, ensure_customer_type_schema, ensure_company_schema,
    ensure_fatturapa_schema, ensure_users_schema, set_recovery_code,
    verify_recovery_code, reset_user_password, recovery_is_configured,
)

APP_VERSION = '0.1.11-R'


class FlowLayout(QLayout):
    """Simple wrapping layout used by table-page toolbars on narrow screens."""
    def __init__(self, parent=None, margin=0, hspacing=6, vspacing=6):
        super().__init__(parent)
        self._items = []
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.takeAt(0):
            pass

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        for item in self._items:
            widget = item.widget()
            if widget is None:
                continue
            space_x = self._hspacing
            space_y = self._vspacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()


class AppWindow(AppWindow021):
    """0.1.11 with a responsive shell for notebooks, DPI scaling and smaller displays."""

    def _build_ui(self):
        ui_logo = QPixmap(UI_LOGO)
        if ui_logo.isNull():
            raise RuntimeError('Impossibile caricare il logo ufficiale incorporato')

        root = QWidget()
        self.setCentralWidget(root)
        hl = QHBoxLayout(root)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        side = QFrame()
        side.setObjectName('ResponsiveSidebar')
        side.setFixedWidth(250)
        side.setStyleSheet(f'QFrame#ResponsiveSidebar{{background:{core.NAVY};border:0;}}')
        sl = QVBoxLayout(side)
        sl.setContentsMargins(10, 10, 8, 10)
        sl.setSpacing(6)

        brand = QLabel()
        brand.setObjectName('ResponsiveBrandLogo')
        brand.setAlignment(Qt.AlignCenter)
        brand.setFixedHeight(140)
        brand.setPixmap(ui_logo.scaled(225, 124, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.setToolTip('Logo ufficiale Officina LA PRIMA')
        sl.addWidget(brand)

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName('ResponsiveSidebarScroll')
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setStyleSheet(
            'QScrollArea{background:transparent;border:0;}'
            'QScrollArea > QWidget > QWidget{background:transparent;}'
            'QScrollBar:vertical{background:transparent;width:9px;margin:0;}'
            'QScrollBar::handle:vertical{background:#5B7287;border-radius:4px;min-height:30px;}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}'
        )
        nav_body = QWidget()
        nav_body.setObjectName('ResponsiveSidebarBody')
        nav_body.setStyleSheet('background:transparent;')
        nv = QVBoxLayout(nav_body)
        nv.setContentsMargins(2, 0, 4, 2)
        nv.setSpacing(3)

        self.nav = {}
        items = [
            ('⌂', 'Dashboard', self.show_dashboard), ('👥', 'Clienti', self.show_clients),
            ('🚗', 'Veicoli', self.show_vehicles), ('🔧', 'Commesse', self.show_jobs),
            ('▣', 'Appuntamenti', self.show_appointments), ('⚙', 'Tagliandi', self.show_services),
            ('▤', 'Preventivi', self.show_quotes), ('▤', 'Fatture', self.show_invoices),
            ('▦', 'Magazzino', self.show_inventory), ('▣', 'Fornitori', self.show_suppliers),
            ('◷', 'Scadenze', self.show_deadlines), ('▥', 'Report', self.show_report),
            ('◉', 'Backup', self.show_backup), ('⚙', 'Impostazioni', self.show_settings),
        ]
        for icon, name, fn in items:
            b = QPushButton(f'{icon}   {name}')
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(38)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(fn)
            nv.addWidget(b)
            self.nav[name] = b

        nv.addStretch()
        tag = QLabel('L A  T U A  A U T O ,\nL A  N O S T R A  P A S S I O N E')
        tag.setObjectName('ResponsiveTagline')
        tag.setAlignment(Qt.AlignCenter)
        tag.setWordWrap(True)
        nv.addWidget(tag)
        nav_scroll.setWidget(nav_body)
        sl.addWidget(nav_scroll, 1)
        hl.addWidget(side)

        self.bg = UserBackgroundWidget(self.db)
        bl = QVBoxLayout(self.bg)
        bl.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.setAttribute(Qt.WA_TranslucentBackground, True)
        self.stack.setStyleSheet('QStackedWidget{background:transparent;border:0;}')
        bl.addWidget(self.stack)
        hl.addWidget(self.bg, 1)

        self._responsive_side = side
        self._responsive_brand = brand
        self._responsive_nav_scroll = nav_scroll
        self._responsive_tagline = tag
        self._ui_logo_ok = True

    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._fit_window_to_screen()
        self._apply_responsive_metrics()
        QTimer.singleShot(0, self._refresh_current_page_layout)

    def _available_geometry(self):
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1366, 768)

    def _fit_window_to_screen(self):
        geo = self._available_geometry()
        min_w = min(900, max(700, int(geo.width() * 0.68)))
        min_h = min(620, max(450, int(geo.height() * 0.68)))
        self.setMinimumSize(min_w, min_h)

        if geo.width() < 1650 or geo.height() < 920:
            target_w = max(min_w, geo.width() - 16)
            target_h = max(min_h, geo.height() - 16)
        else:
            target_w = min(1580, int(geo.width() * 0.90))
            target_h = min(980, int(geo.height() * 0.88))
        target_w = min(target_w, geo.width())
        target_h = min(target_h, geo.height())
        self.resize(target_w, target_h)
        self.move(
            geo.x() + max(0, (geo.width() - target_w) // 2),
            geo.y() + max(0, (geo.height() - target_h) // 2),
        )

    def _profile(self):
        geo = self._available_geometry()
        effective_w = min(max(self.width(), 1), geo.width())
        effective_h = min(max(self.height(), 1), geo.height())
        if effective_w <= 1050 or effective_h <= 620:
            return 'small'
        if effective_w <= 1400 or effective_h <= 820:
            return 'compact'
        return 'desktop'

    def _apply_responsive_metrics(self):
        if not hasattr(self, '_responsive_side'):
            return
        profile = self._profile()
        if profile == 'small':
            side_w, brand_h, btn_h, font_px, pad = 188, 96, 33, 11, 11
        elif profile == 'compact':
            side_w, brand_h, btn_h, font_px, pad = 220, 116, 36, 12, 14
        else:
            side_w, brand_h, btn_h, font_px, pad = 270, 148, 41, 13, 18

        self._responsive_side.setFixedWidth(side_w)
        self._responsive_brand.setFixedHeight(brand_h)
        pm = QPixmap(UI_LOGO)
        if not pm.isNull():
            self._responsive_brand.setPixmap(
                pm.scaled(side_w - 22, brand_h - 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        for button in self.nav.values():
            button.setMinimumHeight(btn_h)
            button.setMaximumHeight(btn_h + 5)
            button.setStyleSheet(
                f'QPushButton{{text-align:left;padding-left:{pad}px;color:white;background:transparent;'
                f'border:0;border-radius:7px;font-size:{font_px}px;font-weight:650;}} '
                f'QPushButton:hover{{background:#1C3C57;}} QPushButton:checked{{background:{core.RED};}}'
            )
        self._responsive_tagline.setVisible(self._available_geometry().height() >= 610)
        self._responsive_tagline.setStyleSheet(
            f'color:white;font-size:{9 if profile != "small" else 8}px;letter-spacing:1px;padding:5px;'
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_responsive_side'):
            self._apply_responsive_metrics()
            QTimer.singleShot(0, self._refresh_current_page_layout)

    def _set_page(self, page):
        super()._set_page(page)
        self._make_toolbar_responsive(page)
        self._adapt_page(page)

    def _make_toolbar_responsive(self, page):
        if not isinstance(page, core.TablePage) or getattr(page, '_responsive_toolbar_done', False):
            return
        old = page.toolbar
        card_layout = page.card.layout()
        if old is None or card_layout is None:
            return
        index = 0
        for i in range(card_layout.count()):
            item = card_layout.itemAt(i)
            if item is not None and item.layout() is old:
                index = i
                card_layout.takeAt(i)
                break

        buttons = []
        while old.count():
            item = old.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                buttons.append(widget)

        wrap = QWidget()
        wrap.setObjectName('ResponsiveToolbarWrap')
        wrap.setStyleSheet('background:transparent;')
        flow = FlowLayout(wrap, 0, 6, 6)
        for button in buttons:
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            flow.addWidget(button)
        card_layout.insertWidget(index, wrap)
        page.toolbar = flow
        page._responsive_toolbar_done = True
        old.setParent(None)
        old.deleteLater()

    def _adapt_page(self, page):
        compact = self._profile() != 'desktop'
        for table in page.findChildren(QTableWidget):
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            header = table.horizontalHeader()
            if compact and table.columnCount() > 6:
                header.setSectionResizeMode(QHeaderView.Interactive)
                table.resizeColumnsToContents()
                for col in range(table.columnCount()):
                    width = table.columnWidth(col)
                    table.setColumnWidth(col, min(190, max(72, width)))
            else:
                header.setSectionResizeMode(QHeaderView.Stretch)

    def _refresh_current_page_layout(self):
        if hasattr(self, 'stack') and self.stack.currentWidget() is not None:
            self._adapt_page(self.stack.currentWidget())
            self.stack.currentWidget().updateGeometry()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and isinstance(obj, QDialog):
            QTimer.singleShot(0, lambda d=obj: self._fit_dialog_to_screen(d))
        return super().eventFilter(obj, event)

    def _fit_dialog_to_screen(self, dialog):
        if dialog is None or not dialog.isVisible():
            return
        screen = dialog.screen() or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        max_w = max(500, int(geo.width() * 0.96))
        max_h = max(400, int(geo.height() * 0.94))
        dialog.setMinimumWidth(min(dialog.minimumWidth(), max_w))
        dialog.setMinimumHeight(min(dialog.minimumHeight(), max_h))
        target_w = min(max(dialog.width(), min(dialog.sizeHint().width(), max_w)), max_w)
        target_h = min(max(dialog.height(), min(dialog.sizeHint().height(), max_h)), max_h)
        dialog.resize(target_w, target_h)
        dialog.move(
            geo.x() + max(0, (geo.width() - target_w) // 2),
            geo.y() + max(0, (geo.height() - target_h) // 2),
        )


__all__ = [
    'AppWindow', 'UserLoginDialog', 'APP_VERSION', 'FlowLayout',
    'ensure_recovery_schema', 'ensure_final_schema', 'ensure_customer_type_schema',
    'ensure_company_schema', 'ensure_fatturapa_schema', 'ensure_users_schema',
    'set_recovery_code', 'verify_recovery_code', 'reset_user_password',
    'recovery_is_configured',
]
