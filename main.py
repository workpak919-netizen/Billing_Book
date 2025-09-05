"""
Billing App PK - Full Single File Version
----------------------------------------
یہ ایک مکمل Python (Kivy) ایپ ہے جو Mobile + PC دونوں پر چل سکتی ہے۔
اس میں Customers, Products, Billing, Reports, Settings سب شامل ہیں۔
Bills کو PDF اور JPG میں بھی export کیا جا سکتا ہے۔
"""
# --------------------------
# Imports
# --------------------------
import os
import json
import datetime
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from reportlab.pdfgen import canvas
from PIL import Image as PILImage, ImageDraw
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserIconView
from kivy.app import App
import os

def get_data_dir():
    try:
        app = App.get_running_app()
        return app.user_data_dir  # Android/desktop دونوں پر per-app dir
    except Exception:
        return os.path.join(os.getcwd(), "app_data")

DATA_DIR = get_data_dir()
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
BILLS_FILE    = os.path.join(DATA_DIR, "bills.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
os.makedirs(DATA_DIR, exist_ok=True)

# try Android share; desktop پر gracefully fallback
try:
    from plyer import share as plyer_share
    PLYER_SHARE = True
except Exception:
    PLYER_SHARE = False


try:
    from jnius import autoclass, cast
    from android import activity
    ANDROID = True
except ImportError:
    ANDROID = False



# --------------------------
# Global Config
# --------------------------
Window.size = (1000, 700)  # PC پر fix size, Mobile پر auto adjust ہوگا

DATA_DIR = "app_data"
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
BILLS_FILE = os.path.join(DATA_DIR, "bills.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# --------------------------
# Utility Functions
# --------------------------

def is_int(s): 
    try:
        int(s)
        return True
    except:
        return False

def is_float(s):
    try:
        float(s)
        return True
    except:
        return False

def load_data(file_path, default):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# --------------------------
# Base Classes
# --------------------------
class NavigationDrawer(BoxLayout):
    """Left side navigation menu"""
    def __init__(self, manager, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_x = None
        self.width = 220
        self.spacing = 5
        self.padding = 10
        self.manager = manager

        with self.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        title = Label(text="Bill Book",
                      font_size=20,
                      bold=True,
                      color=(1, 1, 1, 1),
                      size_hint_y=None,
                      height=60)
        self.add_widget(title)

        menu_items = [
            ("Home", "home"),
            ("Customers", "customers"),
            ("Products", "products"),
            ("New Bill", "billing"),
            ("Reports", "reports"),
            ("Settings", "settings"),
        ]

        for text, screen_name in menu_items:
            btn = Button(text=text,
                         font_size=16,
                         size_hint_y=None,
                         height=40,
                         background_normal="",
                         background_color=(0.2, 0.5, 0.8, 1))
            btn.bind(on_release=lambda btn, scr=screen_name: self.switch(scr))
            self.add_widget(btn)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def switch(self, screen_name):
        self.manager.current = screen_name

class BaseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="horizontal")
        self.content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.layout.add_widget(self.content)
        self.add_widget(self.layout)

    def on_pre_enter(self):
        # Navigation Drawer صرف ایک بار add کرو
        if not hasattr(self, "nav_added"):
            self.nav = NavigationDrawer(manager=self.manager)
            self.layout.add_widget(self.nav, index=0)  # left side add
            self.nav_added = True



class BaseScreen(Screen):
    """ہر screen کا base layout"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="horizontal")

        # navigation drawer (left side)
        self.nav = NavigationDrawer(manager=self.manager)
        self.layout.add_widget(self.nav)

        # main content (right side)
        self.content = BoxLayout(orientation="vertical", padding=20, spacing=10)
        self.layout.add_widget(self.content)

        self.add_widget(self.layout)

    def on_pre_enter(self):
        # اگر nav کا manager update نہ ہوا ہو تو fix کریں
        if self.nav.manager is None:
            self.nav.manager = self.manager

    def show_popup(self, title, msg):
        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        box.add_widget(Label(text=msg))
        btn = Button(text="OK", size_hint_y=None, height=40)
        box.add_widget(btn)
        popup = Popup(title=title, content=box, size_hint=(0.6, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()



# --------------------------
# Home Screen
# --------------------------
class HomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        title = Label(text="Welcome to HH Bill Book",
                      font_size=30,
                      bold=True,
                      size_hint_y=None,
                      height=70)
        self.content.add_widget(title)

        btn1 = Button(text="New Bill", font_size=22, size_hint_y=None, height=60)
        btn1.bind(on_release=lambda x: self.switch("billing"))
        self.content.add_widget(btn1)

        btn2 = Button(text="Previous Bills", font_size=22, size_hint_y=None, height=60)
        btn2.bind(on_release=lambda x: self.switch("reports"))
        self.content.add_widget(btn2)

        btn3 = Button(text="Add Product", font_size=22, size_hint_y=None, height=60)
        btn3.bind(on_release=lambda x: self.switch("products"))
        self.content.add_widget(btn3)

        btn4 = Button(text="Settings", font_size=22, size_hint_y=None, height=60)
        btn4.bind(on_release=lambda x: self.switch("settings"))
        self.content.add_widget(btn4)

    def switch(self, screen):
        self.manager.current = screen


# --------------------------
# Customers Screen
# --------------------------
class CustomersScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        title = Label(text="👤 Customers Management",
                      font_size=28,
                      bold=True,
                      size_hint_y=None,
                      height=60)
        self.content.add_widget(title)

        self.cname = TextInput(hint_text="Enter Customer Name",
                               font_size=18,
                               size_hint_y=None,
                               height=50)
        self.cphone = TextInput(hint_text="Enter Customer Phone",
                                font_size=18,
                                size_hint_y=None,
                                height=50)

        self.content.add_widget(self.cname)
        self.content.add_widget(self.cphone)

        save_btn = Button(text="Save Customer",
                          font_size=20,
                          size_hint_y=None,
                          height=60)
        save_btn.bind(on_release=lambda x: self.add_customer())
        self.content.add_widget(save_btn)

        self.scroll = ScrollView()
        self.grid = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.content.add_widget(self.scroll)

        self.refresh()

    def refresh(self):
        self.grid.clear_widgets()
        customers = load_data(CUSTOMERS_FILE, [])
        for c in customers:
            lbl = Label(text=f"{c['name']} - {c['phone']}",
                        font_size=18,
                        size_hint_y=None,
                        height=40)
            self.grid.add_widget(lbl)

    def add_customer(self):
        name = self.cname.text.strip()
        phone = self.cphone.text.strip()
        if not name:
            self.show_popup("Error", "Name required")
            return
        customers = load_data(CUSTOMERS_FILE, [])
        customers.append({"name": name, "phone": phone})
        save_data(CUSTOMERS_FILE, customers)
        self.cname.text = ""
        self.cphone.text = ""
        self.refresh()
        self.show_popup("Success", f"Customer {name} added")

# --------------------------
# Products Screen
# --------------------------
class ProductsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        title = Label(text="Products Management",
                      font_size=28,
                      bold=True,
                      size_hint_y=None,
                      height=60)
        self.content.add_widget(title)

        self.pname = TextInput(hint_text="Enter Product Name",
                               font_size=18,
                               size_hint_y=None,
                               height=50)
        self.pprice = TextInput(hint_text="Enter Product Price",
                                font_size=18,
                                size_hint_y=None,
                                height=50)

        self.content.add_widget(self.pname)
        self.content.add_widget(self.pprice)

        save_btn = Button(text="Save Product",
                          font_size=20,
                          size_hint_y=None,
                          height=60)
        save_btn.bind(on_release=lambda x: self.add_product())
        self.content.add_widget(save_btn)

        self.scroll = ScrollView()
        self.grid = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.content.add_widget(self.scroll)

        self.refresh()

    def refresh(self):
        self.grid.clear_widgets()
        products = load_data(PRODUCTS_FILE, [])
        for p in products:
            lbl = Label(text=f"{p['name']} - Rs. {p['price']}",
                        font_size=18,
                        size_hint_y=None,
                        height=40)
            self.grid.add_widget(lbl)

    def add_product(self):
        name = self.pname.text.strip()
        price = self.pprice.text.strip()
        if not name or not price.isdigit():
            self.show_popup("Error", "Valid name and price required")
            return
        products = load_data(PRODUCTS_FILE, [])
        products.append({"name": name, "price": int(price)})
        save_data(PRODUCTS_FILE, products)
        self.pname.text = ""
        self.pprice.text = ""
        self.refresh()
        self.show_popup("Success", f"Product {name} added")
# --------------------------
# Billing Screen
# --------------------------
from kivy.uix.spinner import Spinner   # 👈 یہ import ضرور اوپر شامل کریں


class BillingScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.bill_id = 1
        self.customer_name = ""
        self.customer_phone = ""
        self.items = []

        # Title
        title = Label(text="Create New Bill",
                      font_size=28,
                      bold=True,
                      size_hint_y=None,
                      height=60)
        self.content.add_widget(title)

        # Bill Info
        info_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
        self.lbl_bill_no = Label(text=f"Bill No: {self.bill_id}", font_size=18)
        self.lbl_date = Label(text=f"Date: {datetime.date.today()}", font_size=18)
        info_box.add_widget(self.lbl_bill_no)
        info_box.add_widget(self.lbl_date)
        self.content.add_widget(info_box)

        # Customer Info
        self.cname = TextInput(hint_text="Customer Name",
                               font_size=18,
                               size_hint_y=None,
                               height=50)
        self.cphone = TextInput(hint_text="Customer Phone",
                                font_size=18,
                                size_hint_y=None,
                                height=50)
        self.content.add_widget(self.cname)
        self.content.add_widget(self.cphone)

        # Items Title
        self.content.add_widget(Label(text="Items",
                                      font_size=22,
                                      bold=True,
                                      size_hint_y=None,
                                      height=40))

        # Items Grid
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
        header.add_widget(Label(text="Product", bold=True))
        header.add_widget(Label(text="Qty", bold=True))
        header.add_widget(Label(text="Price", bold=True))
        header.add_widget(Label(text="Total", bold=True))
        self.content.add_widget(header)

        self.scroll = ScrollView(size_hint_y=0.4)
        self.grid = GridLayout(cols=4, size_hint_y=None, row_default_height=35, row_force_default=True)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.content.add_widget(self.scroll)

        # Add Item Row
        add_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=5)

        products = load_data(PRODUCTS_FILE, [])
        product_names = [p["name"] for p in products]

        # 👇 Spinner for product selection
        self.prod_spinner = Spinner(
            text="Select Product",
            values=product_names,
            size_hint_x=0.4,
            font_size=16
        )
        self.prod_spinner.bind(text=self.update_price)

        self.prod_qty = TextInput(hint_text="Qty", font_size=16, size_hint_x=0.2)
        self.prod_price = TextInput(hint_text="Price", font_size=16, size_hint_x=0.2)

        add_btn = Button(text="➕ Add", font_size=16, size_hint_x=0.2)
        add_btn.bind(on_release=lambda x: self.add_item())

        add_row.add_widget(self.prod_spinner)
        add_row.add_widget(self.prod_qty)
        add_row.add_widget(self.prod_price)
        add_row.add_widget(add_btn)
        self.content.add_widget(add_row)

        # Subtotal
        self.lbl_total = Label(text="Subtotal: Rs. 0", font_size=18, size_hint_y=None, height=40)
        self.content.add_widget(self.lbl_total)

        # Buttons
        btn_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=60, spacing=10)
        save_btn = Button(text="Save Bill", font_size=18)
        save_btn.bind(on_release=lambda x: self.save_bill())
        pdf_btn = Button(text="Export PDF", font_size=18)
        pdf_btn.bind(on_release=lambda x: self.export_pdf())
        jpg_btn = Button(text="Export JPG", font_size=18)
        jpg_btn.bind(on_release=lambda x: self.export_jpg())
        btn_box.add_widget(save_btn)
        btn_box.add_widget(pdf_btn)
        btn_box.add_widget(jpg_btn)
        self.content.add_widget(btn_box)

        self.refresh_bill()

    def update_price(self, spinner, text):
        """Product select ہوتے ہی price auto fill ہو جائے"""
        products = load_data(PRODUCTS_FILE, [])
        for p in products:
            if p["name"] == text:
                self.prod_price.text = str(p["price"])
                break

    def refresh_bill(self):
        bills = load_data(BILLS_FILE, [])
        self.bill_id = len(bills) + 1
        self.lbl_bill_no.text = f"Bill No: {self.bill_id}"
        self.lbl_date.text = f"Date: {datetime.date.today()}"
        self.items = []
        self.grid.clear_widgets()
        self.lbl_total.text = "Subtotal: Rs. 0"

    def add_item(self):
        name = self.prod_spinner.text.strip()
        if name == "Select Product":
            self.show_popup("Error", "Please select a product")
            return

        qty = self.prod_qty.text.strip()
        price = self.prod_price.text.strip()
        if not qty.isdigit() or not price.replace('.', '', 1).isdigit():
            self.show_popup("Error", "Valid qty and price required")
            return
        qty, price = int(qty), float(price)
        total = qty * price
        item = {"product": name, "qty": qty, "price": price, "total": total}
        self.items.append(item)

        self.grid.add_widget(Label(text=name, font_size=16))
        self.grid.add_widget(Label(text=str(qty), font_size=16))
        self.grid.add_widget(Label(text=str(price), font_size=16))
        self.grid.add_widget(Label(text=str(total), font_size=16))

        self.lbl_total.text = f"Subtotal: Rs. {self.calc_total()}"

        self.prod_spinner.text = "Select Product"
        self.prod_qty.text = ""
        self.prod_price.text = ""

    def calc_total(self):
        return sum(item["total"] for item in self.items)

    def save_bill(self):
        customer_name = self.cname.text.strip()
        customer_phone = self.cphone.text.strip()
        if not customer_name:
            self.show_popup("Error", "Customer name required")
            return

        bill = {
            "id": self.bill_id,
            "date": str(datetime.date.today()),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "items": self.items,
            "total": self.calc_total()
        }
        bills = load_data(BILLS_FILE, [])
        bills.append(bill)
        save_data(BILLS_FILE, bills)

        self.show_popup("Success", f"Bill #{self.bill_id} saved")
        self.refresh_bill()

    from PIL import ImageFont

    def export_jpg(self):
        from PIL import Image as PILImage, ImageDraw, ImageFont
        import os

        file_path = f"Bill_{self.bill_id}.jpg"

        # Page size
        width, height = 600, 900
        img = PILImage.new("RGB", (width, height), "white")
        d = ImageDraw.Draw(img)

        # Load settings
        settings = load_data(SETTINGS_FILE, {"company": "My Company", "logo": ""})

        y = 20

        # --- Company Logo ---
        logo_path = settings.get("logo", "")
        if logo_path and os.path.exists(logo_path):
            try:
                logo = PILImage.open(logo_path).convert("RGBA")
                logo.thumbnail((120, 120))
                img.paste(logo, (width // 2 - logo.width // 2, y), logo)
                y += logo.height + 20
            except Exception as e:
                print("Logo load error:", e)

        # --- Fonts ---
        try:
            font_title = ImageFont.truetype("arial.ttf", 32)
            font_text = ImageFont.truetype("arial.ttf", 22)
            font_bold = ImageFont.truetype("arial.ttf", 26)
            font_watermark = ImageFont.truetype("arial.ttf", 18)
        except:
            font_title = font_text = font_bold = font_watermark = ImageFont.load_default()

        # --- Company Name Center ---
        company = settings.get("company", "My Company")
        bbox = d.textbbox((0, 0), company, font=font_title)
        text_w = bbox[2] - bbox[0]
        d.text(((width - text_w) / 2, y), company, font=font_title, fill="black")
        y += 50

        # --- Bill Info ---
        d.text((40, y), f"Bill No: {self.bill_id}", font=font_text, fill="black")
        d.text((350, y), f"Date: {datetime.date.today()}", font=font_text, fill="black")
        y += 30
        d.text((40, y), f"Customer: {self.cname.text}", font=font_text, fill="black")
        y += 25
        d.text((40, y), f"Phone: {self.cphone.text}", font=font_text, fill="black")
        y += 40

        # --- Table Header ---
        d.line((30, y, width - 30, y), fill="black", width=2)
        y += 10
        d.text((40, y), "Product", font=font_bold, fill="black")
        d.text((250, y), "Qty", font=font_bold, fill="black")
        d.text((330, y), "Price", font=font_bold, fill="black")
        d.text((450, y), "Total", font=font_bold, fill="black")
        y += 30
        d.line((30, y, width - 30, y), fill="black", width=2)
        y += 20

        # --- Items ---
        for item in self.items:
            d.text((40, y), str(item["product"]), font=font_text, fill="black")
            d.text((250, y), str(item["qty"]), font=font_text, fill="black")
            d.text((330, y), str(item["price"]), font=font_text, fill="black")
            d.text((450, y), str(item["total"]), font=font_text, fill="black")
            y += 25

        # --- Subtotal ---
        y += 20
        d.line((250, y, width - 30, y), fill="black", width=2)
        y += 25
        d.text((330, y), f"Sub Total: Rs. {self.calc_total()}", font=font_bold, fill="black")

        # --- Watermark at Bottom Center ---
        watermark = "HH Bill Book"
        bbox = d.textbbox((0, 0), watermark, font=font_watermark)
        text_w = bbox[2] - bbox[0]
        d.text(((width - text_w) / 2, height - 40), watermark, font=font_watermark, fill="gray")

        # Save File
        img.save(file_path)

        # Share or fallback
        if ANDROID:
            self.share_file_android(file_path, "image/jpeg")
        else:
            self.show_share_option(file_path)

        
 

    def export_pdf(self):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader

        import os

        file_path = f"Bill_{self.bill_id}.pdf"
        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        # --- Load settings ---
        settings = load_data(SETTINGS_FILE, {"company": "My Company", "logo": ""})

        y = height - 100  # Start from top

        # --- Company Logo ---
        logo_path = settings.get("logo", "")
        if logo_path and os.path.exists(logo_path):
            try:
                c.drawImage(ImageReader(logo_path), width/2 - 40, y - 60, 80, 80, preserveAspectRatio=True, mask='auto')
                y -= 100
            except Exception as e:
                print("PDF Logo error:", e)

        # --- Company Name Center ---
        company = settings.get("company", "My Company")
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, y, company)
        y -= 40

        # --- Bill Info ---
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Bill No: {self.bill_id}")
        c.drawRightString(width - 50, y, f"Date: {datetime.date.today()}")
        y -= 20
        c.drawString(50, y, f"Customer: {self.cname.text}")
        y -= 20
        c.drawString(50, y, f"Phone: {self.cphone.text}")
        y -= 30

        # --- Table Header ---
        c.setFont("Helvetica-Bold", 12)
        c.line(40, y, width - 40, y)
        y -= 15
        c.drawString(50, y, "Product")
        c.drawString(250, y, "Qty")
        c.drawString(320, y, "Price")
        c.drawString(400, y, "Total")
        y -= 15
        c.line(40, y, width - 40, y)
        y -= 20

        # --- Items ---
        c.setFont("Helvetica", 12)
        for item in self.items:
            c.drawString(50, y, str(item["product"]))
            c.drawString(250, y, str(item["qty"]))
            c.drawString(320, y, str(item["price"]))
            c.drawString(400, y, str(item["total"]))
            y -= 20

        # --- Subtotal ---
        y -= 10
        c.line(250, y, width - 40, y)
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 50, y, f"Sub Total: Rs. {self.calc_total()}")

        # --- Watermark (Bottom Center) ---
        c.setFont("Helvetica-Oblique", 10)
        c.setFillGray(0.6, 0.6)  # light gray
        c.drawCentredString(width/2, 30, "HH Bill Book")

        # Save PDF
        c.save()
        self.share_file_android(file_path, "application/pdf")
        if ANDROID:
            self.share_file_android(file_path, "application/pdf")
        else:
            self.show_share_option(file_path)  # Desktop/Laptop fallback




    def show_share_option(self, file_path):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        msg = Label(text=f"File saved:\n{file_path}", halign="center")
        layout.add_widget(msg)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        open_btn = Button(text="Open File")
        folder_btn = Button(text="Open Folder")
        btn_layout.add_widget(open_btn)
        btn_layout.add_widget(folder_btn)

        layout.add_widget(btn_layout)

        popup = Popup(title="Share / Open", content=layout, size_hint=(0.8, 0.4))

        def open_file(instance):
            import webbrowser, os
            webbrowser.open(file_path)
            popup.dismiss()

        def open_folder(instance):
            import os, subprocess
            folder = os.path.dirname(os.path.abspath(file_path))
            if os.name == 'nt':  # Windows
                os.startfile(folder)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.Popen(['xdg-open', folder])
            popup.dismiss()

        open_btn.bind(on_release=open_file)
        folder_btn.bind(on_release=open_folder)

        popup.open()

    def share_file_android(self, file_path, mime_type="application/pdf"):
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            File = autoclass('java.io.File')
            Uri = autoclass('android.net.Uri')

            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)

            # File as Uri
            file = File(file_path)
            uri = Uri.fromFile(file)

            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.setType(mime_type)
            intent.putExtra(Intent.EXTRA_STREAM, uri)

            chooser = Intent.createChooser(intent, "Share File")
            currentActivity.startActivity(chooser)

        except Exception as e:
            print("Share error:", e)
            self.show_popup("Error", f"Could not share file:\n{e}")






# --------------------------
# Reports Screen
# --------------------------
class ReportsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        title = Label(text="Reports",
                      font_size=28,
                      bold=True,
                      size_hint_y=None,
                      height=60)
        self.content.add_widget(title)

        self.scroll = ScrollView()
        self.grid = GridLayout(cols=1, size_hint_y=None, row_default_height=40, row_force_default=True)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.content.add_widget(self.scroll)

        self.refresh()

    def refresh(self):
        self.grid.clear_widgets()
        bills = load_data(BILLS_FILE, [])
        if not bills:
            self.grid.add_widget(Label(text="No bills saved yet", font_size=18))
            return
        for bill in bills:
            lbl = Label(text=f"Bill #{bill['id']} - {bill['customer_name']} - Rs.{bill['total']}",
                        font_size=18,
                        size_hint_y=None,
                        height=40)
            self.grid.add_widget(lbl)


# --------------------------
# Settings Screen
# --------------------------

class SettingsScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = Label(text="Settings", font_size=22, size_hint_y=None, height=50)
        self.content.add_widget(self.title)

        # Load old settings
        self.settings = load_data(SETTINGS_FILE, {"company": "My Company", "logo": "logo.png"})

        # Company Name Input
        self.cname = TextInput(text=self.settings.get("company", ""), hint_text="Company Name")
        self.content.add_widget(self.cname)

        # Logo Path + Browse Button
        box = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.logo_input = TextInput(text=self.settings.get("logo", "logo.png"), hint_text="Logo Path")
        browse_btn = Button(text="Browse", size_hint_x=None, width=100)
        browse_btn.bind(on_release=self.browse_logo)
        box.add_widget(self.logo_input)
        box.add_widget(browse_btn)
        self.content.add_widget(box)

        # Save Button
        save_btn = Button(text="Save Settings", size_hint_y=None, height=50)
        save_btn.bind(on_release=self.save_settings)
        self.content.add_widget(save_btn)

    def browse_logo(self, *args):
        # File chooser popup
        chooser = FileChooserIconView(path=".", filters=["*.png", "*.jpg", "*.jpeg"])
        box = BoxLayout(orientation="vertical")
        box.add_widget(chooser)

        select_btn = Button(text="Select", size_hint_y=None, height=40)
        popup = Popup(title="Select Logo", content=box, size_hint=(0.9, 0.9))

        def select_file(instance):
            if chooser.selection:
                self.logo_input.text = chooser.selection[0]
                popup.dismiss()

        select_btn.bind(on_release=select_file)
        box.add_widget(select_btn)
        popup.open()

    


    def refresh(self):
        settings = load_data(SETTINGS_FILE, {"company": "", "phone": "", "address": "", "gstin": "", "currency": "Rs."})
        self.company.text = settings["company"]
        self.phone.text = settings["phone"]
        self.address.text = settings["address"]
        self.gstin.text = settings["gstin"]
        self.currency.text = settings["currency"]

    def save_settings(self, *args):
        import shutil, uuid, os, traceback
        try:
            self.settings["company"] = self.cname.text.strip()[:100]

            selected = self.logo_input.text.strip()
            if selected and os.path.exists(selected):
                ext = os.path.splitext(selected)[1].lower()
                if ext not in [".png", ".jpg", ".jpeg"]:
                    raise ValueError("Only PNG/JPG logos allowed.")
                safe_name = f"logo_{uuid.uuid4().hex}{ext}"
                dest = os.path.join(DATA_DIR, safe_name)
                shutil.copyfile(selected, dest)
                self.settings["logo"] = dest
            # اگر کچھ نہ ملا تو پچھلا ہی رہنے دیں یا خالی
            save_data(SETTINGS_FILE, self.settings)
            self.show_popup("Saved", "Company name and logo updated successfully!")
        except Exception as e:
            self.show_popup("Error", f"Settings save failed:\n{e}")



# --------------------------
# Main App Class
# --------------------------
class BillingApp(App):
    def build(self):
        self.title = "Billing App PK (Full Version)"

        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(CustomersScreen(name="customers"))
        sm.add_widget(ProductsScreen(name="products"))
        sm.add_widget(BillingScreen(name="billing"))
        sm.add_widget(ReportsScreen(name="reports"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm


# --------------------------
# Run App
# --------------------------
if __name__ == "__main__":
    BillingApp().run()

