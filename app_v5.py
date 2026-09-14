import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import calendar

from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

from app_v4 import App as V4App
from app import RED, TEXT, MUTED, BLUE, GREEN, ORANGE, PDF_DIR
from app_visual import LOGO_IMG
from car_catalog import CAR_CATALOG


class App(V4App):
    """V5: catalogo auto locale, preventivi a voci, PDF singolo, calendario operativo."""

    def __init__(self):
        super().__init__()
        self._ensure_v5_schema()
        self.dashboard()

    def _ensure_v5_schema(self):
        self.db.c.executescript('''
            CREATE TABLE IF NOT EXISTS car_makes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS car_models(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(make_id, name),
                FOREIGN KEY(make_id) REFERENCES car_makes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS quote_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                qty REAL NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL DEFAULT 0,
                line_total REAL NOT NULL DEFAULT 0,
                FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE CASCADE
            );
        ''')
        for make, models in CAR_CATALOG.items():
            self.db.c.execute('INSERT OR IGNORE INTO car_makes(name) VALUES(?)', (make,))
            make_id = self.db.c.execute('SELECT id FROM car_makes WHERE name=?', (make,)).fetchone()[0]
            self.db.c.executemany(
                'INSERT OR IGNORE INTO car_models(make_id,name) VALUES(?,?)',
                [(make_id, m) for m in models]
            )
        self.db.c.commit()

    def _make_names(self):
        return [r['name'] for r in self.db.q('SELECT name FROM car_makes ORDER BY name')]

    def _model_names(self, make):
        return [r['name'] for r in self.db.q('''
            SELECT cm.name
            FROM car_models cm JOIN car_makes mk ON mk.id=cm.make_id
            WHERE mk.name=? ORDER BY cm.name
        ''', (make,))]

    def vehicle_dialog(self, vid=None):
        cs = self.db.q('SELECT id,name FROM clients ORDER BY name')
        if not cs:
            return messagebox.showinfo('Attenzione', 'Crea prima un cliente.')
        w = tk.Toplevel(self)
        w.title('Cliente e auto')
        w.geometry('760x540')
        w.minsize(700, 500)
        w.grab_set()
        f = self.card(w)
        f.pack(fill='both', expand=True, padx=14, pady=14)
        for i in range(2):
            f.grid_columnconfigure(i, weight=1)
        cm = {f"{r['name']} [ID {r['id']}]": r['id'] for r in cs}
        tk.Label(f, text='Cliente proprietario', bg='white', fg=MUTED).grid(row=0, column=0, sticky='w', padx=8)
        cb = ttk.Combobox(f, state='readonly', values=list(cm))
        cb.grid(row=1, column=0, columnspan=2, sticky='ew', padx=8, pady=(0, 8))
        tk.Label(f, text='Targa', bg='white', fg=MUTED).grid(row=2, column=0, sticky='w', padx=8)
        pl = ttk.Entry(f)
        pl.grid(row=3, column=0, sticky='ew', padx=8, pady=(0, 8))
        tk.Label(f, text='Marca', bg='white', fg=MUTED).grid(row=2, column=1, sticky='w', padx=8)
        brand = ttk.Combobox(f, state='readonly', values=self._make_names())
        brand.grid(row=3, column=1, sticky='ew', padx=8, pady=(0, 8))
        tk.Label(f, text='Modello', bg='white', fg=MUTED).grid(row=4, column=0, sticky='w', padx=8)
        model = ttk.Combobox(f, state='readonly', values=[])
        model.grid(row=5, column=0, sticky='ew', padx=8, pady=(0, 8))
        yr = self.field(f, 'Anno vettura', 4, 1)
        km = self.field(f, 'Km', 6, 0)
        vin = self.field(f, 'VIN / Telaio', 6, 1)

        def refresh_models(_=None, wanted=None):
            vals = self._model_names(brand.get()) if brand.get() else []
            model.configure(values=vals)
            if wanted and wanted in vals:
                model.set(wanted)
            elif vals:
                model.current(0)
            else:
                model.set('')

        brand.bind('<<ComboboxSelected>>', refresh_models)
        if vid:
            r = self.db.one('SELECT * FROM vehicles WHERE id=?', (vid,))
            [cb.set(k) for k, v in cm.items() if v == r['client_id']]
            pl.insert(0, str(r['plate'] or ''))
            existing_brand = str(r['brand'] or '')
            existing_model = str(r['model'] or '')
            makes = list(brand['values'])
            if existing_brand and existing_brand not in makes:
                brand.configure(values=makes + [existing_brand])
            brand.set(existing_brand)
            refresh_models(wanted=existing_model)
            if existing_model and existing_model not in list(model['values']):
                model.configure(values=list(model['values']) + [existing_model])
                model.set(existing_model)
            yr.insert(0, str(r['year'] or ''))
            km.insert(0, str(r['km'] or 0))
            vin.insert(0, str(r['vin'] or ''))
        else:
            cb.current(0)
            makes = self._make_names()
            if makes:
                brand.set('Fiat' if 'Fiat' in makes else makes[0])
                refresh_models()

        def save():
            if cb.get() not in cm or not pl.get().strip():
                return messagebox.showwarning('Dati mancanti', 'Seleziona il cliente e inserisci la targa.')
            if not brand.get() or not model.get():
                return messagebox.showwarning('Dati mancanti', 'Seleziona marca e modello dai menu a tendina.')
            try:
                kmi = int(km.get() or 0)
            except ValueError:
                return messagebox.showwarning('Km non validi', 'Inserisci i chilometri come numero intero.')
            vals = (cm[cb.get()], pl.get().strip().upper(), brand.get(), model.get(), yr.get().strip(), kmi, vin.get().strip())
            try:
                if vid:
                    self.db.ex('UPDATE vehicles SET client_id=?,plate=?,brand=?,model=?,year=?,km=?,vin=? WHERE id=?', vals + (vid,))
                else:
                    self.db.ex('INSERT INTO vehicles(client_id,plate,brand,model,year,km,vin) VALUES(?,?,?,?,?,?,?)', vals)
            except Exception as e:
                return messagebox.showerror('Errore', str(e))
            w.destroy()
            self.vehicles()
        self.btn(f, 'Salva', save, True).grid(row=8, column=1, sticky='e', padx=8, pady=16)

    def quotes(self):
        q = '''SELECT q.*,v.plate,c.name client FROM quotes q
               JOIN vehicles v ON v.id=q.vehicle_id
               JOIN clients c ON c.id=v.client_id ORDER BY q.id DESC'''
        rows = [(r['id'], r['number'], r['created'], r['plate'], r['client'], r['status'], f"{r['total']:.2f}", r['notes'] or '') for r in self.db.q(q)]
        self.qt = self._page(
            'Preventivi', 'Preventivi clienti',
            [('id','ID',45),('num','Numero',130),('date','Data',95),('plate','Targa',90),
             ('client','Cliente',190),('status','Stato',110),('total','Totale €',90),('notes','Note',250)],
            rows, lambda:self.quote_dialog(), self.edit_quote, self.del_quote,
            self.print_quotes, self.print_quote
        )
        self.qt.bind('<Double-1>', lambda e:self.edit_quote())

    def quote_dialog(self, qid=None):
        vs = self.db.q('''SELECT v.id,v.plate,v.brand,v.model,c.name
                          FROM vehicles v JOIN clients c ON c.id=v.client_id
                          ORDER BY c.name,v.plate''')
        if not vs:
            return messagebox.showinfo('Attenzione', 'Crea prima un veicolo.')
        w = tk.Toplevel(self)
        w.title('Preventivo')
        w.geometry('980x720')
        w.minsize(900, 650)
        w.grab_set()
        f = self.card(w)
        f.pack(fill='both', expand=True, padx=14, pady=14)
        for i in range(4):
            f.grid_columnconfigure(i, weight=1)
        f.grid_rowconfigure(7, weight=1)
        vm = {f"{r['name']} — {r['plate']} — {r['brand'] or ''} {r['model'] or ''}": r['id'] for r in vs}
        tk.Label(f, text='Cliente / Veicolo', bg='white', fg=MUTED).grid(row=0, column=0, columnspan=2, sticky='w', padx=8)
        cb = ttk.Combobox(f, state='readonly', values=list(vm))
        cb.grid(row=1, column=0, columnspan=2, sticky='ew', padx=8, pady=(0,8))
        tk.Label(f, text='Stato', bg='white', fg=MUTED).grid(row=0, column=2, sticky='w', padx=8)
        st = ttk.Combobox(f, state='readonly', values=['Bozza','Inviato','Accettato','Rifiutato'])
        st.grid(row=1, column=2, sticky='ew', padx=8, pady=(0,8))
        num = self.field(f, 'Numero preventivo', 2, 0)
        cr = self.field(f, 'Data', 2, 1)
        total_var = tk.StringVar(value='€ 0,00')
        tk.Label(f, text='Totale preventivo', bg='white', fg=MUTED).grid(row=2, column=2, sticky='w', padx=8, pady=(8,2))
        tk.Label(f, textvariable=total_var, bg='white', fg=RED, font=('Segoe UI Semibold', 18)).grid(row=3, column=2, sticky='w', padx=8, pady=(0,8))
        items_box = tk.LabelFrame(f, text='Voci del preventivo', bg='white', fg=TEXT, padx=8, pady=8)
        items_box.grid(row=4, column=0, columnspan=4, rowspan=4, sticky='nsew', padx=8, pady=10)
        for i in range(4):
            items_box.grid_columnconfigure(i, weight=1 if i == 0 else 0)
        items_box.grid_rowconfigure(2, weight=1)
        tk.Label(items_box, text='Descrizione / voce', bg='white', fg=MUTED).grid(row=0, column=0, sticky='w')
        tk.Label(items_box, text='Q.tà', bg='white', fg=MUTED).grid(row=0, column=1, sticky='w', padx=(8,0))
        tk.Label(items_box, text='Prezzo unit. €', bg='white', fg=MUTED).grid(row=0, column=2, sticky='w', padx=(8,0))
        desc_e = ttk.Entry(items_box)
        qty_e = ttk.Entry(items_box, width=10)
        price_e = ttk.Entry(items_box, width=14)
        desc_e.grid(row=1, column=0, sticky='ew')
        qty_e.grid(row=1, column=1, padx=(8,0)); qty_e.insert(0, '1')
        price_e.grid(row=1, column=2, padx=(8,0)); price_e.insert(0, '0')
        btns = tk.Frame(items_box, bg='white')
        btns.grid(row=1, column=3, padx=(10,0))
        tree = ttk.Treeview(items_box, columns=('desc','qty','unit','line'), show='headings', height=10)
        for k,l,wid,anc in [('desc','Voce / lavorazione / ricambio',470,'w'),('qty','Q.tà',70,'center'),('unit','Prezzo unit. €',120,'e'),('line','Totale €',120,'e')]:
            tree.heading(k, text=l); tree.column(k, width=wid, anchor=anc)
        tree.grid(row=2, column=0, columnspan=4, sticky='nsew', pady=(10,6))
        sb = ttk.Scrollbar(items_box, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.grid(row=2, column=4, sticky='ns', pady=(10,6))
        notes_box = tk.LabelFrame(f, text='Note generali del preventivo', bg='white', fg=TEXT, padx=8, pady=6)
        notes_box.grid(row=8, column=0, columnspan=4, sticky='ew', padx=8, pady=(4,8))
        notes = tk.Text(notes_box, height=4, wrap='word', font=('Segoe UI',10), relief='solid', bd=1)
        notes.pack(fill='x', expand=True)

        def fnum(s):
            try:
                return float(str(s).replace('€','').replace(' ','').replace(',','.'))
            except Exception:
                return 0.0

        def refresh_total():
            tot = 0.0
            for iid in tree.get_children():
                vals = tree.item(iid, 'values')
                tot += fnum(vals[3])
            total_var.set(f"€ {tot:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.'))
            return tot

        def clear_item_fields():
            desc_e.delete(0, 'end'); qty_e.delete(0, 'end'); qty_e.insert(0, '1')
            price_e.delete(0, 'end'); price_e.insert(0, '0')
            tree.selection_remove(tree.selection())
            desc_e.focus_set()

        def add_or_update_item():
            desc = desc_e.get().strip()
            if not desc:
                return messagebox.showwarning('Voce mancante', 'Inserisci la descrizione della voce del preventivo.', parent=w)
            qty = fnum(qty_e.get())
            unit = fnum(price_e.get())
            if qty <= 0:
                return messagebox.showwarning('Quantità non valida', 'La quantità deve essere maggiore di zero.', parent=w)
            vals = (desc, f'{qty:g}', f'{unit:.2f}', f'{qty*unit:.2f}')
            sel = tree.selection()
            if sel:
                tree.item(sel[0], values=vals)
            else:
                tree.insert('', 'end', values=vals)
            refresh_total(); clear_item_fields()

        def load_selected_item(_=None):
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0], 'values')
            desc_e.delete(0,'end'); desc_e.insert(0, vals[0])
            qty_e.delete(0,'end'); qty_e.insert(0, vals[1])
            price_e.delete(0,'end'); price_e.insert(0, vals[2])

        def remove_item():
            for iid in tree.selection(): tree.delete(iid)
            refresh_total(); clear_item_fields()

        self.btn(btns, 'Aggiungi / aggiorna', add_or_update_item, True).pack(side='left')
        self.btn(btns, 'Rimuovi', remove_item).pack(side='left', padx=(6,0))
        tree.bind('<<TreeviewSelect>>', load_selected_item)
        tree.bind('<Double-1>', load_selected_item)
        if qid:
            r = self.db.one('SELECT * FROM quotes WHERE id=?', (qid,))
            [cb.set(k) for k,v in vm.items() if v == r['vehicle_id']]
            num.insert(0, str(r['number'] or ''))
            cr.insert(0, str(r['created'] or ''))
            st.set(r['status'] or 'Bozza')
            notes.insert('1.0', r['notes'] or '')
            its = self.db.q('SELECT * FROM quote_items WHERE quote_id=? ORDER BY id', (qid,))
            for it in its:
                tree.insert('', 'end', values=(it['description'], f"{it['qty']:g}", f"{it['unit_price']:.2f}", f"{it['line_total']:.2f}"))
            if not its and float(r['total'] or 0) > 0:
                tree.insert('', 'end', values=('Importo preventivo precedente', '1', f"{float(r['total']):.2f}", f"{float(r['total']):.2f}"))
        else:
            cb.current(0); num.insert(0, self.next_quote()); cr.insert(0, date.today().isoformat()); st.set('Bozza')
        refresh_total()

        def save():
            if cb.get() not in vm:
                return messagebox.showwarning('Dati mancanti', 'Seleziona cliente e veicolo.', parent=w)
            if not num.get().strip():
                return messagebox.showwarning('Dati mancanti', 'Inserisci il numero del preventivo.', parent=w)
            if not tree.get_children():
                return messagebox.showwarning('Preventivo vuoto', 'Aggiungi almeno una voce al preventivo.', parent=w)
            tot = refresh_total()
            vals = (num.get().strip(), vm[cb.get()], cr.get().strip(), st.get() or 'Bozza', tot, notes.get('1.0','end').strip())
            try:
                if qid:
                    self.db.ex('UPDATE quotes SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=? WHERE id=?', vals + (qid,))
                    quote_id = qid
                    self.db.ex('DELETE FROM quote_items WHERE quote_id=?', (quote_id,))
                else:
                    cur = self.db.ex('INSERT INTO quotes(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)', vals)
                    quote_id = cur.lastrowid
                for iid in tree.get_children():
                    d, q, u, line = tree.item(iid, 'values')
                    self.db.ex('INSERT INTO quote_items(quote_id,description,qty,unit_price,line_total) VALUES(?,?,?,?,?)', (quote_id, d, fnum(q), fnum(u), fnum(line)))
            except Exception as e:
                return messagebox.showerror('Errore', str(e), parent=w)
            w.destroy(); self.quotes()
        self.btn(f, 'Salva preventivo', save, True).grid(row=9, column=3, sticky='e', padx=8, pady=12)

    def print_quote(self):
        x = self.selected(self.qt)
        if not x:
            return messagebox.showinfo('Preventivi', 'Seleziona il preventivo da stampare.')
        r = self.db.one('''SELECT q.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email
                           FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id
                           JOIN clients c ON c.id=v.client_id WHERE q.id=?''', (x,))
        items = self.db.q('SELECT * FROM quote_items WHERE quote_id=? ORDER BY id', (x,))
        p = self.pdf_path(f"Preventivo_{r['number']}")
        c = pdfcanvas.Canvas(str(p), pagesize=A4)
        W,H = A4
        if LOGO_IMG.exists():
            try:
                c.drawImage(str(LOGO_IMG), 15*mm, H-38*mm, width=62*mm, height=24*mm, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        c.setFillColor(colors.HexColor(RED)); c.setFont('Helvetica-Bold', 18)
        c.drawRightString(W-16*mm, H-22*mm, 'PREVENTIVO')
        c.setFillColor(colors.HexColor('#333333')); c.setFont('Helvetica-Bold', 10)
        c.drawRightString(W-16*mm, H-30*mm, str(r['number']))
        c.setFont('Helvetica', 9)
        c.drawRightString(W-16*mm, H-36*mm, f"Data: {r['created']}   Stato: {r['status']}")
        c.setStrokeColor(colors.HexColor(RED)); c.setLineWidth(1.2)
        c.line(15*mm, H-44*mm, W-15*mm, H-44*mm)
        y = H-56*mm
        c.setFont('Helvetica-Bold', 10); c.setFillColor(colors.HexColor('#555555'))
        c.drawString(15*mm, y, 'CLIENTE'); c.drawString(112*mm, y, 'VEICOLO')
        y -= 6*mm
        c.setFont('Helvetica', 10); c.setFillColor(colors.black)
        c.drawString(15*mm, y, str(r['client'] or ''))
        c.drawString(112*mm, y, f"{r['brand'] or ''} {r['model'] or ''}".strip())
        y -= 5*mm
        c.setFont('Helvetica', 8.5)
        c.drawString(15*mm, y, f"Tel: {r['phone'] or '-'}   Email: {r['email'] or '-'}")
        c.drawString(112*mm, y, f"Targa: {r['plate'] or '-'}   Anno: {r['year'] or '-'}")
        y -= 12*mm
        x0=15*mm; col_desc=102*mm; col_qty=20*mm; col_unit=28*mm
        def header(ypos):
            c.setFillColor(colors.HexColor('#e9eef3')); c.rect(x0, ypos-6*mm, W-30*mm, 8*mm, fill=1, stroke=0)
            c.setFillColor(colors.black); c.setFont('Helvetica-Bold', 8.5)
            c.drawString(x0+2*mm, ypos-3.5*mm, 'Descrizione')
            c.drawRightString(x0+col_desc+col_qty-2*mm, ypos-3.5*mm, 'Q.tà')
            c.drawRightString(x0+col_desc+col_qty+col_unit-2*mm, ypos-3.5*mm, 'Prezzo unit.')
            c.drawRightString(W-17*mm, ypos-3.5*mm, 'Totale')
            return ypos-10*mm
        y = header(y)
        c.setFont('Helvetica', 9)
        for it in items:
            if y < 42*mm:
                c.showPage(); y=H-24*mm; y=header(y)
            desc = str(it['description'] or '')
            if len(desc) > 58: desc = desc[:55] + '...'
            c.setFillColor(colors.black)
            c.drawString(x0+2*mm, y, desc)
            c.drawRightString(x0+col_desc+col_qty-2*mm, y, f"{it['qty']:g}")
            c.drawRightString(x0+col_desc+col_qty+col_unit-2*mm, y, f"€ {it['unit_price']:.2f}")
            c.drawRightString(W-17*mm, y, f"€ {it['line_total']:.2f}")
            c.setStrokeColor(colors.HexColor('#dddddd')); c.line(x0, y-2*mm, W-15*mm, y-2*mm)
            y -= 7*mm
        y -= 4*mm
        c.setFillColor(colors.HexColor(RED)); c.setFont('Helvetica-Bold', 13)
        c.drawRightString(W-16*mm, y, f"TOTALE: € {float(r['total'] or 0):.2f}")
        y -= 12*mm
        if r['notes']:
            c.setFillColor(colors.HexColor('#555555')); c.setFont('Helvetica-Bold', 9); c.drawString(15*mm, y, 'NOTE')
            y -= 5*mm; c.setFont('Helvetica', 9); c.setFillColor(colors.black)
            for raw in str(r['notes']).splitlines() or ['']:
                line = raw
                while len(line) > 95:
                    c.drawString(15*mm, y, line[:95]); line=line[95:]; y-=5*mm
                c.drawString(15*mm, y, line); y-=5*mm
        c.setFont('Helvetica', 7.5); c.setFillColor(colors.HexColor('#777777'))
        c.drawString(15*mm, 14*mm, f"Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')} - Officina LA PRIMA")
        c.save(); self.open_pdf(p)

    def _paint_dashboard_v4(self, event=None):
        super()._paint_dashboard_v4(event)
        self._dash_canvas.bind('<Button-1>', self._dashboard_click_v5)

    def _nav_month(self, step):
        self.cal_month += step
        if self.cal_month < 1:
            self.cal_month = 12; self.cal_year -= 1
        elif self.cal_month > 12:
            self.cal_month = 1; self.cal_year += 1
        self._paint_dashboard_v4()

    def _today_month(self):
        self.cal_year = date.today().year
        self.cal_month = date.today().month
        self._paint_dashboard_v4()

    def _dashboard_click_v5(self, event):
        c = self._dash_canvas
        x = c.canvasx(event.x); y = c.canvasy(event.y)
        w = max(1040, c.winfo_width())
        pad=24; cal_y=286; right_w=max(330,int(w*.30)); cal_w=w-3*pad-right_w
        bx=pad+cal_w-160
        if bx <= x <= bx+38 and cal_y+13 <= y <= cal_y+45:
            return self._nav_month(-1)
        if bx+44 <= x <= bx+82 and cal_y+13 <= y <= cal_y+45:
            return self._nav_month(1)
        if bx+94 <= x <= bx+146 and cal_y+13 <= y <= cal_y+45:
            return self._today_month()
        for x1,y1,x2,y2,ds in getattr(self, '_calendar_hitboxes', []):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return self.app_dialog(ds)

    def _draw_calendar(self, c, x, y, w, h, txt):
        cols=7; rows=6; head=30; cw=w/cols; rh=(h-head)/rows
        self._calendar_hitboxes=[]
        for i,n in enumerate(['Lun','Mar','Mer','Gio','Ven','Sab','Dom']):
            txt(x+i*cw+cw/2, y+7, n, 9, 'bold', '#223449', 'n')
        for i in range(cols+1):
            c.create_line(x+i*cw, y+head, x+i*cw, y+h, fill='#b8c4cf')
        for r in range(rows+1):
            c.create_line(x, y+head+r*rh, x+w, y+head+r*rh, fill='#b8c4cf')
        weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(self.cal_year,self.cal_month)
        while len(weeks)<6: weeks.append([0]*7)
        first=f'{self.cal_year:04d}-{self.cal_month:02d}-01'
        last=calendar.monthrange(self.cal_year,self.cal_month)[1]
        final=f'{self.cal_year:04d}-{self.cal_month:02d}-{last:02d}'
        apps=self.db.q('''SELECT a.date,a.time,a.reason,v.plate,c.name client
                          FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id
                          LEFT JOIN clients c ON c.id=v.client_id
                          WHERE a.date BETWEEN ? AND ? ORDER BY a.date,a.time''',(first,final))
        by={}
        for a in apps:
            by.setdefault(int(a['date'][-2:]),[]).append(a)
        today=date.today()
        maxchars=max(11, int((cw-16)/6.2))
        for rr,wk in enumerate(weeks[:6]):
            for cc,day in enumerate(wk):
                if not day: continue
                x1=x+cc*cw; y1=y+head+rr*rh; x2=x1+cw; y2=y1+rh
                ds=f'{self.cal_year:04d}-{self.cal_month:02d}-{day:02d}'
                self._calendar_hitboxes.append((x1,y1,x2,y2,ds))
                if date(self.cal_year,self.cal_month,day)==today:
                    c.create_rectangle(x1+5,y1+5,x1+28,y1+26,fill=BLUE,outline='')
                    c.create_text(x1+16.5,y1+15.5,text=str(day),font=('Segoe UI Semibold',9),fill='white')
                else:
                    c.create_text(x1+8,y1+7,text=str(day),font=('Segoe UI Semibold',9),fill=TEXT,anchor='nw')
                events=by.get(day,[])
                for j,a in enumerate(events[:2]):
                    ey=y1+29+j*17
                    label=' '.join(v for v in [a['time'] or '', a['plate'] or '', a['reason'] or ''] if v).strip()
                    if len(label)>maxchars: label=label[:maxchars-1]+'…'
                    fill='#dbeafe' if j==0 else '#d9f3e9'
                    fg='#0756a1' if j==0 else '#087a52'
                    c.create_rectangle(x1+5,ey,x2-5,ey+14,fill=fill,outline='')
                    c.create_text(x1+8,ey+7,text=label,font=('Segoe UI',7),fill=fg,anchor='w')
                if len(events)>2:
                    c.create_text(x2-7,y2-7,text=f'+{len(events)-2}',font=('Segoe UI Semibold',7),fill=RED,anchor='se')


if __name__ == '__main__':
    App().mainloop()
