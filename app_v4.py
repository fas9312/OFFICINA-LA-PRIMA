import tkinter as tk
from datetime import date, datetime
from PIL import Image, ImageTk, ImageDraw

from app_visual import App as VisualApp, LOGO_IMG, RED, TEXT, BLUE, GREEN, ORANGE

class App(VisualApp):
    DASH_H = 1120

    def dashboard(self):
        self.clear()
        for n,b in self.nav_buttons.items():
            b.configure(bg=RED if n=='Dashboard' else '#152536')

        holder=tk.Frame(self.body,bg='#b7c1c9')
        holder.pack(fill='both',expand=True)
        sb=tk.Scrollbar(holder,orient='vertical')
        sb.pack(side='right',fill='y')
        c=tk.Canvas(holder,highlightthickness=0,bg='#b7c1c9',yscrollcommand=sb.set)
        c.pack(side='left',fill='both',expand=True)
        sb.config(command=c.yview)
        self._dash_canvas=c
        c.bind('<Configure>',self._paint_dashboard_v4)
        c.bind('<Enter>',lambda e:c.bind_all('<MouseWheel>',self._wheel_v4))
        c.bind('<Leave>',lambda e:c.unbind_all('<MouseWheel>'))

    def _wheel_v4(self,event):
        if event.delta:
            self._dash_canvas.yview_scroll(int(-event.delta/120),'units')

    def _paint_dashboard_v4(self,event=None):
        c=self._dash_canvas
        w=max(1040,c.winfo_width())
        H=self.DASH_H

        base=Image.new('RGBA',(w,H),(180,190,199,255))
        try:
            logo=Image.open(LOGO_IMG).convert('RGBA')
            logo.thumbnail((int(w*0.84),int(H*0.62)),Image.LANCZOS)
            if 'A' not in logo.getbands(): logo.putalpha(255)
            alpha=logo.getchannel('A').point(lambda v:int(v*0.45))
            logo.putalpha(alpha)
            base.alpha_composite(logo,((w-logo.width)//2,155))
        except Exception:
            pass

        base=Image.alpha_composite(base,Image.new('RGBA',(w,H),(236,241,244,26)))
        draw=ImageDraw.Draw(base,'RGBA')
        def panel(x1,y1,x2,y2,a=180,r=16):
            draw.rounded_rectangle((x1,y1,x2,y2),radius=r,fill=(255,255,255,a),outline=(180,191,201,135),width=1)

        pad=24; gap=14; card_y=160; card_h=108
        usable=w-2*pad; card_w=(usable-3*gap)//4
        for i in range(4):
            x=pad+i*(card_w+gap)
            panel(x,card_y,x+card_w,card_y+card_h,188,14)

        cal_y=286; right_w=max(330,int(w*.30)); cal_w=w-3*pad-right_w; cal_h=470
        panel(pad,cal_y,pad+cal_w,cal_y+cal_h,168,16)
        panel(pad+cal_w+pad,cal_y,w-pad,cal_y+205,178,16)
        panel(pad+cal_w+pad,cal_y+220,w-pad,cal_y+365,178,16)
        bottom_y=cal_y+cal_h+16
        panel(pad,bottom_y,pad+cal_w,bottom_y+245,178,16)
        panel(pad+cal_w+pad,bottom_y,w-pad,bottom_y+245,178,16)

        self._dash_img=ImageTk.PhotoImage(base)
        c.delete('all')
        c.create_image(0,0,image=self._dash_img,anchor='nw')
        c.configure(scrollregion=(0,0,w,H))

        def txt(x,y,s,size=12,weight='normal',fill='#102033',anchor='nw'):
            font=('Segoe UI Semibold' if weight=='bold' else 'Segoe UI',size)
            c.create_text(x,y,text=s,font=font,fill=fill,anchor=anchor)

        txt(pad,34,'Dashboard',30,'bold')
        txt(pad,78,'Benvenuto in Officina LA PRIMA',15)
        txt(pad,104,'Gestisci il tuo lavoro, un cliente alla volta.',12)
        now=datetime.now()
        txt(w-pad,36,now.strftime('%A %d %B %Y').capitalize(),11,'normal','#102033','ne')
        txt(w-pad,60,now.strftime('%H:%M'),13,'bold','#102033','ne')

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
            txt(x+76,card_y+80,sub,10,'normal','#657585')

        txt(pad+20,cal_y+20,f'{self.MONTHNAME(self.cal_month)} {self.cal_year}',20,'bold')
        bx=pad+cal_w-160
        c.create_rectangle(bx,cal_y+13,bx+38,cal_y+45,fill='#eef2f6',outline='',tags='prev')
        c.create_text(bx+19,cal_y+29,text='‹',font=('Segoe UI Semibold',18),fill=TEXT)
        c.create_rectangle(bx+44,cal_y+13,bx+82,cal_y+45,fill='#eef2f6',outline='',tags='next')
        c.create_text(bx+63,cal_y+29,text='›',font=('Segoe UI Semibold',18),fill=TEXT)
        c.create_rectangle(bx+94,cal_y+13,bx+146,cal_y+45,fill=RED,outline='',tags='today')
        c.create_text(bx+120,cal_y+29,text='Oggi',font=('Segoe UI Semibold',10),fill='white')
        c.tag_bind('prev','<Button-1>',lambda e:self._nav_month(-1))
        c.tag_bind('next','<Button-1>',lambda e:self._nav_month(1))
        c.tag_bind('today','<Button-1>',lambda e:self._today_month())
        self._draw_calendar(c,pad+16,cal_y+58,cal_w-32,cal_h-72,txt)

        rx=pad+cal_w+pad
        txt(rx+18,cal_y+17,'🔔  Promemoria e scadenze',15,'bold')
        txt(rx+18,cal_y+54,'Tutti     Tagliandi     Preventivi     Appuntamenti',9,'bold','#39495a')
        dn=self.db.one("SELECT COUNT(*) c FROM quotes WHERE status!='Inviato'")['c']
        txt(rx+right_w/2,cal_y+112,'▣',26,'normal','#8996a4','n')
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
            txt(rx+20,yy,'●',9,'bold',col)
            txt(rx+38,yy,label,10)
            txt(w-pad-28,yy,str(n),10,'bold',TEXT,'ne')
            yy+=22

        txt(pad+18,bottom_y+16,'🔧  Commesse in evidenza',15,'bold')
        self._draw_jobs(c,pad+18,bottom_y+52,cal_w-36,165,txt)
        txt(rx+18,bottom_y+16,'▣  Ultimi appuntamenti',15,'bold')
        self._draw_apps(c,rx+18,bottom_y+52,right_w-36,165,txt)

if __name__=='__main__':
    App().mainloop()
