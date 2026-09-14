import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw

from app_v5 import App as V5App
from app import RES_DIR, RED, TEXT, BLUE, GREEN, ORANGE

SIDEBAR = '#152536'
LOGO_CANDIDATES = [
    RES_DIR / 'assets' / 'la_prima_logo.png',
    RES_DIR / 'assets' / 'la_prima_logo_official.png',
]


class App(V5App):
    """V6.1: sola correzione grafica del logo/background, senza cambiare le funzioni V5."""

    def _load_assets(self):
        """Carica il logo direttamente dagli asset inclusi da PyInstaller.
        Niente base64: il file viene distribuito nell'EXE con --add-data assets;assets.
        """
        self.logo_src = None
        self.logo_tk = None
        self.logo_path = None
        self._logo_error = None

        for path in LOGO_CANDIDATES:
            try:
                if path.exists():
                    im = Image.open(path).convert('RGBA')
                    im.load()
                    self.logo_src = im
                    self.logo_path = path
                    break
            except Exception as exc:
                self._logo_error = exc

        if self.logo_src is not None:
            side = self.logo_src.copy()
            side.thumbnail((260, 118), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(side)

    def _shell(self):
        """Sidebar con il logo vero sempre mostrato sopra al menu."""
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=292)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=SIDEBAR, height=178)
        brand.pack(fill='x')
        brand.pack_propagate(False)

        if self.logo_tk is not None:
            tk.Label(brand, image=self.logo_tk, bg=SIDEBAR, bd=0).pack(pady=(18, 4))
        else:
            # fallback solo testuale se l'asset fosse davvero assente/corrotto
            tk.Label(
                brand, text='OFFICINA\n“LA PRIMA”', bg=SIDEBAR, fg='white',
                font=('Segoe UI Black', 24)
            ).pack(pady=28)

        self.nav_buttons = {}
        items = [
            ('⌂','Dashboard',self.dashboard),
            ('👥','Clienti',self.clients),
            ('🚗','Veicoli',self.vehicles),
            ('🔧','Commesse',self.jobs),
            ('▣','Appuntamenti',self.appointments),
            ('⚙','Tagliandi',self.services),
            ('▤','Preventivi',self.quotes),
            ('▤','Fatture',self._fatture),
            ('▦','Magazzino',self.inventory),
            ('▣','Fornitori',self.suppliers),
            ('◷','Scadenze',self.deadlines),
            ('▥','Report',self.report),
            ('◉','Backup',self.backup),
            ('⚙','Impostazioni',self._impostazioni),
        ]
        for icon, title, cmd in items:
            b = tk.Button(
                self.sidebar,
                text=f'{icon}   {title}',
                command=lambda n=title, c=cmd: self._go(n, c),
                anchor='w', bg=SIDEBAR, fg='white',
                activebackground=RED, activeforeground='white',
                relief='flat', bd=0, padx=28, pady=9,
                font=('Segoe UI Semibold', 11), cursor='hand2'
            )
            b.pack(fill='x', padx=14, pady=1)
            self.nav_buttons[title] = b

        tk.Label(
            self.sidebar, text='LA TUA AUTO,\nLA NOSTRA PASSIONE',
            bg=SIDEBAR, fg='white', font=('Segoe UI Semibold', 9),
            justify='center'
        ).pack(side='bottom', pady=18)

        self.body = tk.Frame(self, bg='#aebbc5')
        self.body.pack(fill='both', expand=True)

    def _go(self, name, cmd):
        for n, b in self.nav_buttons.items():
            b.configure(bg=RED if n == name else SIDEBAR)
        cmd()

    def _paint_dashboard_v4(self, event=None):
        """Home V6: logo molto visibile come vero background, pannelli sovrapposti semitrasparenti."""
        c = self._dash_canvas
        w = max(1040, c.winfo_width())
        H = self.DASH_H

        # Fondo neutro; il logo viene poi composto realmente sotto tutta l'interfaccia.
        base = Image.new('RGBA', (w, H), (178, 190, 200, 255))

        if self.logo_src is not None:
            # Logo principale: quasi tutta la larghezza, chiaramente visibile.
            logo = self.logo_src.copy()
            logo.thumbnail((int(w * 0.92), int(H * 0.48)), Image.LANCZOS)
            alpha = logo.getchannel('A').point(lambda v: int(v * 0.92))
            logo.putalpha(alpha)
            lx = (w - logo.width) // 2
            ly = 195
            base.alpha_composite(logo, (lx, ly))

            # Secondo richiamo nella parte bassa per far restare il branding visibile anche scrollando.
            logo2 = self.logo_src.copy()
            logo2.thumbnail((int(w * 0.68), int(H * 0.28)), Image.LANCZOS)
            alpha2 = logo2.getchannel('A').point(lambda v: int(v * 0.38))
            logo2.putalpha(alpha2)
            base.alpha_composite(logo2, ((w - logo2.width) // 2, 765))

        # Velo quasi impercettibile: non deve più cancellare il logo.
        base = Image.alpha_composite(base, Image.new('RGBA', (w, H), (245, 248, 250, 14)))
        draw = ImageDraw.Draw(base, 'RGBA')

        def panel(x1, y1, x2, y2, a=128, r=16):
            draw.rounded_rectangle(
                (x1, y1, x2, y2), radius=r,
                fill=(255, 255, 255, a),
                outline=(255, 255, 255, 185), width=1
            )

        pad = 24
        gap = 14
        card_y = 160
        card_h = 108
        usable = w - 2 * pad
        card_w = (usable - 3 * gap) // 4

        for i in range(4):
            x = pad + i * (card_w + gap)
            panel(x, card_y, x + card_w, card_y + card_h, 145, 14)

        cal_y = 286
        right_w = max(330, int(w * .30))
        cal_w = w - 3 * pad - right_w
        cal_h = 470
        panel(pad, cal_y, pad + cal_w, cal_y + cal_h, 118, 16)
        panel(pad + cal_w + pad, cal_y, w - pad, cal_y + 205, 142, 16)
        panel(pad + cal_w + pad, cal_y + 220, w - pad, cal_y + 365, 142, 16)

        bottom_y = cal_y + cal_h + 16
        panel(pad, bottom_y, pad + cal_w, bottom_y + 245, 140, 16)
        panel(pad + cal_w + pad, bottom_y, w - pad, bottom_y + 245, 140, 16)

        self._dash_img = ImageTk.PhotoImage(base)
        c.delete('all')
        c.create_image(0, 0, image=self._dash_img, anchor='nw')
        c.configure(scrollregion=(0, 0, w, H))

        def txt(x, y, s, size=12, weight='normal', fill='#102033', anchor='nw'):
            font = ('Segoe UI Semibold' if weight == 'bold' else 'Segoe UI', size)
            c.create_text(x, y, text=s, font=font, fill=fill, anchor=anchor)

        txt(pad, 34, 'Dashboard', 30, 'bold')
        txt(pad, 78, 'Benvenuto in Officina LA PRIMA', 15)
        txt(pad, 104, 'Gestisci il tuo lavoro, un cliente alla volta.', 12)
        now = datetime.now()
        txt(w - pad, 36, now.strftime('%d/%m/%Y'), 11, 'normal', '#102033', 'ne')
        txt(w - pad, 60, now.strftime('%H:%M'), 13, 'bold', '#102033', 'ne')

        vals = [
            ('👥','Clienti', self.db.one('SELECT COUNT(*) c FROM clients')['c'], RED, 'Totali nel database'),
            ('🚗','Veicoli', self.db.one('SELECT COUNT(*) c FROM vehicles')['c'], BLUE, 'Totali nel database'),
            ('🔧','Commesse Aperte', self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c'], ORANGE, 'In lavorazione'),
            ('✓','Auto pronte', self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'], GREEN, 'Da consegnare'),
        ]
        for i, (ico, title, val, col, sub) in enumerate(vals):
            x = pad + i * (card_w + gap)
            txt(x + 20, card_y + 20, ico, 25, 'bold', col)
            txt(x + 76, card_y + 20, title, 12, 'bold')
            txt(x + 76, card_y + 46, str(val), 27, 'bold', col)
            txt(x + 76, card_y + 80, sub, 10, 'normal', '#526372')

        txt(pad + 20, cal_y + 20, f'{self.MONTHNAME(self.cal_month)} {self.cal_year}', 20, 'bold')
        bx = pad + cal_w - 160

        c.create_rectangle(bx, cal_y + 13, bx + 38, cal_y + 45, fill='#eef2f6', outline='', tags='prev')
        c.create_text(bx + 19, cal_y + 29, text='‹', font=('Segoe UI Semibold',18), fill=TEXT, tags='prev')
        c.create_rectangle(bx + 44, cal_y + 13, bx + 82, cal_y + 45, fill='#eef2f6', outline='', tags='next')
        c.create_text(bx + 63, cal_y + 29, text='›', font=('Segoe UI Semibold',18), fill=TEXT, tags='next')
        c.create_rectangle(bx + 94, cal_y + 13, bx + 146, cal_y + 45, fill=RED, outline='', tags='today')
        c.create_text(bx + 120, cal_y + 29, text='Oggi', font=('Segoe UI Semibold',10), fill='white', tags='today')

        c.tag_bind('prev', '<Button-1>', lambda e: self._nav_month(-1))
        c.tag_bind('next', '<Button-1>', lambda e: self._nav_month(1))
        c.tag_bind('today', '<Button-1>', lambda e: self._today_month())

        # Usa il calendario V5: testi adattati e click sui giorni realmente funzionanti.
        self._draw_calendar(c, pad + 16, cal_y + 58, cal_w - 32, cal_h - 72, txt)

        rx = pad + cal_w + pad
        txt(rx + 18, cal_y + 17, '🔔  Promemoria e scadenze', 15, 'bold')
        txt(rx + 18, cal_y + 54, 'Tutti     Tagliandi     Preventivi     Appuntamenti', 9, 'bold', '#39495a')
        dn = self.db.one("SELECT COUNT(*) c FROM quotes WHERE status!='Inviato'")['c']
        txt(rx + right_w / 2, cal_y + 112, '▣', 26, 'normal', '#8996a4', 'n')
        txt(rx + right_w / 2, cal_y + 150,
            'Nessuna scadenza imminente' if dn == 0 else f'{dn} preventivi da seguire',
            12, 'bold', '#566675', 'n')

        txt(rx + 18, cal_y + 237, '▥  Stato Officina', 15, 'bold')
        st = [
            ('Tagliandi programmati', self.db.one('SELECT COUNT(*) c FROM services')['c'], BLUE),
            ('Preventivi da inviare', dn, ORANGE),
            ('Appuntamenti futuri', self.db.one("SELECT COUNT(*) c FROM appointments WHERE date>=date('now')")['c'], GREEN),
            ('Commesse in lavorazione', self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='In lavorazione'")['c'], RED),
            ('Auto pronte alla consegna', self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'], GREEN),
        ]
        yy = cal_y + 272
        for label, n, col in st:
            txt(rx + 20, yy, '●', 9, 'bold', col)
            txt(rx + 38, yy, label, 10)
            txt(w - pad - 28, yy, str(n), 10, 'bold', TEXT, 'ne')
            yy += 22

        txt(pad + 18, bottom_y + 16, '🔧  Commesse in evidenza', 15, 'bold')
        self._draw_jobs(c, pad + 18, bottom_y + 52, cal_w - 36, 165, txt)
        txt(rx + 18, bottom_y + 16, '▣  Ultimi appuntamenti', 15, 'bold')
        self._draw_apps(c, rx + 18, bottom_y + 52, right_w - 36, 165, txt)

        # Mantiene attivo il click-handler V5 per frecce, Oggi e giorni del calendario.
        c.bind('<Button-1>', self._dashboard_click_v5)


if __name__ == '__main__':
    App().mainloop()
