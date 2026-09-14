import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
import calendar
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageEnhance

from app_visual import App as VisualApp
from app import RES_DIR, RED, TEXT, BLUE, GREEN, ORANGE

OFFICIAL_LOGO = RES_DIR / 'assets' / 'la_prima_logo_official.png'
SIDEBAR = '#132638'
SIDEBAR_2 = '#0f1f2f'
PANEL_BORDER = (255,255,255,105)


class App(VisualApp):
    """V4: vera dashboard scrollabile + logo ufficiale come background visibile."""

    def _transparent_logo(self, image: Image.Image) -> Image.Image:
        im = image.convert('RGBA')
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r,g,b,a = px[x,y]
                if r > 244 and g > 244 and b > 244:
                    px[x,y] = (255,255,255,0)
        return im

    def _load_assets(self):
        self.logo_src = None
        self.logo_tk = None
        try:
            self.logo_src = self._transparent_logo(Image.open(OFFICIAL_LOGO))
            side = self.logo_src.copy()
            side.thumbnail((268, 124), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(side)
        except Exception:
            self.logo_src = None

    def _shell(self):
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=292)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR, height=176)
        brand.pack(fill='x')
        brand.pack_propagate(False)
        if self.logo_tk:
            tk.Label(brand, image=self.logo_tk, bg=SIDEBAR, bd=0).pack(pady=(14, 4))
        else:
            tk.Label(brand, text='OFFICINA\n“LA PRIMA”', bg=SIDEBAR, fg='white', font=('Segoe UI Black', 24)).pack(pady=28)
        self.nav_buttons = {}
        items = [
            ('⌂','Dashboard',self.dashboard),('👥','Clienti',self.clients),('🚗','Veicoli',self.vehicles),
            ('🔧','Commesse',self.jobs),('▣','Appuntamenti',self.appointments),('⚙','Tagliandi',self.services),
            ('▤','Preventivi',self.quotes),('▤','Fatture',self._fatture),('▦','Magazzino',self.inventory),
            ('▣','Fornitori',self.suppliers),('◷','Scadenze',self.deadlines),('▥','Report',self.report),
            ('◉','Backup',self.backup),('⚙','Impostazioni',self._impostazioni)
        ]
        for icon, title, cmd in items:
            b = tk.Button(self.sidebar, text=f'{icon}   {title}', command=lambda n=title,c=cmd:self._go(n,c),
                anchor='w', bg=SIDEBAR, fg='white', activebackground=RED, activeforeground='white',
                relief='flat', bd=0, padx=28, pady=9, font=('Segoe UI Semibold',11), cursor='hand2')
            b.pack(fill='x', padx=14, pady=1)
            self.nav_buttons[title] = b
        tk.Label(self.sidebar, text='LA TUA AUTO,\nLA NOSTRA PASSIONE', bg=SIDEBAR, fg='white',
                 font=('Segoe UI Semibold',9), justify='center').pack(side='bottom', pady=18)
        self.body = tk.Frame(self, bg='#152433')
        self.body.pack(fill='both', expand=True)

    def _go(self, name, cmd):
        for n,b in self.nav_buttons.items():
            b.configure(bg=RED if n == name else SIDEBAR)
        cmd()

    def set_bg(self):
        c = tk.Canvas(self.body, highlightthickness=0, bd=0, bg='#203447')
        c.place(relx=0, rely=0, relwidth=1, relheight=1)
        def redraw(e=None):
            w=max(1,c.winfo_width()); h=max(1,c.winfo_height())
            base = Image.new('RGBA',(w,h),(22,37,52,255))
            if self.logo_src:
                logo = self.logo_src.copy()
                logo.thumbnail((int(w*.88), int(h*.72)), Image.LANCZOS)
                a = logo.getchannel('A').point(lambda v: int(v*0.30))
                logo.putalpha(a)
                base.alpha_composite(logo, ((w-logo.width)//2, (h-logo.height)//2))
            base = Image.alpha_composite(base, Image.new('RGBA',(w,h),(255,255,255,18)))
            c._img = ImageTk.PhotoImage(base)
            c.delete('bg'); c.create_image(0,0,image=c._img,anchor='nw',tags='bg'); c.tag_lower('bg')
        c.bind('<Configure>', redraw)

    def dashboard(self):
        self.clear()
        for n,b in self.nav_buttons.items():
            b.configure(bg=RED if n=='Dashboard' else SIDEBAR)
        host = tk.Frame(self.body, bg='#142638')
        host.pack(fill='both', expand=True)
        self._dash_canvas = tk.Canvas(host, highlightthickness=0, bd=0, bg='#142638')
        self._dash_scroll = ttk.Scrollbar(host, orient='vertical', command=self._dash_canvas.yview)
        self._dash_canvas.configure(yscrollcommand=self._dash_scroll.set)
        self._dash_scroll.pack(side='right', fill='y')
        self._dash_canvas.pack(side='left', fill='both', expand=True)
        self._dash_canvas.bind('<Configure>', self._paint_dashboard)
        self._dash_canvas.bind('<Enter>', lambda e:self._dash_canvas.bind_all('<MouseWheel>', self._wheel_dashboard))
        self._dash_canvas.bind('<Leave>', lambda e:self._dash_canvas.unbind_all('<MouseWheel>'))
        self.after(60, self._paint_dashboard)

    def _wheel_dashboard(self, event):
        self._dash_canvas.yview_scroll(int(-event.delta/120), 'units')

    def _panel(self, draw, box, alpha=188, radius=16):
        draw.rounded_rectangle(box, radius=radius, fill=(247,250,252,alpha), outline=PANEL_BORDER, width=1)

    def _background(self, w, virtual_h):
        base = Image.new('RGBA',(w,virtual_h),(24,41,57,255))
        if self.logo_src:
            logo = self.logo_src.copy()
            logo.thumbnail((int(w*.88), int(virtual_h*.64)), Image.LANCZOS)
            a = logo.getchannel('A').point(lambda v: int(v*0.27))
            logo.putalpha(a)
            x=(w-logo.width)//2; y=max(120,(virtual_h-logo.height)//2-80)
            base.alpha_composite(logo,(x,y))
        return Image.alpha_composite(base, Image.new('RGBA',(w,virtual_h),(255,255,255,20)))

    def _paint_dashboard(self, event=None):
        c = self._dash_canvas
        w = max(1050, c.winfo_width())
        viewport_h = max(720, c.winfo_height())
        virtual_h = max(1120, viewport_h + 220)
        base = self._background(w, virtual_h)
        draw = ImageDraw.Draw(base, 'RGBA')
        pad=24; gap=14; card_y=160; card_h=104; usable=w-2*pad; card_w=(usable-3*gap)//4
        for i in range(4):
            x=pad+i*(card_w+gap); self._panel(draw,(x,card_y,x+card_w,card_y+card_h),182,16)
        cal_y=282; right_w=max(330,int(w*.30)); cal_w=w-3*pad-right_w; cal_h=455
        self._panel(draw,(pad,cal_y,pad+cal_w,cal_y+cal_h),172,16)
        self._panel(draw,(pad+cal_w+pad,cal_y,w-pad,cal_y+195),182,16)
        self._panel(draw,(pad+cal_w+pad,cal_y+210,w-pad,cal_y+350),182,16)
        bottom_y=cal_y+cal_h+14
        self._panel(draw,(pad,bottom_y,pad+cal_w,bottom_y+245),184,16)
        self._panel(draw,(pad+cal_w+pad,bottom_y,w-pad,bottom_y+245),184,16)
        self._dash_img = ImageTk.PhotoImage(base)
        c.delete('all'); c.create_image(0,0,image=self._dash_img,anchor='nw')
        def txt(x,y,s,size=12,weight='normal',fill='#102033',anchor='nw'):
            font=('Segoe UI Semibold' if weight=='bold' else 'Segoe UI', size)
            c.create_text(x,y,text=s,font=font,fill=fill,anchor=anchor)
        txt(pad,34,'Dashboard',30,'bold','white')
        txt(pad,78,'Benvenuto in Officina LA PRIMA',15,'normal','#f4f7fa')
        txt(pad,103,'Gestisci il tuo lavoro, un cliente alla volta.',12,'normal','#d9e2e9')
        now=datetime.now(); txt(w-pad,36,now.strftime('%d/%m/%Y'),11,'normal','#f4f7fa','ne'); txt(w-pad,60,now.strftime('%H:%M'),13,'bold','#ffffff','ne')
        vals=[
            ('👥','Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c'],RED,'Totali nel database'),
            ('🚗','Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c'],BLUE,'Totali nel database'),
            ('🔧','Commesse Aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c'],ORANGE,'In lavorazione'),
            ('✓','Auto pronte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN,'Da consegnare')]
        for i,(ico,title,val,col,sub) in enumerate(vals):
            x=pad+i*(card_w+gap); txt(x+20,card_y+19,ico,25,'bold',col); txt(x+76,card_y+20,title,12,'bold'); txt(x+76,card_y+45,str(val),27,'bold',col); txt(x+76,card_y+78,sub,10,'normal','#657585')
        txt(pad+20,cal_y+18,f'{self.MONTHNAME(self.cal_month)} {self.cal_year}',20,'bold')
        bx=pad+cal_w-160
        for off,label,fill,tag in [(0,'‹','#eef2f6','prev'),(44,'›','#eef2f6','next'),(94,'Oggi',RED,'today')]:
            ww=38 if off<90 else 52
            c.create_rectangle(bx+off,cal_y+13,bx+off+ww,cal_y+45,fill=fill,outline='',tags=tag)
            c.create_text(bx+off+ww/2,cal_y+29,text=label,font=('Segoe UI Semibold',18 if off<90 else 10),fill='white' if fill==RED else TEXT,tags=tag)
        c.tag_bind('prev','<Button-1>',lambda e:self._nav_month(-1)); c.tag_bind('next','<Button-1>',lambda e:self._nav_month(1)); c.tag_bind('today','<Button-1>',lambda e:self._today_month())
        self._draw_calendar(c,pad+16,cal_y+58,cal_w-32,cal_h-72,txt)
        rx=pad+cal_w+pad
        txt(rx+18,cal_y+16,'🔔  Promemoria e scadenze',15,'bold')
        txt(rx+18,cal_y+52,'Tutti     Tagliandi     Preventivi     Appuntamenti',9,'bold','#39495a')
        dn=self.db.one("SELECT COUNT(*) c FROM quotes WHERE status!='Inviato'")['c']
        txt(rx+right_w/2,cal_y+104,'▣',26,'normal','#8996a4','n'); txt(rx+right_w/2,cal_y+140,'Nessuna scadenza imminente' if dn==0 else f'{dn} preventivi da seguire',12,'bold','#6d7985','n')
        txt(rx+18,cal_y+226,'▥  Stato Officina',15,'bold')
        st=[('Tagliandi programmati',self.db.one('SELECT COUNT(*) c FROM services')['c'],BLUE),('Preventivi da inviare',dn,ORANGE),('Appuntamenti futuri',self.db.one("SELECT COUNT(*) c FROM appointments WHERE date>=date('now')")['c'],GREEN),('Commesse in lavorazione',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='In lavorazione'")['c'],RED),('Auto pronte alla consegna',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN)]
        yy=cal_y+260
        for label,n,col in st:
            txt(rx+20,yy,'●',9,'bold',col); txt(rx+38,yy,label,10); txt(w-pad-28,yy,str(n),10,'bold',TEXT,'ne'); yy+=22
        txt(pad+18,bottom_y+16,'🔧  Commesse in evidenza',15,'bold'); self._draw_jobs(c,pad+18,bottom_y+52,cal_w-36,165,txt)
        txt(rx+18,bottom_y+16,'▣  Ultimi appuntamenti',15,'bold'); self._draw_apps(c,rx+18,bottom_y+52,right_w-36,165,txt)
        c.configure(scrollregion=(0,0,w,virtual_h))

if __name__ == '__main__':
    App().mainloop()
