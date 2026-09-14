import base64
from io import BytesIO
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageTk, ImageDraw

from app_v5 import App as V5App
from app import RES_DIR, RED, TEXT, BLUE, GREEN, ORANGE

# Fallback incorporato nell'EXE: logo reale LA PRIMA. Viene usato solo se
# l'asset esterno non viene trovato dal bundle PyInstaller.
FALLBACK_LOGO_B64 = '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'


class App(V5App):
    """V6: SOLO correzione grafica logo/background. Funzioni V5 invariate."""

    DASH_H = 1140

    def _load_assets(self):
        # Prova prima il logo ufficiale ad alta risoluzione incluso nel bundle.
        candidates = [
            RES_DIR / 'assets' / 'la_prima_logo_official.png',
            RES_DIR / 'assets' / 'la_prima_logo.png',
        ]
        src = None
        for p in candidates:
            try:
                if p.exists():
                    src = Image.open(p).convert('RGBA')
                    break
            except Exception:
                src = None
        if src is None:
            # Fallback incorporato: il logo non può più sparire dall'EXE.
            src = Image.open(BytesIO(base64.b64decode(FALLBACK_LOGO_B64))).convert('RGBA')

        # Toglie solo il fondo bianco; il logo non viene ridisegnato.
        data = []
        for r, g, b, a in src.getdata():
            data.append((255,255,255,0) if r > 245 and g > 245 and b > 245 else (r,g,b,a))
        src.putdata(data)
        self.logo_src = src
        self.bg_src = src.copy()

        side = src.copy()
        side.thumbnail((268, 126), Image.LANCZOS)
        self.logo_tk = ImageTk.PhotoImage(side)

    def _paint_dashboard_v4(self, event=None):
        c = self._dash_canvas
        w = max(1040, c.winfo_width())
        H = self.DASH_H

        # BACKGROUND REALE DELLA HOME: logo ufficiale dietro TUTTI gli elementi.
        base = Image.new('RGBA', (w, H), (214, 220, 225, 255))
        logo = self.logo_src.copy()
        logo.thumbnail((int(w * 0.92), int(H * 0.58)), Image.LANCZOS)
        logo.putalpha(logo.getchannel('A').point(lambda v: int(v * 0.78)))
        base.alpha_composite(logo, ((w - logo.width)//2, 115))

        logo2 = self.logo_src.copy()
        logo2.thumbnail((int(w * 0.64), int(H * 0.30)), Image.LANCZOS)
        logo2.putalpha(logo2.getchannel('A').point(lambda v: int(v * 0.28)))
        base.alpha_composite(logo2, ((w - logo2.width)//2, 790))

        draw = ImageDraw.Draw(base, 'RGBA')
        def panel(x1,y1,x2,y2,a=145,r=16):
            draw.rounded_rectangle((x1,y1,x2,y2), radius=r,
                                   fill=(255,255,255,a),
                                   outline=(171,184,195,170), width=1)

        pad=24; gap=14; card_y=160; card_h=108
        usable=w-2*pad; card_w=(usable-3*gap)//4
        for i in range(4):
            x=pad+i*(card_w+gap); panel(x,card_y,x+card_w,card_y+card_h,152,15)

        cal_y=286; right_w=max(330,int(w*.30)); cal_w=w-3*pad-right_w; cal_h=470
        panel(pad,cal_y,pad+cal_w,cal_y+cal_h,136,16)
        panel(pad+cal_w+pad,cal_y,w-pad,cal_y+205,148,16)
        panel(pad+cal_w+pad,cal_y+220,w-pad,cal_y+365,148,16)
        bottom_y=cal_y+cal_h+16
        panel(pad,bottom_y,pad+cal_w,bottom_y+245,148,16)
        panel(pad+cal_w+pad,bottom_y,w-pad,bottom_y+245,148,16)

        self._dash_img=ImageTk.PhotoImage(base)
        c.delete('all')
        c.create_image(0,0,image=self._dash_img,anchor='nw')
        c.configure(scrollregion=(0,0,w,H))

        def txt(x,y,s,size=12,weight='normal',fill='#102033',anchor='nw'):
            font=('Segoe UI Semibold' if weight=='bold' else 'Segoe UI',size)
            c.create_text(x,y,text=s,font=font,fill=fill,anchor=anchor)

        txt(pad,34,'Dashboard',30,'bold')
        txt(pad,78,'Benvenuto in Officina LA PRIMA',15)
        txt(pad,104,'Gestisci il tuo lavoro, un cliente alla volta.',12,fill='#314455')
        now=datetime.now()
        txt(w-pad,36,now.strftime('%d/%m/%Y'),11,anchor='ne')
        txt(w-pad,60,now.strftime('%H:%M'),13,'bold',anchor='ne')

        vals=[
            ('👥','Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c'],RED,'Totali nel database'),
            ('🚗','Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c'],BLUE,'Totali nel database'),
            ('🔧','Commesse Aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c'],ORANGE,'In lavorazione'),
            ('✓','Auto pronte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN,'Da consegnare')]
        for i,(ico,title,val,col,sub) in enumerate(vals):
            x=pad+i*(card_w+gap)
            txt(x+20,card_y+20,ico,25,'bold',col)
            txt(x+76,card_y+20,title,12,'bold')
            txt(x+76,card_y+46,str(val),27,'bold',col)
            txt(x+76,card_y+80,sub,10,fill='#657585')

        txt(pad+20,cal_y+20,f'{self.MONTHNAME(self.cal_month)} {self.cal_year}',20,'bold')
        bx=pad+cal_w-160
        c.create_rectangle(bx,cal_y+13,bx+38,cal_y+45,fill='#eef2f6',outline='',tags='prev')
        c.create_text(bx+19,cal_y+29,text='‹',font=('Segoe UI Semibold',18),fill=TEXT,tags='prev')
        c.create_rectangle(bx+44,cal_y+13,bx+82,cal_y+45,fill='#eef2f6',outline='',tags='next')
        c.create_text(bx+63,cal_y+29,text='›',font=('Segoe UI Semibold',18),fill=TEXT,tags='next')
        c.create_rectangle(bx+94,cal_y+13,bx+146,cal_y+45,fill=RED,outline='',tags='today')
        c.create_text(bx+120,cal_y+29,text='Oggi',font=('Segoe UI Semibold',10),fill='white',tags='today')
        c.tag_bind('prev','<Button-1>',lambda e:self._nav_month(-1))
        c.tag_bind('next','<Button-1>',lambda e:self._nav_month(1))
        c.tag_bind('today','<Button-1>',lambda e:self._today_month())

        self._draw_calendar(c,pad+16,cal_y+58,cal_w-32,cal_h-72,txt)

        rx=pad+cal_w+pad
        txt(rx+18,cal_y+17,'🔔  Promemoria e scadenze',15,'bold')
        txt(rx+18,cal_y+54,'Tutti     Tagliandi     Preventivi     Appuntamenti',9,'bold','#39495a')
        dn=self.db.one("SELECT COUNT(*) c FROM quotes WHERE status!='Inviato'")['c']
        txt(rx+right_w/2,cal_y+112,'▣',26,fill='#8996a4',anchor='n')
        txt(rx+right_w/2,cal_y+150,'Nessuna scadenza imminente' if dn==0 else f'{dn} preventivi da seguire',12,'bold','#6d7985','n')

        txt(rx+18,cal_y+237,'▥  Stato Officina',15,'bold')
        st=[
            ('Tagliandi programmati',self.db.one('SELECT COUNT(*) c FROM services')['c'],BLUE),
            ('Preventivi da inviare',dn,ORANGE),
            ('Appuntamenti futuri',self.db.one("SELECT COUNT(*) c FROM appointments WHERE date>=date('now')")['c'],GREEN),
            ('Commesse in lavorazione',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='In lavorazione'")['c'],RED),
            ('Auto pronte alla consegna',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN)]
        yy=cal_y+272
        for label,n,col in st:
            txt(rx+20,yy,'●',9,'bold',col); txt(rx+38,yy,label,10)
            txt(w-pad-28,yy,str(n),10,'bold',TEXT,'ne'); yy+=22

        txt(pad+18,bottom_y+16,'🔧  Commesse in evidenza',15,'bold')
        self._draw_jobs(c,pad+18,bottom_y+52,cal_w-36,165,txt)
        txt(rx+18,bottom_y+16,'▣  Ultimi appuntamenti',15,'bold')
        self._draw_apps(c,rx+18,bottom_y+52,right_w-36,165,txt)

        # Mantiene le funzioni reali della V5: frecce/Oggi/click sui giorni.
        c.bind('<Button-1>',self._dashboard_click_v5)


if __name__=='__main__':
    App().mainloop()
