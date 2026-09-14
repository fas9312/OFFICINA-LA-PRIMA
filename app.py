import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, sys, os, shutil, calendar
from pathlib import Path
from datetime import date, datetime
from PIL import Image, ImageTk
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm

APP_NAME='LA PRIMA Garage Manager'
RED='#c51724'; NAVY='#182332'; BG='#eef2f5'; TEXT='#172033'; MUTED='#64748b'
BLUE='#0b69d1'; GREEN='#159b6b'; ORANGE='#f28c18'
STATUSES=['Accettata','Da diagnosticare','Preventivo','Autorizzata','In lavorazione','Attesa ricambi','Pronta','Consegnata']
MONTHS=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre']

if getattr(sys,'frozen',False):
    RES_DIR=Path(getattr(sys,'_MEIPASS',Path(sys.executable).resolve().parent))
else:
    RES_DIR=Path(__file__).resolve().parent
DATA_DIR=Path.home()/'Documents'/'LA_PRIMA_Garage_Manager'; DATA_DIR.mkdir(parents=True,exist_ok=True)
DB_PATH=DATA_DIR/'la_prima_garage.db'; PDF_DIR=DATA_DIR/'PDF'; BACKUP_DIR=DATA_DIR/'Backup'; PDF_DIR.mkdir(exist_ok=True); BACKUP_DIR.mkdir(exist_ok=True)
BG_IMG=RES_DIR/'assets'/'la_prima_bg.jpg'; LOGO_IMG=RES_DIR/'assets'/'la_prima_logo.png'

class DB:
    def __init__(self):
        self.c=sqlite3.connect(DB_PATH); self.c.row_factory=sqlite3.Row; self.c.execute('PRAGMA foreign_keys=ON'); self.schema()
    def schema(self):
        self.c.executescript('''
        CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT,email TEXT,notes TEXT);
        CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY AUTOINCREMENT,client_id INTEGER NOT NULL,plate TEXT NOT NULL UNIQUE,brand TEXT,model TEXT,year TEXT,km INTEGER DEFAULT 0,vin TEXT,FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,number TEXT UNIQUE NOT NULL,vehicle_id INTEGER NOT NULL,opened TEXT NOT NULL,issue TEXT,diagnosis TEXT,status TEXT NOT NULL,labor REAL DEFAULT 0,parts REAL DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY AUTOINCREMENT,vehicle_id INTEGER,date TEXT NOT NULL,time TEXT,reason TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY AUTOINCREMENT,vehicle_id INTEGER NOT NULL,service_date TEXT NOT NULL,km INTEGER DEFAULT 0,engine_oil TEXT,oil_filter INTEGER DEFAULT 0,air_filter INTEGER DEFAULT 0,fuel_filter INTEGER DEFAULT 0,cabin_filter INTEGER DEFAULT 0,other_filters TEXT,next_service_km INTEGER DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,description TEXT NOT NULL,qty REAL DEFAULT 0,min_qty REAL DEFAULT 0,cost REAL DEFAULT 0,sale REAL DEFAULT 0,supplier TEXT);
        CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT,email TEXT,notes TEXT);
        CREATE TABLE IF NOT EXISTS quotes(id INTEGER PRIMARY KEY AUTOINCREMENT,number TEXT UNIQUE NOT NULL,vehicle_id INTEGER NOT NULL,created TEXT NOT NULL,status TEXT NOT NULL,total REAL DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        '''); self.c.commit()
    def q(self,s,p=()): return self.c.execute(s,p).fetchall()
    def one(self,s,p=()): return self.c.execute(s,p).fetchone()
    def ex(self,s,p=()): cur=self.c.cursor(); cur.execute(s,p); self.c.commit(); return cur

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_NAME); self.geometry('1536x960'); self.minsize(1180,760); self.db=DB(); self.cal_year=date.today().year; self.cal_month=date.today().month; self.protocol('WM_DELETE_WINDOW',self.on_close)
        st=ttk.Style(self); st.theme_use('clam'); st.configure('Treeview',rowheight=30,font=('Segoe UI',10),background='white',fieldbackground='white'); st.configure('Treeview.Heading',font=('Segoe UI Semibold',10),background='#e9eef3',foreground=TEXT)
        self._load_assets(); self._shell(); self.dashboard()
    def _load_assets(self):
        self.bg_src=None; self.logo_tk=None
        try:self.bg_src=Image.open(BG_IMG).convert('RGB')
        except:pass
        try:
            im=Image.open(LOGO_IMG).convert('RGBA'); im.thumbnail((250,105),Image.LANCZOS); self.logo_tk=ImageTk.PhotoImage(im)
        except:pass
    def _shell(self):
        self.sidebar=tk.Frame(self,bg=NAVY,width=292); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        lb=tk.Frame(self.sidebar,bg=NAVY,height=165); lb.pack(fill='x'); lb.pack_propagate(False)
        if self.logo_tk: tk.Label(lb,image=self.logo_tk,bg=NAVY).pack(pady=(22,4))
        else: tk.Label(lb,text='OFFICINA\nLA PRIMA',bg=NAVY,fg='white',font=('Segoe UI Black',24)).pack(pady=28)
        for icon,t,cmd in [('⌂','Dashboard',self.dashboard),('👥','Clienti',self.clients),('🚗','Veicoli',self.vehicles),('🔧','Commesse',self.jobs),('▣','Appuntamenti',self.appointments),('⚙','Tagliandi',self.services),('▤','Preventivi',self.quotes),('▦','Magazzino',self.inventory),('▣','Fornitori',self.suppliers),('◷','Scadenze',self.deadlines),('▥','Report',self.report),('◉','Backup',self.backup)]:
            tk.Button(self.sidebar,text=f'{icon}   {t}',command=cmd,anchor='w',bg=NAVY,fg='white',activebackground=RED,activeforeground='white',relief='flat',padx=28,pady=11,font=('Segoe UI Semibold',11),cursor='hand2').pack(fill='x',padx=14,pady=1)
        tk.Label(self.sidebar,text='LA TUA AUTO,\nLA NOSTRA PASSIONE',bg=NAVY,fg='white',font=('Segoe UI Semibold',9),justify='center').pack(side='bottom',pady=22)
        self.body=tk.Frame(self,bg=BG); self.body.pack(fill='both',expand=True)
    def clear(self):
        for w in self.body.winfo_children():w.destroy()
    def set_bg(self):
        if not self.bg_src:return
        c=tk.Canvas(self.body,highlightthickness=0,bg=BG); c.place(relx=0,rely=0,relwidth=1,relheight=1)
        def draw(e=None):
            w=max(1,c.winfo_width()); h=max(1,c.winfo_height()); im=self.bg_src.copy(); ir=im.width/im.height; wr=w/h
            if ir>wr: nw=int(im.height*wr); x=(im.width-nw)//2; im=im.crop((x,0,x+nw,im.height))
            else: nh=int(im.width/wr); y=(im.height-nh)//2; im=im.crop((0,y,im.width,y+nh))
            im=im.resize((w,h),Image.LANCZOS); ov=Image.new('RGBA',(w,h),(238,244,248,150)); im=Image.alpha_composite(im.convert('RGBA'),ov); c._im=ImageTk.PhotoImage(im); c.delete('bg'); c.create_image(0,0,image=c._im,anchor='nw',tags='bg'); c.tag_lower('bg')
        c.bind('<Configure>',draw)
    def card(self,p):return tk.Frame(p,bg='white',highlightbackground='#d7dee6',highlightthickness=1)
    def btn(self,p,text,cmd,primary=False):return tk.Button(p,text=text,command=cmd,bg=RED if primary else '#edf1f5',fg='white' if primary else TEXT,relief='flat',padx=14,pady=8,font=('Segoe UI Semibold',9),cursor='hand2')
    def field(self,p,label,r,c):tk.Label(p,text=label,bg='white',fg=MUTED,font=('Segoe UI',9)).grid(row=r,column=c,sticky='w',padx=8,pady=(8,2));e=ttk.Entry(p);e.grid(row=r+1,column=c,sticky='ew',padx=8,pady=(0,8));return e
    def selected(self,t):
        s=t.selection();return int(t.item(s[0],'values')[0]) if s else None
    def wrap(self,title,sub=''):
        self.clear();self.set_bg();w=tk.Frame(self.body,bg='#f7f9fb');w.place(relx=.02,rely=.02,relwidth=.96,relheight=.96);h=tk.Frame(w,bg='white');h.pack(fill='x',padx=24,pady=(18,10));tk.Label(h,text=title,bg='white',fg=TEXT,font=('Segoe UI Semibold',25)).pack(anchor='w');tk.Label(h,text=sub,bg='white',fg=MUTED,font=('Segoe UI',10)).pack(anchor='w');return w
    def _page(self,title,sub,cols,rows,add,edit,delete,print_all,print_one=None):
        w=self.wrap(title,sub);c=self.card(w);c.pack(fill='both',expand=True,padx=24,pady=(0,20));top=tk.Frame(c,bg='white');top.pack(fill='x',padx=10,pady=10);self.btn(top,'+ Nuovo',add,True).pack(side='left');self.btn(top,'Modifica',edit).pack(side='left',padx=4);self.btn(top,'Elimina',delete).pack(side='left');self.btn(top,'Stampa reparto PDF',print_all).pack(side='right');
        if print_one:self.btn(top,'Stampa selezionato',print_one).pack(side='right',padx=4)
        tv=ttk.Treeview(c,columns=[x[0] for x in cols],show='headings');
        for k,l,ww in cols:tv.heading(k,text=l);tv.column(k,width=ww)
        tv.pack(fill='both',expand=True,padx=10,pady=(0,10));[tv.insert('','end',values=r) for r in rows];return tv
    def next_job(self):
        y=date.today().year;r=self.db.one("SELECT number FROM jobs WHERE number LIKE ? ORDER BY id DESC LIMIT 1",(f'LP-{y}-%',));n=1
        if r:
            try:n=int(r['number'].split('-')[-1])+1
            except:pass
        return f'LP-{y}-{n:05d}'
    def next_quote(self):
        y=date.today().year;r=self.db.one("SELECT number FROM quotes WHERE number LIKE ? ORDER BY id DESC LIMIT 1",(f'PREV-{y}-%',));n=1
        if r:
            try:n=int(r['number'].split('-')[-1])+1
            except:pass
        return f'PREV-{y}-{n:05d}'
    def pdf_path(self,n):return PDF_DIR/f"{n}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    def open_pdf(self,p):
        try:os.startfile(str(p))
        except:pass
        messagebox.showinfo('PDF creato',f'PDF salvato in:\n{p}')
    def print_rows(self,title,headers,rows,name):
        p=self.pdf_path(name);c=pdfcanvas.Canvas(str(p),pagesize=landscape(A4));w,h=landscape(A4)
        if LOGO_IMG.exists():
            try:c.drawImage(str(LOGO_IMG),15*mm,h-35*mm,width=58*mm,height=22*mm,preserveAspectRatio=True,mask='auto')
            except:pass
        c.setFont('Helvetica-Bold',16);c.setFillColor(colors.HexColor(RED));c.drawString(82*mm,h-22*mm,title);c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#555'));c.drawRightString(w-15*mm,h-20*mm,datetime.now().strftime('%d/%m/%Y %H:%M'));y=h-43*mm;n=len(headers);cw=(w-30*mm)/max(1,n)
        def head(y):
            c.setFillColor(colors.HexColor('#e9eef3'));c.rect(15*mm,y-6*mm,w-30*mm,7*mm,fill=1,stroke=0);c.setFillColor(colors.black);c.setFont('Helvetica-Bold',7)
            for i,x in enumerate(headers):c.drawString(16*mm+i*cw,y-4*mm,str(x)[:24])
            return y-9*mm
        y=head(y);c.setFont('Helvetica',7)
        for row in rows:
            if y<15*mm:c.showPage();y=h-18*mm;y=head(y)
            for i,v in enumerate(row):c.drawString(16*mm+i*cw,y,str(v if v is not None else '')[:28])
            c.setStrokeColor(colors.HexColor('#ddd'));c.line(15*mm,y-1.5*mm,w-15*mm,y-1.5*mm);y-=6*mm
        c.save();self.open_pdf(p)
    def print_entity(self,title,rows,name):
        p=self.pdf_path(name);c=pdfcanvas.Canvas(str(p),pagesize=A4);w,h=A4
        if LOGO_IMG.exists():
            try:c.drawImage(str(LOGO_IMG),18*mm,h-42*mm,width=62*mm,height=24*mm,preserveAspectRatio=True,mask='auto')
            except:pass
        c.setFillColor(colors.HexColor(RED));c.setFont('Helvetica-Bold',16);c.drawString(88*mm,h-23*mm,title);c.setFont('Helvetica',9);c.setFillColor(colors.HexColor('#555'));c.drawRightString(w-18*mm,h-36*mm,datetime.now().strftime('%d/%m/%Y %H:%M'));c.setStrokeColor(colors.HexColor(RED));c.line(18*mm,h-46*mm,w-18*mm,h-46*mm);y=h-58*mm
        for k,v in rows:c.setFont('Helvetica-Bold',9);c.setFillColor(colors.HexColor('#666'));c.drawString(18*mm,y,k);c.setFont('Helvetica',10);c.setFillColor(colors.black);c.drawString(60*mm,y,str(v or '')[:92]);y-=8*mm
        c.save();self.open_pdf(p)
    def dashboard(self):
        self.clear();self.set_bg();outer=tk.Frame(self.body,bg='#f7f9fb');outer.place(relx=.02,rely=.02,relwidth=.96,relheight=.96);can=tk.Canvas(outer,bg='#f7f9fb',highlightthickness=0);sb=ttk.Scrollbar(outer,orient='vertical',command=can.yview);can.configure(yscrollcommand=sb.set);sb.pack(side='right',fill='y');can.pack(fill='both',expand=True);content=tk.Frame(can,bg='#f7f9fb');win=can.create_window((0,0),window=content,anchor='nw');content.bind('<Configure>',lambda e:can.configure(scrollregion=can.bbox('all')));can.bind('<Configure>',lambda e:can.itemconfigure(win,width=e.width));can.bind_all('<MouseWheel>',lambda e:can.yview_scroll(int(-e.delta/120),'units'))
        top=tk.Frame(content,bg='#f7f9fb');top.pack(fill='x',padx=18,pady=(18,4));tk.Label(top,text='Dashboard',bg='#f7f9fb',fg=TEXT,font=('Segoe UI Semibold',28)).pack(side='left');tk.Label(top,text=datetime.now().strftime('%d/%m/%Y   %H:%M'),bg='#f7f9fb',fg=TEXT,font=('Segoe UI',10)).pack(side='right',pady=10);tk.Label(content,text='Benvenuto in Officina LA PRIMA',bg='#f7f9fb',fg=TEXT,font=('Segoe UI',11)).pack(anchor='w',padx=20)
        cards=tk.Frame(content,bg='#f7f9fb');cards.pack(fill='x',padx=18,pady=12);vals=[('Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c'],BLUE),('Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c'],BLUE),('Commesse Aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c'],ORANGE),('Auto pronte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN)]
        for i,(t,v,col) in enumerate(vals):f=self.card(cards);f.grid(row=0,column=i,sticky='nsew',padx=6);cards.grid_columnconfigure(i,weight=1);tk.Label(f,text=t,bg='white',fg=TEXT,font=('Segoe UI Semibold',11)).pack(anchor='w',padx=16,pady=(13,0));tk.Label(f,text=str(v),bg='white',fg=col,font=('Segoe UI Semibold',26)).pack(anchor='w',padx=16,pady=(0,12))
        cal=self.card(content);cal.pack(fill='x',padx=24,pady=(0,12));bar=tk.Frame(cal,bg='white');bar.pack(fill='x',padx=12,pady=9);self.btn(bar,'‹',self.prev_month).pack(side='left');self.btn(bar,'›',self.next_month).pack(side='left',padx=4);self.cal_title=tk.Label(bar,text='',bg='white',fg=TEXT,font=('Segoe UI Semibold',16));self.cal_title.pack(side='left',padx=10);self.btn(bar,'Oggi',self.today_month,True).pack(side='right');self.calendar_host=tk.Frame(cal,bg='white');self.calendar_host.pack(fill='x',padx=10,pady=(0,10));self.render_calendar()
        low=tk.Frame(content,bg='#f7f9fb');low.pack(fill='x',padx=24,pady=(0,24));low.grid_columnconfigure(0,weight=2);low.grid_columnconfigure(1,weight=1);lj=self.card(low);lj.grid(row=0,column=0,sticky='nsew',padx=(0,6));tk.Label(lj,text='Commesse in evidenza',bg='white',fg=TEXT,font=('Segoe UI Semibold',13)).pack(anchor='w',padx=12,pady=10);tv=ttk.Treeview(lj,columns=('n','client','car','status'),show='headings',height=7)
        for k,l in [('n','#'),('client','Cliente'),('car','Veicolo'),('status','Stato')]:tv.heading(k,text=l)
        tv.pack(fill='x',padx=10,pady=(0,10))
        for r in self.db.q('''SELECT j.number,j.status,c.name,v.brand,v.model FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY j.id DESC LIMIT 8'''):tv.insert('','end',values=(r['number'],r['name'],f"{r['brand'] or ''} {r['model'] or ''}",r['status']))
        rr=self.card(low);rr.grid(row=0,column=1,sticky='nsew',padx=(6,0));tk.Label(rr,text='Promemoria e scadenze',bg='white',fg=TEXT,font=('Segoe UI Semibold',13)).pack(anchor='w',padx=12,pady=10);ac=self.db.one("SELECT COUNT(*) c FROM appointments WHERE date>=?",(date.today().isoformat(),))['c'];tc=self.db.one('SELECT COUNT(*) c FROM services WHERE next_service_km>0')['c'];qc=self.db.one("SELECT COUNT(*) c FROM quotes WHERE status!='Accettato'")['c'];tk.Label(rr,text=f'🔧  {tc} tagliandi programmati',bg='white',fg=TEXT).pack(anchor='w',padx=14,pady=7);tk.Label(rr,text=f'📄  {qc} preventivi da seguire',bg='white',fg=TEXT).pack(anchor='w',padx=14,pady=7);tk.Label(rr,text=f'📅  {ac} appuntamenti futuri',bg='white',fg=TEXT).pack(anchor='w',padx=14,pady=7)
    def render_calendar(self):
        for w in self.calendar_host.winfo_children():w.destroy()
        self.cal_title.config(text=f'{MONTHS[self.cal_month-1]} {self.cal_year}')
        for i,d in enumerate(['Lun','Mar','Mer','Gio','Ven','Sab','Dom']):tk.Label(self.calendar_host,text=d,bg='#edf1f5',fg=TEXT,font=('Segoe UI Semibold',9)).grid(row=0,column=i,sticky='nsew',padx=1,pady=1);self.calendar_host.grid_columnconfigure(i,weight=1,uniform='cal')
        weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(self.cal_year,self.cal_month);last=calendar.monthrange(self.cal_year,self.cal_month)[1];aa=self.db.q('''SELECT a.*,v.plate FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id WHERE a.date BETWEEN ? AND ? ORDER BY a.date,a.time''',(f'{self.cal_year:04d}-{self.cal_month:02d}-01',f'{self.cal_year:04d}-{self.cal_month:02d}-{last:02d}'));am={}
        for x in aa:am.setdefault(x['date'],[]).append(x)
        for rr,wk in enumerate(weeks,1):
            for cc,day in enumerate(wk):
                cell=tk.Frame(self.calendar_host,bg='white',height=86,highlightbackground='#dfe5eb',highlightthickness=1);cell.grid(row=rr,column=cc,sticky='nsew',padx=1,pady=1);cell.grid_propagate(False)
                if not day:continue
                ds=f'{self.cal_year:04d}-{self.cal_month:02d}-{day:02d}';today=date.today().isoformat()==ds;n=tk.Label(cell,text=str(day),bg=BLUE if today else 'white',fg='white' if today else TEXT,font=('Segoe UI Semibold',9),cursor='hand2');n.pack(anchor='nw',padx=5,pady=3);n.bind('<Button-1>',lambda e,d=ds:self.app_dialog(d))
                for x in am.get(ds,[])[:3]:tk.Label(cell,text=(f"{x['time'] or ''} {x['plate'] or ''} {x['reason'] or ''}")[:26],bg='#dbeafe',fg='#0756a1',anchor='w',font=('Segoe UI',8),padx=4).pack(fill='x',padx=3,pady=1)
    def prev_month(self):
        self.cal_month-=1
        if self.cal_month<1:self.cal_month=12;self.cal_year-=1
        self.render_calendar()
    def next_month(self):
        self.cal_month+=1
        if self.cal_month>12:self.cal_month=1;self.cal_year+=1
        self.render_calendar()
    def today_month(self):self.cal_year=date.today().year;self.cal_month=date.today().month;self.render_calendar()

    # Clienti
    def clients(self):
        rows=[(r['id'],r['name'],r['phone'] or '',r['email'] or '',r['notes'] or '') for r in self.db.q('SELECT * FROM clients ORDER BY name')];self.ct=self._page('Clienti','Anagrafica clienti',[('id','ID',50),('name','Cliente',250),('phone','Telefono',140),('email','Email',220),('notes','Note',320)],rows,lambda:self.client_dialog(),self.edit_client,self.del_client,self.print_clients,self.print_client);self.ct.bind('<Double-1>',lambda e:self.edit_client())
    def client_dialog(self,cid=None):
        w=tk.Toplevel(self);w.title('Cliente');w.geometry('650x360');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];n=self.field(f,'Nome / Ragione sociale',0,0);ph=self.field(f,'Telefono',0,1);em=self.field(f,'Email',2,0);no=self.field(f,'Note',2,1)
        if cid:
            r=self.db.one('SELECT * FROM clients WHERE id=?',(cid,));[x.insert(0,str(v or '')) for x,v in zip([n,ph,em,no],[r['name'],r['phone'],r['email'],r['notes']])]
        def save():
            if not n.get().strip():return
            vals=(n.get().strip(),ph.get().strip(),em.get().strip(),no.get().strip());self.db.ex('UPDATE clients SET name=?,phone=?,email=?,notes=? WHERE id=?',vals+(cid,)) if cid else self.db.ex('INSERT INTO clients(name,phone,email,notes) VALUES(?,?,?,?)',vals);w.destroy();self.clients()
        self.btn(f,'Salva',save,True).grid(row=4,column=1,sticky='e',padx=8,pady=12)
    def edit_client(self):x=self.selected(self.ct);self.client_dialog(x) if x else None
    def del_client(self):
        x=self.selected(self.ct)
        if x and messagebox.askyesno('Conferma','Eliminare cliente e dati collegati?'):self.db.ex('DELETE FROM clients WHERE id=?',(x,));self.clients()
    def print_clients(self):self.print_rows('SITUAZIONE CLIENTI',['ID','Cliente','Telefono','Email','Note'],[[r['id'],r['name'],r['phone'],r['email'],r['notes']] for r in self.db.q('SELECT * FROM clients ORDER BY name')],'Clienti')
    def print_client(self):
        x=self.selected(self.ct)
        if x:
            r=self.db.one('SELECT * FROM clients WHERE id=?',(x,));self.print_entity('SCHEDA CLIENTE',[('Cliente',r['name']),('Telefono',r['phone']),('Email',r['email']),('Note',r['notes'])],'Cliente')

    # Veicoli
    def vehicles(self):
        q='''SELECT v.*,c.name client FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate''';rows=[(r['id'],r['plate'],f"{r['brand'] or ''} {r['model'] or ''}".strip(),r['year'] or '',r['client'],r['km'] or 0,r['vin'] or '') for r in self.db.q(q)];self.vt=self._page('Veicoli','Archivio mezzi per targa',[('id','ID',50),('plate','Targa',95),('car','Veicolo',220),('year','Anno',70),('client','Cliente',220),('km','Km',85),('vin','VIN',220)],rows,lambda:self.vehicle_dialog(),self.edit_vehicle,self.del_vehicle,self.print_vehicles,self.print_vehicle);self.vt.bind('<Double-1>',lambda e:self.edit_vehicle())
    def vehicle_dialog(self,vid=None):
        cs=self.db.q('SELECT id,name FROM clients ORDER BY name')
        if not cs:return messagebox.showinfo('Attenzione','Crea prima un cliente.')
        w=tk.Toplevel(self);w.title('Cliente e auto');w.geometry('720x490');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];cm={f"{r['name']} [ID {r['id']}]":r['id'] for r in cs};tk.Label(f,text='Cliente proprietario',bg='white',fg=MUTED).grid(row=0,column=0,sticky='w',padx=8);cb=ttk.Combobox(f,state='readonly',values=list(cm));cb.grid(row=1,column=0,columnspan=2,sticky='ew',padx=8);pl=self.field(f,'Targa',2,0);br=self.field(f,'Marca',2,1);mo=self.field(f,'Modello',4,0);yr=self.field(f,'Anno vettura',4,1);km=self.field(f,'Km',6,0);vin=self.field(f,'VIN / Telaio',6,1)
        if vid:
            r=self.db.one('SELECT * FROM vehicles WHERE id=?',(vid,));[cb.set(k) for k,v in cm.items() if v==r['client_id']];[x.insert(0,str(v or '')) for x,v in zip([pl,br,mo,yr,km,vin],[r['plate'],r['brand'],r['model'],r['year'],r['km'],r['vin']])]
        else:cb.current(0)
        def save():
            if cb.get() not in cm or not pl.get().strip():return
            try:kmi=int(km.get() or 0)
            except:kmi=0
            vals=(cm[cb.get()],pl.get().strip().upper(),br.get().strip(),mo.get().strip(),yr.get().strip(),kmi,vin.get().strip())
            try:self.db.ex('UPDATE vehicles SET client_id=?,plate=?,brand=?,model=?,year=?,km=?,vin=? WHERE id=?',vals+(vid,)) if vid else self.db.ex('INSERT INTO vehicles(client_id,plate,brand,model,year,km,vin) VALUES(?,?,?,?,?,?,?)',vals)
            except Exception as e:return messagebox.showerror('Errore',str(e))
            w.destroy();self.vehicles()
        self.btn(f,'Salva',save,True).grid(row=8,column=1,sticky='e',padx=8,pady=12)
    def edit_vehicle(self):x=self.selected(self.vt);self.vehicle_dialog(x) if x else None
    def del_vehicle(self):
        x=self.selected(self.vt)
        if x and messagebox.askyesno('Conferma','Eliminare veicolo?'):self.db.ex('DELETE FROM vehicles WHERE id=?',(x,));self.vehicles()
    def print_vehicles(self):
        q='''SELECT v.*,c.name client FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate''';self.print_rows('SITUAZIONE VEICOLI',['ID','Targa','Veicolo','Anno','Cliente','Km','VIN'],[[r['id'],r['plate'],f"{r['brand'] or ''} {r['model'] or ''}",r['year'],r['client'],r['km'],r['vin']] for r in self.db.q(q)],'Veicoli')
    def print_vehicle(self):
        x=self.selected(self.vt)
        if x:
            r=self.db.one('''SELECT v.*,c.name client,c.phone,c.email FROM vehicles v JOIN clients c ON c.id=v.client_id WHERE v.id=?''',(x,));self.print_entity('SCHEDA VEICOLO',[('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Veicolo',f"{r['brand'] or ''} {r['model'] or ''}"),('Anno',r['year']),('Km',r['km']),('VIN',r['vin'])],'Veicolo')

    # Commesse
    def jobs(self):
        q='''SELECT j.*,v.plate,c.name client FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY j.id DESC''';rows=[(r['id'],r['number'],r['opened'],r['plate'],r['client'],r['status'],f"{r['labor']+r['parts']:.2f}") for r in self.db.q(q)];self.jt=self._page('Commesse','Accettazione, diagnosi e lavorazioni',[('id','ID',45),('num','Commessa',140),('date','Data',95),('plate','Targa',90),('client','Cliente',200),('status','Stato',140),('total','Totale €',95)],rows,lambda:self.job_dialog(),self.edit_job,self.del_job,self.print_jobs,self.print_job);self.jt.bind('<Double-1>',lambda e:self.edit_job())
    def job_dialog(self,jid=None):
        vs=self.db.q('''SELECT v.id,v.plate,v.brand,v.model,c.name FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate''')
        if not vs:return messagebox.showinfo('Attenzione','Crea prima un veicolo.')
        w=tk.Toplevel(self);w.title('Commessa');w.geometry('800x560');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];vm={f"{r['plate']} - {r['brand'] or ''} {r['model'] or ''} - {r['name']}":r['id'] for r in vs};tk.Label(f,text='Veicolo',bg='white',fg=MUTED).grid(row=0,column=0,sticky='w',padx=8);cb=ttk.Combobox(f,state='readonly',values=list(vm));cb.grid(row=1,column=0,columnspan=2,sticky='ew',padx=8);num=self.field(f,'Numero commessa',2,0);op=self.field(f,'Data apertura',2,1);issue=self.field(f,'Problema segnalato',4,0);diag=self.field(f,'Diagnosi / lavoro',4,1);tk.Label(f,text='Stato',bg='white',fg=MUTED).grid(row=6,column=0,sticky='w',padx=8);st=ttk.Combobox(f,state='readonly',values=STATUSES);st.grid(row=7,column=0,sticky='ew',padx=8);lab=self.field(f,'Manodopera €',6,1);parts=self.field(f,'Ricambi €',8,0);notes=self.field(f,'Note',8,1)
        if jid:
            r=self.db.one('SELECT * FROM jobs WHERE id=?',(jid,));[cb.set(k) for k,v in vm.items() if v==r['vehicle_id']];[x.insert(0,str(v or '')) for x,v in zip([num,op,issue,diag,lab,parts,notes],[r['number'],r['opened'],r['issue'],r['diagnosis'],r['labor'],r['parts'],r['notes']])];st.set(r['status'])
        else:cb.current(0);num.insert(0,self.next_job());op.insert(0,date.today().isoformat());st.set('Accettata');lab.insert(0,'0');parts.insert(0,'0')
        def ff(x):
            try:return float(x.get().replace(',','.') or 0)
            except:return 0
        def save():
            vals=(num.get().strip(),vm.get(cb.get()),op.get().strip(),issue.get().strip(),diag.get().strip(),st.get(),ff(lab),ff(parts),notes.get().strip());self.db.ex('UPDATE jobs SET number=?,vehicle_id=?,opened=?,issue=?,diagnosis=?,status=?,labor=?,parts=?,notes=? WHERE id=?',vals+(jid,)) if jid else self.db.ex('INSERT INTO jobs(number,vehicle_id,opened,issue,diagnosis,status,labor,parts,notes) VALUES(?,?,?,?,?,?,?,?,?)',vals);w.destroy();self.jobs()
        self.btn(f,'Salva commessa',save,True).grid(row=10,column=1,sticky='e',padx=8,pady=12)
    def edit_job(self):x=self.selected(self.jt);self.job_dialog(x) if x else None
    def del_job(self):
        x=self.selected(self.jt)
        if x and messagebox.askyesno('Conferma','Eliminare commessa?'):self.db.ex('DELETE FROM jobs WHERE id=?',(x,));self.jobs()
    def print_jobs(self):
        q='''SELECT j.*,v.plate,c.name client FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY j.id DESC''';self.print_rows('SITUAZIONE COMMESSE',['Commessa','Data','Targa','Cliente','Stato','Manod.','Ricambi','Totale'],[[r['number'],r['opened'],r['plate'],r['client'],r['status'],r['labor'],r['parts'],r['labor']+r['parts']] for r in self.db.q(q)],'Commesse')
    def print_job(self):
        x=self.selected(self.jt)
        if x:
            r=self.db.one('''SELECT j.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id WHERE j.id=?''',(x,));self.print_entity('RICEVUTA / PROMEMORIA LAVORAZIONE',[('Commessa',r['number']),('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Veicolo',f"{r['brand'] or ''} {r['model'] or ''} - {r['year'] or ''}"),('Data',r['opened']),('Stato',r['status']),('Problema',r['issue']),('Diagnosi / lavoro',r['diagnosis']),('Manodopera',f"€ {r['labor']:.2f}"),('Ricambi',f"€ {r['parts']:.2f}"),('Totale',f"€ {r['labor']+r['parts']:.2f}"),('Note',r['notes'])],'Commessa')

    # Appuntamenti
    def appointments(self):
        q='''SELECT a.*,v.plate,c.name client FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id ORDER BY a.date,a.time''';rows=[(r['id'],r['date'],r['time'] or '',r['plate'] or '-',r['client'] or '',r['reason'] or '') for r in self.db.q(q)];self.at=self._page('Appuntamenti','Agenda officina',[('id','ID',45),('date','Data',100),('time','Ora',70),('plate','Targa',90),('client','Cliente',200),('reason','Motivo',350)],rows,lambda:self.app_dialog(),self.edit_app,self.del_app,self.print_apps,self.print_app);self.at.bind('<Double-1>',lambda e:self.edit_app())
    def app_dialog(self,preset_date=None,aid=None):
        vs=self.db.q('SELECT id,plate,brand,model FROM vehicles ORDER BY plate');w=tk.Toplevel(self);w.title('Appuntamento');w.geometry('650x390');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];vm={'Nessun veicolo':None}|{f"{r['plate']} - {r['brand'] or ''} {r['model'] or ''}":r['id'] for r in vs};tk.Label(f,text='Veicolo',bg='white',fg=MUTED).grid(row=0,column=0,sticky='w',padx=8);cb=ttk.Combobox(f,state='readonly',values=list(vm));cb.grid(row=1,column=0,columnspan=2,sticky='ew',padx=8);cb.set('Nessun veicolo');d=self.field(f,'Data',2,0);t=self.field(f,'Ora',2,1);re=self.field(f,'Motivo',4,0)
        if aid:
            r=self.db.one('SELECT * FROM appointments WHERE id=?',(aid,));d.insert(0,r['date']);t.insert(0,r['time'] or '');re.insert(0,r['reason'] or '');[cb.set(k) for k,v in vm.items() if v==r['vehicle_id']]
        else:d.insert(0,preset_date or date.today().isoformat())
        def save():
            vals=(vm.get(cb.get()),d.get().strip(),t.get().strip(),re.get().strip());self.db.ex('UPDATE appointments SET vehicle_id=?,date=?,time=?,reason=? WHERE id=?',vals+(aid,)) if aid else self.db.ex('INSERT INTO appointments(vehicle_id,date,time,reason) VALUES(?,?,?,?)',vals);w.destroy();self.dashboard() if preset_date else self.appointments()
        self.btn(f,'Salva',save,True).grid(row=6,column=1,sticky='e',padx=8,pady=12)
    def edit_app(self):x=self.selected(self.at);self.app_dialog(aid=x) if x else None
    def del_app(self):
        x=self.selected(self.at)
        if x:self.db.ex('DELETE FROM appointments WHERE id=?',(x,));self.appointments()
    def print_apps(self):
        q='''SELECT a.*,v.plate,c.name client FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id ORDER BY a.date,a.time''';self.print_rows('SITUAZIONE APPUNTAMENTI',['Data','Ora','Targa','Cliente','Motivo'],[[r['date'],r['time'],r['plate'],r['client'],r['reason']] for r in self.db.q(q)],'Appuntamenti')
    def print_app(self):
        x=self.selected(self.at)
        if x:
            r=self.db.one('''SELECT a.*,v.plate,v.brand,v.model,c.name client,c.phone,c.email FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id WHERE a.id=?''',(x,));self.print_entity('PROMEMORIA APPUNTAMENTO',[('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Veicolo',f"{r['brand'] or ''} {r['model'] or ''}"),('Data',r['date']),('Ora',r['time']),('Motivo',r['reason'])],'Appuntamento')

    # Tagliandi
    def services(self):
        q='''SELECT s.*,v.plate,c.name client FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY s.service_date DESC''';rows=[]
        for r in self.db.q(q):
            fs=[]
            if r['oil_filter']:fs.append('Olio')
            if r['air_filter']:fs.append('Aria')
            if r['fuel_filter']:fs.append('Carburante')
            if r['cabin_filter']:fs.append('Abitacolo')
            if r['other_filters']:fs.append(r['other_filters'])
            rows.append((r['id'],r['service_date'],r['plate'],r['client'],r['km'],r['engine_oil'] or '',', '.join(fs),r['next_service_km'] or '',r['notes'] or ''))
        self.st=self._page('Tagliandi','Storico olio, filtri e chilometraggio',[('id','ID',45),('date','Data',95),('plate','Targa',90),('client','Cliente',180),('km','Km',80),('oil','Olio',120),('filters','Filtri',240),('next','Prossimo km',100),('notes','Note',190)],rows,lambda:self.service_dialog(),self.edit_service,self.del_service,self.print_services,self.print_service);self.st.bind('<Double-1>',lambda e:self.edit_service())
    def service_dialog(self,sid=None):
        vs=self.db.q('''SELECT v.id,v.plate,v.brand,v.model,c.name FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate''')
        if not vs:return messagebox.showinfo('Attenzione','Crea prima un veicolo.')
        w=tk.Toplevel(self);w.title('Tagliando');w.geometry('820x620');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];vm={f"{r['plate']} - {r['brand'] or ''} {r['model'] or ''} - {r['name']}":r['id'] for r in vs};tk.Label(f,text='Veicolo',bg='white',fg=MUTED).grid(row=0,column=0,sticky='w',padx=8);cb=ttk.Combobox(f,state='readonly',values=list(vm));cb.grid(row=1,column=0,columnspan=2,sticky='ew',padx=8);dt=self.field(f,'Data tagliando',2,0);km=self.field(f,'Km attuali',2,1);oil=self.field(f,'Olio motore / gradazione',4,0);nxt=self.field(f,'Prossimo tagliando a km',4,1);box=tk.LabelFrame(f,text='Filtri sostituiti',bg='white',fg=TEXT);box.grid(row=6,column=0,columnspan=2,sticky='ew',padx=8,pady=10);vo=tk.IntVar();va=tk.IntVar();vf=tk.IntVar();vc=tk.IntVar()
        for tx,v in [('Filtro olio',vo),('Filtro aria',va),('Filtro carburante',vf),('Filtro abitacolo',vc)]:tk.Checkbutton(box,text=tx,variable=v,bg='white').pack(side='left',padx=10,pady=8)
        other=self.field(f,'Altri filtri / materiali',8,0);notes=self.field(f,'Note',8,1)
        if sid:
            r=self.db.one('SELECT * FROM services WHERE id=?',(sid,));[cb.set(k) for k,v in vm.items() if v==r['vehicle_id']];[x.insert(0,str(v or '')) for x,v in zip([dt,km,oil,nxt,other,notes],[r['service_date'],r['km'],r['engine_oil'],r['next_service_km'],r['other_filters'],r['notes']])];vo.set(r['oil_filter']);va.set(r['air_filter']);vf.set(r['fuel_filter']);vc.set(r['cabin_filter'])
        else:cb.current(0);dt.insert(0,date.today().isoformat())
        def save():
            try:kmi=int(km.get() or 0)
            except:kmi=0
            try:nxi=int(nxt.get() or 0)
            except:nxi=0
            vals=(vm.get(cb.get()),dt.get().strip(),kmi,oil.get().strip(),vo.get(),va.get(),vf.get(),vc.get(),other.get().strip(),nxi,notes.get().strip());self.db.ex('UPDATE services SET vehicle_id=?,service_date=?,km=?,engine_oil=?,oil_filter=?,air_filter=?,fuel_filter=?,cabin_filter=?,other_filters=?,next_service_km=?,notes=? WHERE id=?',vals+(sid,)) if sid else self.db.ex('INSERT INTO services(vehicle_id,service_date,km,engine_oil,oil_filter,air_filter,fuel_filter,cabin_filter,other_filters,next_service_km,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)',vals);self.db.ex('UPDATE vehicles SET km=CASE WHEN km<? THEN ? ELSE km END WHERE id=?',(kmi,kmi,vm.get(cb.get())));w.destroy();self.services()
        self.btn(f,'Salva tagliando',save,True).grid(row=10,column=1,sticky='e',padx=8,pady=12)
    def edit_service(self):x=self.selected(self.st);self.service_dialog(x) if x else None
    def del_service(self):
        x=self.selected(self.st)
        if x:self.db.ex('DELETE FROM services WHERE id=?',(x,));self.services()
    def print_services(self):
        q='''SELECT s.*,v.plate,c.name client FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY s.service_date DESC''';self.print_rows('SITUAZIONE TAGLIANDI',['Data','Targa','Cliente','Km','Olio','F.olio','Aria','Carb.','Abit.','Pross.km'],[[r['service_date'],r['plate'],r['client'],r['km'],r['engine_oil'],r['oil_filter'],r['air_filter'],r['fuel_filter'],r['cabin_filter'],r['next_service_km']] for r in self.db.q(q)],'Tagliandi')
    def print_service(self):
        x=self.selected(self.st)
        if x:
            r=self.db.one('''SELECT s.*,v.plate,v.brand,v.model,c.name client,c.phone,c.email FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id WHERE s.id=?''',(x,));fs=[n for n,b in [('Filtro olio',r['oil_filter']),('Filtro aria',r['air_filter']),('Filtro carburante',r['fuel_filter']),('Filtro abitacolo',r['cabin_filter'])] if b];fs+=([r['other_filters']] if r['other_filters'] else []);self.print_entity('PROMEMORIA TAGLIANDO',[('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Veicolo',f"{r['brand'] or ''} {r['model'] or ''}"),('Data',r['service_date']),('Km',r['km']),('Olio motore',r['engine_oil']),('Filtri sostituiti',', '.join(fs)),('Prossimo tagliando km',r['next_service_km']),('Note',r['notes'])],'Tagliando')

    # Preventivi, Magazzino, Fornitori
    def quotes(self):
        q='''SELECT q.*,v.plate,c.name client FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY q.id DESC''';rows=[(r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],f"{r['total']:.2f}",r['notes'] or '') for r in self.db.q(q)];self.qt=self._page('Preventivi','Preventivi clienti',[('id','ID',45),('num','Numero',130),('date','Data',95),('plate','Targa',90),('client','Cliente',190),('status','Stato',110),('total','Totale €',90),('notes','Note',250)],rows,lambda:self.quote_dialog(),self.edit_quote,self.del_quote,self.print_quotes)
    def quote_dialog(self,qid=None):
        vs=self.db.q('''SELECT v.id,v.plate,c.name FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate''')
        if not vs:return messagebox.showinfo('Attenzione','Crea prima un veicolo.')
        w=tk.Toplevel(self);w.title('Preventivo');w.geometry('700x450');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];vm={f"{r['plate']} - {r['name']}":r['id'] for r in vs};tk.Label(f,text='Veicolo',bg='white',fg=MUTED).grid(row=0,column=0,sticky='w',padx=8);cb=ttk.Combobox(f,state='readonly',values=list(vm));cb.grid(row=1,column=0,columnspan=2,sticky='ew',padx=8);num=self.field(f,'Numero',2,0);cr=self.field(f,'Data',2,1);tk.Label(f,text='Stato',bg='white',fg=MUTED).grid(row=4,column=0,sticky='w',padx=8);st=ttk.Combobox(f,state='readonly',values=['Bozza','Inviato','Accettato','Rifiutato']);st.grid(row=5,column=0,sticky='ew',padx=8);total=self.field(f,'Totale €',4,1);notes=self.field(f,'Note',6,0)
        if qid:
            r=self.db.one('SELECT * FROM quotes WHERE id=?',(qid,));[cb.set(k) for k,v in vm.items() if v==r['vehicle_id']];[x.insert(0,str(v or '')) for x,v in zip([num,cr,total,notes],[r['number'],r['created'],r['total'],r['notes']])];st.set(r['status'])
        else:cb.current(0);num.insert(0,self.next_quote());cr.insert(0,date.today().isoformat());st.set('Bozza');total.insert(0,'0')
        def save():
            try:tot=float(total.get().replace(',','.') or 0)
            except:tot=0
            vals=(num.get(),vm.get(cb.get()),cr.get(),st.get(),tot,notes.get());self.db.ex('UPDATE quotes SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=? WHERE id=?',vals+(qid,)) if qid else self.db.ex('INSERT INTO quotes(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)',vals);w.destroy();self.quotes()
        self.btn(f,'Salva',save,True).grid(row=8,column=1,sticky='e',padx=8,pady=12)
    def edit_quote(self):x=self.selected(self.qt);self.quote_dialog(x) if x else None
    def del_quote(self):
        x=self.selected(self.qt)
        if x:self.db.ex('DELETE FROM quotes WHERE id=?',(x,));self.quotes()
    def print_quotes(self):
        q='''SELECT q.*,v.plate,c.name client FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY q.id DESC''';self.print_rows('SITUAZIONE PREVENTIVI',['Numero','Data','Targa','Cliente','Stato','Totale','Note'],[[r['number'],r['created'],r['plate'],r['client'],r['status'],r['total'],r['notes']] for r in self.db.q(q)],'Preventivi')
    def inventory(self):
        rows=[(r['id'],r['code'] or '',r['description'],r['supplier'] or '',r['qty'],r['min_qty'],r['cost'],r['sale']) for r in self.db.q('SELECT * FROM inventory ORDER BY description')];self.it=self._page('Magazzino','Ricambi e giacenze',[('id','ID',45),('code','Codice',90),('desc','Descrizione',240),('sup','Fornitore',180),('qty','Q.tà',70),('min','Min',60),('cost','Costo',80),('sale','Vendita',80)],rows,lambda:self.part_dialog(),self.edit_part,self.del_part,self.print_inventory)
    def part_dialog(self,pid=None):
        w=tk.Toplevel(self);w.title('Ricambio');w.geometry('680x430');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];code=self.field(f,'Codice',0,0);desc=self.field(f,'Descrizione',0,1);sup=self.field(f,'Fornitore',2,0);qty=self.field(f,'Quantità',2,1);mi=self.field(f,'Scorta minima',4,0);cost=self.field(f,'Costo',4,1);sale=self.field(f,'Prezzo vendita',6,0)
        if pid:
            r=self.db.one('SELECT * FROM inventory WHERE id=?',(pid,));[x.insert(0,str(v or '')) for x,v in zip([code,desc,sup,qty,mi,cost,sale],[r['code'],r['description'],r['supplier'],r['qty'],r['min_qty'],r['cost'],r['sale']])]
        def ff(x):
            try:return float(x.get().replace(',','.') or 0)
            except:return 0
        def save():
            vals=(code.get(),desc.get(),sup.get(),ff(qty),ff(mi),ff(cost),ff(sale));self.db.ex('UPDATE inventory SET code=?,description=?,supplier=?,qty=?,min_qty=?,cost=?,sale=? WHERE id=?',vals+(pid,)) if pid else self.db.ex('INSERT INTO inventory(code,description,supplier,qty,min_qty,cost,sale) VALUES(?,?,?,?,?,?,?)',vals);w.destroy();self.inventory()
        self.btn(f,'Salva',save,True).grid(row=8,column=1,sticky='e',padx=8,pady=12)
    def edit_part(self):x=self.selected(self.it);self.part_dialog(x) if x else None
    def del_part(self):
        x=self.selected(self.it)
        if x:self.db.ex('DELETE FROM inventory WHERE id=?',(x,));self.inventory()
    def print_inventory(self):self.print_rows('SITUAZIONE MAGAZZINO',['Codice','Descrizione','Fornitore','Q.tà','Min','Costo','Vendita'],[[r['code'],r['description'],r['supplier'],r['qty'],r['min_qty'],r['cost'],r['sale']] for r in self.db.q('SELECT * FROM inventory ORDER BY description')],'Magazzino')
    def suppliers(self):
        rows=[(r['id'],r['name'],r['phone'] or '',r['email'] or '',r['notes'] or '') for r in self.db.q('SELECT * FROM suppliers ORDER BY name')];self.spt=self._page('Fornitori','Anagrafica fornitori',[('id','ID',45),('name','Fornitore',250),('phone','Telefono',140),('email','Email',220),('notes','Note',320)],rows,lambda:self.supplier_dialog(),self.edit_supplier,self.del_supplier,self.print_suppliers)
    def supplier_dialog(self,sid=None):
        w=tk.Toplevel(self);w.title('Fornitore');w.geometry('650x360');w.grab_set();f=self.card(w);f.pack(fill='both',expand=True,padx=14,pady=14);[f.grid_columnconfigure(i,weight=1) for i in range(2)];n=self.field(f,'Nome',0,0);p=self.field(f,'Telefono',0,1);e=self.field(f,'Email',2,0);no=self.field(f,'Note',2,1)
        if sid:
            r=self.db.one('SELECT * FROM suppliers WHERE id=?',(sid,));[x.insert(0,str(v or '')) for x,v in zip([n,p,e,no],[r['name'],r['phone'],r['email'],r['notes']])]
        def save():
            vals=(n.get(),p.get(),e.get(),no.get());self.db.ex('UPDATE suppliers SET name=?,phone=?,email=?,notes=? WHERE id=?',vals+(sid,)) if sid else self.db.ex('INSERT INTO suppliers(name,phone,email,notes) VALUES(?,?,?,?)',vals);w.destroy();self.suppliers()
        self.btn(f,'Salva',save,True).grid(row=4,column=1,sticky='e',padx=8,pady=12)
    def edit_supplier(self):x=self.selected(self.spt);self.supplier_dialog(x) if x else None
    def del_supplier(self):
        x=self.selected(self.spt)
        if x:self.db.ex('DELETE FROM suppliers WHERE id=?',(x,));self.suppliers()
    def print_suppliers(self):self.print_rows('SITUAZIONE FORNITORI',['ID','Fornitore','Telefono','Email','Note'],[[r['id'],r['name'],r['phone'],r['email'],r['notes']] for r in self.db.q('SELECT * FROM suppliers ORDER BY name')],'Fornitori')
    def deadlines(self):
        w=self.wrap('Scadenze','Promemoria manutenzione e agenda');c=self.card(w);c.pack(fill='both',expand=True,padx=24,pady=(0,20));rows=[]
        for r in self.db.q('''SELECT s.next_service_km,v.plate,c.name FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id WHERE s.next_service_km>0 ORDER BY s.next_service_km'''):rows.append((r['plate'],r['name'],f"Tagliando previsto a {r['next_service_km']} km"))
        for r in self.db.q('''SELECT a.date,a.time,v.plate,c.name,a.reason FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id WHERE a.date>=? ORDER BY a.date,a.time''',(date.today().isoformat(),)):rows.append((r['plate'] or '',r['name'] or '',f"{r['date']} {r['time'] or ''} - {r['reason'] or ''}"))
        tv=ttk.Treeview(c,columns=('plate','client','item'),show='headings');tv.heading('plate',text='Targa');tv.heading('client',text='Cliente');tv.heading('item',text='Scadenza / Promemoria');tv.pack(fill='both',expand=True,padx=10,pady=10);[tv.insert('','end',values=r) for r in rows];self.btn(c,'Stampa reparto PDF',lambda:self.print_rows('SCADENZE E PROMEMORIA',['Targa','Cliente','Scadenza'],rows,'Scadenze')).pack(anchor='e',padx=10,pady=(0,10))
    def report(self):
        w=self.wrap('Report','Situazione generale aggiornata');c=self.card(w);c.pack(fill='x',padx=24,pady=(0,20));vals=[('Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c']),('Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c']),('Commesse aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c']),('Auto pronte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c']),('Valore commesse',self.db.one('SELECT COALESCE(SUM(labor+parts),0) s FROM jobs')['s'])]
        for k,v in vals:tk.Label(c,text=f'{k}: {v}',bg='white',fg=TEXT,font=('Segoe UI Semibold',12)).pack(anchor='w',padx=18,pady=8)
        self.btn(c,'Stampa Report PDF',lambda:self.print_rows('REPORT GENERALE',['Voce','Valore'],vals,'Report')).pack(anchor='e',padx=18,pady=16)
    def backup(self):
        w=self.wrap('Backup','Protezione dei dati locali');c=self.card(w);c.pack(fill='x',padx=24,pady=(0,20));tk.Label(c,text=f'Database: {DB_PATH}',bg='white',fg=MUTED,font=('Segoe UI',10)).pack(anchor='w',padx=16,pady=(16,8));tk.Label(c,text=f'PDF: {PDF_DIR}',bg='white',fg=MUTED,font=('Segoe UI',10)).pack(anchor='w',padx=16,pady=8);self.btn(c,'Crea backup adesso',self.create_backup,True).pack(anchor='w',padx=16,pady=16)
    def create_backup(self):
        self.db.c.commit();d=BACKUP_DIR/f"la_prima_backup_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.db";shutil.copy2(DB_PATH,d);messagebox.showinfo('Backup creato',str(d));return d
    def on_close(self):
        ans=messagebox.askyesnocancel('Chiusura programma','Vuoi creare un backup dei dati prima di chiudere?')
        if ans is None:return
        if ans:
            try:self.create_backup()
            except Exception as e:
                if not messagebox.askyesno('Errore backup',f'{e}\n\nChiudere comunque?'):return
        try:self.db.c.close()
        except:pass
        self.destroy()

if __name__=='__main__':App().mainloop()
