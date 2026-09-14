import tkinter as tk
from tkinter import ttk
from datetime import date, datetime
import calendar
from PIL import Image, ImageTk, ImageDraw

from app import App as BaseApp, BG, NAVY, RED, TEXT, MUTED, BLUE, GREEN, ORANGE, RES_DIR

# La grafica V3 usa il logo reale dell'officina come sfondo/watermark.
# Nessuna immagine generata: usiamo esclusivamente l'asset ufficiale già incluso.
LOGO_IMG = RES_DIR/'assets'/'la_prima_logo.png'
BG_IMG = LOGO_IMG

class App(BaseApp):
    def _load_assets(self):
        self.bg_src=None; self.logo_tk=None
        try:self.bg_src=Image.open(BG_IMG).convert('RGB')
        except:pass
        try:
            im=Image.open(LOGO_IMG).convert('RGBA')
            im.thumbnail((255,120),Image.LANCZOS); self.logo_tk=ImageTk.PhotoImage(im)
        except:pass

    def _shell(self):
        self.sidebar=tk.Frame(self,bg='#152536',width=292); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        brand=tk.Frame(self.sidebar,bg='#152536',height=180); brand.pack(fill='x'); brand.pack_propagate(False)
        if self.logo_tk:
            tk.Label(brand,image=self.logo_tk,bg='#152536').pack(pady=(18,4))
        else:
            tk.Label(brand,text='OFFICINA\n“LA PRIMA”',bg='#152536',fg='white',font=('Segoe UI Black',24)).pack(pady=28)
        self.nav_buttons={}
        items=[('⌂','Dashboard',self.dashboard),('👥','Clienti',self.clients),('🚗','Veicoli',self.vehicles),('🔧','Commesse',self.jobs),('▣','Appuntamenti',self.appointments),('⚙','Tagliandi',self.services),('▤','Preventivi',self.quotes),('▤','Fatture',self._fatture),('▦','Magazzino',self.inventory),('▣','Fornitori',self.suppliers),('◷','Scadenze',self.deadlines),('▥','Report',self.report),('◉','Backup',self.backup),('⚙','Impostazioni',self._impostazioni)]
        for icon,t,cmd in items:
            b=tk.Button(self.sidebar,text=f'{icon}   {t}',command=lambda n=t,c=cmd:self._go(n,c),anchor='w',bg='#152536',fg='white',activebackground=RED,activeforeground='white',relief='flat',padx=28,pady=10,font=('Segoe UI Semibold',11),cursor='hand2')
            b.pack(fill='x',padx=14,pady=1); self.nav_buttons[t]=b
        tk.Label(self.sidebar,text='LA TUA AUTO,\nLA NOSTRA PASSIONE',bg='#152536',fg='white',font=('Segoe UI Semibold',9),justify='center').pack(side='bottom',pady=22)
        self.body=tk.Frame(self,bg=BG); self.body.pack(fill='both',expand=True)

    def _go(self,name,cmd):
        for n,b in self.nav_buttons.items():
            b.configure(bg=RED if n==name else '#152536')
        cmd()

    def wrap(self,title,sub=''):
        self.clear(); self.set_bg()
        w=tk.Frame(self.body,bg='#f5f7f9',highlightthickness=0)
        w.place(relx=.018,rely=.018,relwidth=.964,relheight=.964)
        h=tk.Frame(w,bg='#ffffff')
        h.pack(fill='x',padx=22,pady=(18,10))
        tk.Label(h,text=title,bg='white',fg=TEXT,font=('Segoe UI Semibold',25)).pack(anchor='w')
        tk.Label(h,text=sub,bg='white',fg=MUTED,font=('Segoe UI',10)).pack(anchor='w')
        return w

    def set_bg(self):
        c=tk.Canvas(self.body,highlightthickness=0,bg='#d4d9de')
        c.place(relx=0,rely=0,relwidth=1,relheight=1)
        try:
            logo=Image.open(LOGO_IMG).convert('RGBA')
        except Exception:
            return
        def draw(e=None):
            w=max(1,c.winfo_width()); h=max(1,c.winfo_height())
            base=Image.new('RGBA',(w,h),(191,199,205,255))
            lm=logo.copy(); lm.thumbnail((int(w*.84),int(h*.68)),Image.LANCZOS)
            alpha=lm.getchannel('A').point(lambda a: int(a*0.34)); lm.putalpha(alpha)
            base.alpha_composite(lm,((w-lm.width)//2,(h-lm.height)//2))
            veil=Image.new('RGBA',(w,h),(238,242,245,58)); base=Image.alpha_composite(base,veil)
            c._im=ImageTk.PhotoImage(base)
            c.delete('bg'); c.create_image(0,0,image=c._im,anchor='nw',tags='bg'); c.tag_lower('bg')
        c.bind('<Configure>',draw)

    def _fatture(self):
        w=self.wrap('Fatture','Sezione predisposta per fatture e documenti fiscali.')
        box=tk.Frame(w,bg='white',highlightbackground='#d7dee6',highlightthickness=1)
        box.pack(fill='both',expand=True,padx=24,pady=(0,20))
        tk.Label(box,text='Fatture',bg='white',fg=TEXT,font=('Segoe UI Semibold',20)).pack(pady=(45,8))
        tk.Label(box,text='Modulo pronto per la prossima integrazione funzionale.',bg='white',fg=MUTED,font=('Segoe UI',11)).pack()

    def _impostazioni(self):
        w=self.wrap('Impostazioni','Configurazione generale del gestionale LA PRIMA.')
        box=tk.Frame(w,bg='white',highlightbackground='#d7dee6',highlightthickness=1)
        box.pack(fill='both',expand=True,padx=24,pady=(0,20))
        tk.Label(box,text='Impostazioni',bg='white',fg=TEXT,font=('Segoe UI Semibold',20)).pack(pady=(45,8))
        tk.Label(box,text='Configurazioni officina, stampa e preferenze saranno raccolte qui.',bg='white',fg=MUTED,font=('Segoe UI',11)).pack()

    def dashboard(self):
        self.clear()
        for n,b in self.nav_buttons.items(): b.configure(bg=RED if n=='Dashboard' else '#152536')
        c=tk.Canvas(self.body,highlightthickness=0,bg='#dbe3e9'); c.pack(fill='both',expand=True)
        self._dash_canvas=c
        c.bind('<Configure>',self._paint_dashboard)

    def _paint_dashboard(self,event=None):
        c=self._dash_canvas; w=max(980,c.winfo_width()); h=max(760,c.winfo_height())
        base=Image.new('RGBA',(w,h),(183,193,201,255))
        try:
            logo=Image.open(LOGO_IMG).convert('RGBA')
            logo.thumbnail((int(w*.88),int(h*.72)),Image.LANCZOS)
            a=logo.getchannel('A').point(lambda v:int(v*0.38)); logo.putalpha(a)
            base.alpha_composite(logo,((w-logo.width)//2,(h-logo.height)//2))
        except Exception:
            pass
        shade=Image.new('RGBA',(w,h),(224,231,236,62)); base=Image.alpha_composite(base,shade)
        draw=ImageDraw.Draw(base,'RGBA')
        def panel(x1,y1,x2,y2,alpha=218,r=15): draw.rounded_rectangle((x1,y1,x2,y2),radius=r,fill=(255,255,255,alpha),outline=(190,201,212,155),width=1)
        pad=24; card_y=165; gap=14; usable=w-2*pad; card_w=(usable-3*gap)//4; card_h=105
        for i in range(4):
            x=pad+i*(card_w+gap); panel(x,card_y,x+card_w,card_y+card_h,220,14)
        cal_y=286; right_w=max(330,int(w*.30)); cal_w=w-3*pad-right_w; cal_h=455
        panel(pad,cal_y,pad+cal_w,cal_y+cal_h,205,15)
        panel(pad+cal_w+pad,cal_y,w-pad,cal_y+195,220,15)
        panel(pad+cal_w+pad,cal_y+210,w-pad,cal_y+350,220,15)
        bottom_y=cal_y+cal_h+14; panel(pad,bottom_y,pad+cal_w,bottom_y+215,220,15); panel(pad+cal_w+pad,bottom_y,w-pad,bottom_y+215,220,15)
        self._dash_img=ImageTk.PhotoImage(base); c.delete('all'); c.create_image(0,0,image=self._dash_img,anchor='nw')

        def txt(x,y,s,size=12,weight='normal',fill='#102033',anchor='nw'):
            font=('Segoe UI Semibold' if weight=='bold' else 'Segoe UI',size)
            c.create_text(x,y,text=s,font=font,fill=fill,anchor=anchor)
        txt(pad,38,'Dashboard',30,'bold')
        txt(pad,82,'Benvenuto in Officina LA PRIMA',15,'normal')
        txt(pad,106,'Gestisci il tuo lavoro, un cliente alla volta.',12,'normal')
        now=datetime.now(); txt(w-pad,40,now.strftime('%A %d %B %Y').capitalize(),11,'normal','#102033','ne'); txt(w-pad,63,now.strftime('%H:%M'),13,'bold','#102033','ne')

        vals=[('👥','Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c'],RED,'Totali nel database'),('🚗','Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c'],BLUE,'Totali nel database'),('🔧','Commesse Aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c'],ORANGE,'In lavorazione'),('✓','Auto pronte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN,'Da consegnare')]
        for i,(ico,title,val,col,sub) in enumerate(vals):
            x=pad+i*(card_w+gap); txt(x+20,card_y+20,ico,25,'bold',col); txt(x+76,card_y+20,title,12,'bold'); txt(x+76,card_y+45,str(val),27,'bold',col); txt(x+76,card_y+78,sub,10,'normal','#657585')

        txt(pad+20,cal_y+20,f'{self.MONTHNAME(self.cal_month)} {self.cal_year}',20,'bold')
        bx=pad+cal_w-160; c.create_rectangle(bx,cal_y+13,bx+38,cal_y+45,fill='#eef2f6',outline=''); c.create_text(bx+19,cal_y+29,text='‹',font=('Segoe UI Semibold',18),fill=TEXT)
        c.create_rectangle(bx+44,cal_y+13,bx+82,cal_y+45,fill='#eef2f6',outline=''); c.create_text(bx+63,cal_y+29,text='›',font=('Segoe UI Semibold',18),fill=TEXT)
        c.create_rectangle(bx+94,cal_y+13,bx+146,cal_y+45,fill=RED,outline=''); c.create_text(bx+120,cal_y+29,text='Oggi',font=('Segoe UI Semibold',10),fill='white')
        c.tag_bind('prev','<Button-1>',lambda e:self._nav_month(-1)); c.tag_bind('next','<Button-1>',lambda e:self._nav_month(1)); c.tag_bind('today','<Button-1>',lambda e:self._today_month())
        c.create_rectangle(bx,cal_y+13,bx+38,cal_y+45,outline='',tags='prev'); c.create_rectangle(bx+44,cal_y+13,bx+82,cal_y+45,outline='',tags='next'); c.create_rectangle(bx+94,cal_y+13,bx+146,cal_y+45,outline='',tags='today')
        self._draw_calendar(c,pad+16,cal_y+58,cal_w-32,cal_h-72,txt)

        rx=pad+cal_w+pad; txt(rx+18,cal_y+17,'🔔  Promemoria e scadenze',15,'bold'); txt(rx+18,cal_y+54,'Tutti     Tagliandi     Preventivi     Appuntamenti',9,'bold','#39495a')
        dn=self.db.one("SELECT COUNT(*) c FROM quotes WHERE status!='Inviato'")['c'] if self.db.one("SELECT COUNT(*) c FROM quotes") else 0
        txt(rx+right_w/2,cal_y+105,'▣',26,'normal','#8996a4','n'); txt(rx+right_w/2,cal_y+140,'Nessuna scadenza imminente' if dn==0 else f'{dn} preventivi da seguire',12,'bold','#6d7985','n')
        txt(rx+18,cal_y+227,'▥  Stato Officina',15,'bold')
        st=[('Tagliandi programmati',self.db.one('SELECT COUNT(*) c FROM services')['c'],BLUE),('Preventivi da inviare',dn,ORANGE),('Appuntamenti futuri',self.db.one("SELECT COUNT(*) c FROM appointments WHERE date>=date('now')")['c'],GREEN),('Commesse in lavorazione',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='In lavorazione'")['c'],RED),('Auto pronte alla consegna',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN)]
        yy=cal_y+262
        for label,n,col in st: txt(rx+20,yy,'●',9,'bold',col);txt(rx+38,yy,label,10);txt(w-pad-28,yy,str(n),10,'bold',TEXT,'ne');yy+=22

        txt(pad+18,bottom_y+16,'🔧  Commesse in evidenza',15,'bold'); self._draw_jobs(c,pad+18,bottom_y+52,cal_w-36,140,txt)
        txt(rx+18,bottom_y+16,'▣  Ultimi appuntamenti',15,'bold'); self._draw_apps(c,rx+18,bottom_y+52,right_w-36,140,txt)
        c.configure(scrollregion=(0,0,w,bottom_y+235))

    def MONTHNAME(self,m):
        return ['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'][m-1]

    def _nav_month(self,step):
        m=self.cal_month+step; y=self.cal_year
        if m<1:m=12;y-=1
        if m>12:m=1;y+=1
        self.cal_month=m;self.cal_year=y;self._paint_dashboard()
    def _today_month(self): self.cal_month=date.today().month;self.cal_year=date.today().year;self._paint_dashboard()

    def _draw_calendar(self,c,x,y,w,h,txt):
        cols=7; rows=6; head=26; cw=w/cols; rh=(h-head)/rows
        for i,n in enumerate(['Lun','Mar','Mer','Gio','Ven','Sab','Dom']): txt(x+i*cw+cw/2,y+5,n,9,'bold','#223449','n')
        for i in range(cols+1): c.create_line(x+i*cw,y+head,x+i*cw,y+h,fill='#b8c4cf')
        for r in range(rows+1): c.create_line(x,y+head+r*rh,x+w,y+head+r*rh,fill='#b8c4cf')
        weeks=calendar.Calendar().monthdayscalendar(self.cal_year,self.cal_month)
        apps=self.db.q("SELECT a.date,a.time,a.reason,c.name client,v.plate FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id WHERE substr(a.date,1,7)=? ORDER BY a.time",(f'{self.cal_year:04d}-{self.cal_month:02d}',)); by={}
        for a in apps: by.setdefault(int(a['date'][-2:]),[]).append(a)
        today=date.today()
        for r,wk in enumerate(weeks):
            for col,d in enumerate(wk):
                if not d: continue
                xx=x+col*cw+8; yy=y+head+r*rh+7
                if date(self.cal_year,self.cal_month,d)==today:
                    c.create_rectangle(xx-3,yy-2,xx+22,yy+20,fill=BLUE,outline=''); txt(xx+9,yy+1,str(d),10,'bold','white','n')
                else: txt(xx,yy,str(d),10,'bold')
                for j,a in enumerate(by.get(d,[])[:2]):
                    cy=yy+26+j*23; color=['#d8eaff','#d9f3e9','#ffe8c8','#ffdadd'][j%4]; c.create_rectangle(xx,cy,xx+cw-16,cy+18,fill=color,outline=''); txt(xx+6,cy+2,f"● {a['time'] or ''} - {a['reason'] or a['plate'] or ''}"[:28],8,'normal','#17334f')

    def _draw_jobs(self,c,x,y,w,h,txt):
        heads=['#','Cliente','Veicolo','Intervento','Stato','Consegna']; widths=[.12,.18,.16,.22,.17,.15]; rows=self.db.q("SELECT j.number,c.name,v.plate,j.issue,j.status,'' FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id WHERE j.status!='Consegnata' ORDER BY j.id DESC LIMIT 5")
        xx=x
        for i,h1 in enumerate(heads): txt(xx+4,y,h1,9,'bold');xx+=w*widths[i]
        yy=y+24
        for row in rows:
            xx=x
            for i,val in enumerate(row): txt(xx+4,yy,str(val or '')[:24],8);xx+=w*widths[i]
            c.create_line(x,yy+18,x+w,yy+18,fill='#d1d9e0');yy+=25
        if not rows: txt(x+w/2,y+60,'Nessuna commessa in evidenza',11,'bold','#7a8794','n')

    def _draw_apps(self,c,x,y,w,h,txt):
        rows=self.db.q("SELECT a.date,a.time,c.name,v.plate,a.reason FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id ORDER BY a.date DESC,a.time DESC LIMIT 4")
        yy=y
        if not rows: txt(x+w/2,y+55,'Nessun appuntamento',11,'bold','#7a8794','n'); return
        for row in rows:
            txt(x,yy,f"{row['date']}  {row['time'] or ''}",8,'bold'); txt(x,yy+14,f"{row['client'] or ''} · {row['plate'] or ''} · {row['reason'] or ''}"[:48],8); c.create_line(x,yy+34,x+w,yy+34,fill='#d1d9e0'); yy+=42

if __name__=='__main__':
    App().mainloop()
