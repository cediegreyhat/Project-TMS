import datetime
import os
import tkinter as tk
from tkinter import StringVar, ttk
import customtkinter as ctk
from tkinter import messagebox
from tkinter import simpledialog
from PIL import Image, ImageTk, ImageDraw
from matplotlib.figure import Figure
from database import DatabaseManager
from service import AuthService, ServiceError, ToolService
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from colorama import Fore, Style

RETURN_EVENT = "<Return>"

VIEW_TOOLS_TITLE = "View Tools"



ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("dark-blue")


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#23272f", foreground="#4f8cff", relief="solid", borderwidth=1)
        label.pack()

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class AdvancedToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.text = ""
        self.row_id = None

    def show(self, text, x, y):
        self.hide()
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=text, background="#23272f", foreground="#4f8cff",
            relief="solid", borderwidth=1, font=("Roboto", 11), justify="left", anchor="w"
        )
        label.pack(ipadx=8, ipady=4)

    def hide(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class LoginApp:
    def __init__(self, db_path):
        print("Initializing LoginApp...")
        self.db_path = db_path  
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.db = DatabaseManager(self.db_path)
        self.auth = AuthService(self.db)
        self.create_login_window()
        
    def create_login_window(self):
        print("Creating login window...")

        # Get screen size for adaptive window
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()

        win_width = int(screen_width * 0.34)
        win_height = int(screen_height * 0.48)

        self.login_window = ctk.CTk()
        self.login_window.geometry(f'{win_width}x{win_height}')
        self.login_window.title('Login | Project-LMS')
        self.login_window.resizable(False, False)
        self.login_window.configure(bg="#181c24")

        # Center the window
        x = (screen_width // 2) - (win_width // 2)
        y = (screen_height // 2) - (win_height // 2)
        self.login_window.geometry(f"+{x}+{y}")

        # Fade-in animation
        self.login_window.attributes('-alpha', 0.0)
        def fade_in(step=0):
            alpha = min(1.0, step / 12)
            self.login_window.attributes('-alpha', alpha)
            if alpha < 1.0:
                self.login_window.after(18, lambda: fade_in(step + 1))
        fade_in()

        # Glassy main frame with shadow
        login_frame = ctk.CTkFrame(
            self.login_window, corner_radius=22, fg_color="#23272f", border_width=2, border_color="#3a3f4b",
            width=int(win_width*0.85), height=int(win_height*0.85)
        )
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        login_frame.update()
        login_frame.place_configure(rely=1.2)  # Start off-screen

        # Slide-in animation
        def slide_in(step=0):
            target = 0.5
            start = 1.2
            pos = start - (start - target) * (step / 12)
            login_frame.place_configure(rely=pos)
            if step < 12:
                self.login_window.after(14, lambda: slide_in(step + 1))
        slide_in()

        # Logo or Icon (optional)
        logo = ctk.CTkLabel(login_frame, text="🔑", font=('Arial', int(win_height*0.13)))
        logo.pack(pady=(int(win_height*0.04), 0))

        # Title
        title_label = ctk.CTkLabel(
            login_frame, text="Welcome Back!", font=('Roboto', int(win_height * 0.09), 'bold'), text_color="#f5f6fa"
        )
        title_label.pack(pady=(int(win_height * 0.06), int(win_height * 0.01)))

        subtitle_label = ctk.CTkLabel(
            login_frame, text="Sign in to continue", font=('Roboto', int(win_height * 0.035)), text_color="#b0b3b8"
        )
        subtitle_label.pack(pady=(0, int(win_height * 0.04)))

        # Username Entry
        user_row = ctk.CTkFrame(login_frame, fg_color="transparent")
        user_row.pack(fill="x", padx=32, pady=8)
        user_icon = ctk.CTkLabel(user_row, text="👤", font=('Arial', 16), width=32)
        user_icon.pack(side="left")
        self.username_entry = ctk.CTkEntry(user_row, font=('Roboto', int(win_height * 0.035)), width=int(win_width * 0.5), placeholder_text="Username")
        self.username_entry.pack(side="left", fill="x", expand=True)

        # Password Entry with visibility toggle
        pw_row = ctk.CTkFrame(login_frame, fg_color="transparent")
        pw_row.pack(fill="x", padx=32, pady=8)
        pw_icon = ctk.CTkLabel(pw_row, text="🔒", font=('Arial', 16), width=32)
        pw_icon.pack(side="left")
        self.password_entry = ctk.CTkEntry(pw_row, show='*', font=('Roboto', int(win_height * 0.035)), width=int(win_width * 0.4), placeholder_text="Password")
        self.password_entry.pack(side="left", fill="x", expand=True)
        self.show_pw = False

        def toggle_pw():
            self.show_pw = not self.show_pw
            self.password_entry.configure(show='' if self.show_pw else '*')
            pw_eye_btn.configure(text="👁️" if not self.show_pw else "🙈")

        pw_eye_btn = ctk.CTkButton(pw_row, text="👁️", width=32, command=toggle_pw, fg_color="#444", hover_color="#666")
        self.username_entry.bind(RETURN_EVENT, lambda event: self.password_entry.focus())
        self.password_entry.bind(RETURN_EVENT, lambda event: self.login())
        self.username_entry.bind(RETURN_EVENT, lambda event: self.password_entry.focus())
        self.password_entry.bind(RETURN_EVENT, lambda event: self.login())

        # Error label (animated)
        self.error_label = ctk.CTkLabel(login_frame, text="", font=('Roboto', int(win_height * 0.025)), text_color="red")
        self.error_label.pack(pady=(5, 0))

        # Login Button
        self.login_button = ctk.CTkButton(
            login_frame, text='Login', font=('Roboto', int(win_height * 0.045), 'bold'),
            command=self.login, width=int(win_width * 0.6), height=int(win_height * 0.09), corner_radius=12,
            fg_color="#4f8cff", hover_color="#357ae8"
        )
        self.login_button.pack(pady=(int(win_height * 0.04), int(win_height * 0.01)))

        # Loading spinner (hidden by default)
        self.spinner = ctk.CTkLabel(login_frame, text="⏳", font=('Arial', int(win_height * 0.04)), text_color="#aaa")
        self.spinner.pack(pady=(0, 10))
        self.spinner.pack_forget()

        # Signup label
        signup_label = ctk.CTkLabel(
            login_frame, text="New User? Sign Up Here", font=('Arial', int(win_height * 0.025), 'underline'),
            text_color="#4f8cff", cursor="hand2"
        )
        signup_label.pack(pady=(int(win_height * 0.02), int(win_height * 0.02)))
        signup_label.bind("<Button-1>", self.signup_transition)

        # Focus on username
        self.username_entry.focus_set()
        self.login_window.bind('<Tab>', lambda e: self.password_entry.focus() if self.username_entry.focus_get() else self.username_entry.focus())
        self.login_window.bind(RETURN_EVENT, lambda e: self.login())
        self.login_window.bind('<Tab>', lambda e: self.password_entry.focus() if self.username_entry.focus_get() else self.username_entry.focus())
        self.login_window.bind(RETURN_EVENT, lambda e: self.login())

        # Set background image
        bg_path = os.path.join("assets", "background_image.jpg")
        if os.path.exists(bg_path):
            bg_img = Image.open(bg_path)
            bg_img = bg_img.resize((win_width, win_height))
            self.bg_photo = ImageTk.PhotoImage(bg_img)
            bg_label = tk.Label(self.login_window, image=self.bg_photo, borderwidth=0)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            # Raise the login frame above the background
            login_frame.lift()

        print("Entering Tkinter event loop...")
        self.login_window.mainloop()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        # Show spinner
        self.spinner.pack()
        self.login_window.update_idletasks()

        if not username or not password:
            self.error_label.configure(text="Please fill in both fields")
            self.animate_error()
            self.spinner.pack_forget()
            return

        try:
            user = self.auth.login(username, password)
        except ServiceError as e:
            self.error_label.configure(text=str(e))
            self.animate_error()
            self.spinner.pack_forget()
            return

        self.spinner.pack_forget()

        if user:
            user_dict = user
            self.user_id = user_dict['id']
            print(f"Login successful. User ID: {self.user_id}")
            self.login_window.destroy()
            ToolManagementApp(self.user_id, self.db, self.db_path)
        else:
            self.error_label.configure(text="Incorrect username or password.")
            self.animate_error()

    def animate_error(self):
        # Simple shake animation for error label
        for _ in range(2):
            self.error_label.pack_configure(padx=10)
            self.login_window.update()
            self.error_label.pack_configure(padx=0)
            self.login_window.update()

    def create_signup_window(self):
        print("Creating signup window...")
        self.signup_window = ctk.CTk()
        self.signup_window.geometry('420x600')
        self.signup_window.title('Sign Up - Project-LMS')
        self.signup_window.resizable(False, False)
        self.signup_window.configure(bg="#181c24")

        # Center the window
        self.signup_window.eval('tk::PlaceWindow %s center' % self.signup_window.winfo_toplevel())

        # Glassy main frame
        signup_frame = ctk.CTkFrame(
            self.signup_window, corner_radius=24, fg_color="#23272f", border_width=2, border_color="#3a3f4b",
            width=370, height=520
        )
        signup_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        title_label = ctk.CTkLabel(
            signup_frame, text="Create Account", font=('Roboto', 26, 'bold'), text_color="#f5f6fa"
        )
        title_label.pack(pady=(28, 2))

        subtitle_label = ctk.CTkLabel(
            signup_frame, text="Join Project-LMS today!", font=('Roboto', 14), text_color="#b0b3b8"
        )
        subtitle_label.pack(pady=(0, 18))

        # Entry fields with icons
        entry_pad = {'padx': 24, 'pady': 6}

        # Username
        user_row = ctk.CTkFrame(signup_frame, fg_color="transparent")
        user_row.pack(fill="x", **entry_pad)
        user_icon = ctk.CTkLabel(user_row, text="👤", font=('Arial', 16), width=32)
        user_icon.pack(side="left")
        self.signup_username_entry = ctk.CTkEntry(user_row, font=('Roboto', 14), width=220, placeholder_text="Username")
        self.signup_username_entry.pack(side="left", fill="x", expand=True)

        # Password
        pw_row = ctk.CTkFrame(signup_frame, fg_color="transparent")
        pw_row.pack(fill="x", **entry_pad)
        pw_icon = ctk.CTkLabel(pw_row, text="🔒", font=('Arial', 16), width=32)
        pw_icon.pack(side="left")
        self.signup_password_entry = ctk.CTkEntry(pw_row, show='*', font=('Roboto', 14), width=180, placeholder_text="Password")
        self.signup_password_entry.pack(side="left", fill="x", expand=True)
        self.signup_show_pw = False

        def toggle_signup_pw():
            self.signup_show_pw = not self.signup_show_pw
            self.signup_password_entry.configure(show='' if self.signup_show_pw else '*')
            pw_eye_btn.configure(text="👁️" if not self.signup_show_pw else "🙈")

        pw_eye_btn = ctk.CTkButton(pw_row, text="👁️", width=32, command=toggle_signup_pw, fg_color="#444", hover_color="#666")
        pw_eye_btn.pack(side="left", padx=(4, 0))

        # Confirm Password
        cpw_row = ctk.CTkFrame(signup_frame, fg_color="transparent")
        cpw_row.pack(fill="x", **entry_pad)
        cpw_icon = ctk.CTkLabel(cpw_row, text="🔒", font=('Arial', 16), width=32)
        cpw_icon.pack(side="left")
        self.confirm_password_entry = ctk.CTkEntry(cpw_row, show='*', font=('Roboto', 14), width=180, placeholder_text="Confirm Password")
        self.confirm_password_entry.pack(side="left", fill="x", expand=True)
        self.signup_show_cpw = False

        def toggle_signup_cpw():
            self.signup_show_cpw = not self.signup_show_cpw
            self.confirm_password_entry.configure(show='' if self.signup_show_cpw else '*')
            cpw_eye_btn.configure(text="👁️" if not self.signup_show_cpw else "🙈")

        cpw_eye_btn = ctk.CTkButton(cpw_row, text="👁️", width=32, command=toggle_signup_cpw, fg_color="#444", hover_color="#666")
        cpw_eye_btn.pack(side="left", padx=(4, 0))

        # Name
        name_row = ctk.CTkFrame(signup_frame, fg_color="transparent")
        name_row.pack(fill="x", **entry_pad)
        name_icon = ctk.CTkLabel(name_row, text="📝", font=('Arial', 16), width=32)
        name_icon.pack(side="left")
        self.signup_name_entry = ctk.CTkEntry(name_row, font=('Roboto', 14), width=220, placeholder_text="Full Name")
        self.signup_name_entry.pack(side="left", fill="x", expand=True)

        # Age
        age_row = ctk.CTkFrame(signup_frame, fg_color="transparent")
        age_row.pack(fill="x", **entry_pad)
        age_icon = ctk.CTkLabel(age_row, text="🎂", font=('Arial', 16), width=32)
        age_icon.pack(side="left")
        self.signup_age_entry = ctk.CTkEntry(age_row, font=('Roboto', 14), width=220, placeholder_text="Age")
        self.signup_age_entry.pack(side="left", fill="x", expand=True)

        # Email
        email_row = ctk.CTkFrame(signup_frame, fg_color="transparent")
        email_row.pack(fill="x", **entry_pad)
        email_icon = ctk.CTkLabel(email_row, text="✉️", font=('Arial', 16), width=32)
        email_icon.pack(side="left")
        self.signup_email_entry = ctk.CTkEntry(email_row, font=('Roboto', 14), width=220, placeholder_text="Email")
        self.signup_email_entry.pack(side="left", fill="x", expand=True)

        # Error label
        self.signup_error_label = ctk.CTkLabel(signup_frame, text="", font=('Roboto', 12), text_color="#ff4d4f", anchor="center")
        self.signup_error_label.pack(pady=(6, 0))

        # Sign Up Button
        self.signup_button = ctk.CTkButton(
            signup_frame, text='Sign Up', font=('Roboto', 16, 'bold'),
            command=self.register_user, width=220, height=38, corner_radius=10,
            fg_color="#4f8cff", hover_color="#357ae8"
        )
        self.signup_button.pack(pady=(18, 6))

        # Back to Login Button
        back_to_login_button = ctk.CTkButton(
            signup_frame, text="Back to Login", font=('Roboto', 14),
            command=self.back_to_login, width=220, fg_color="#23272f", hover_color="#444", text_color="#b0b3b8"
        )
        back_to_login_button.pack(pady=(0, 10))
        self.signup_username_entry.bind(RETURN_EVENT, lambda e: self.signup_password_entry.focus())
        self.signup_password_entry.bind(RETURN_EVENT, lambda e: self.confirm_password_entry.focus())
        self.confirm_password_entry.bind(RETURN_EVENT, lambda e: self.signup_name_entry.focus())
        self.signup_name_entry.bind(RETURN_EVENT, lambda e: self.signup_age_entry.focus())
        self.signup_age_entry.bind(RETURN_EVENT, lambda e: self.signup_email_entry.focus())
        self.signup_email_entry.bind(RETURN_EVENT, lambda e: self.signup_button.invoke())
        self.signup_age_entry.bind(RETURN_EVENT, lambda e: self.signup_email_entry.focus())
        self.signup_email_entry.bind(RETURN_EVENT, lambda e: self.signup_button.invoke())
        self.signup_window.bind('<Escape>', lambda e: self.back_to_login())

        self.signup_username_entry.focus_set()

        # Set background image
        bg_path = os.path.join("assets", "background_image_light.jpg")
        if os.path.exists(bg_path):
            bg_img = Image.open(bg_path)
            bg_img = bg_img.resize((420, 600))
            self.signup_bg_photo = ImageTk.PhotoImage(bg_img)
            bg_label = tk.Label(self.signup_window, image=self.signup_bg_photo, borderwidth=0)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            signup_frame.lift()

        self.signup_window.mainloop()

    def register_user(self):
        username = self.signup_username_entry.get().strip()
        password = self.signup_password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        name = self.signup_name_entry.get().strip()
        age = self.signup_age_entry.get().strip()
        email = self.signup_email_entry.get().strip()

        if not username or not password or not confirm_password or not name or not age or not email:
            self.signup_error_label.configure(text="Please fill in all fields")
            return

        try:
            self.auth.register(username, password, confirm_password, name, age, email)
            self.signup_error_label.configure(text="Signup successful!", text_color="#4CAF50")
            self.signup_window.after(800, self.back_to_login)
        except ServiceError as e:
            self.signup_error_label.configure(text=str(e), text_color="#ff4d4f")

    def back_to_login(self):
        self.signup_window.destroy()
        self.create_login_window()
            
    def signup_transition(self, event=None):
        self.login_window.destroy()
        self.create_signup_window()


class ToolManagementApp:
    def __init__(self, user_id, db, db_path):
        print(f"Received user_id type: {type(user_id)} and value: {user_id}")
        self.user_id = user_id
        self.db_path = db_path
        self.db = db
        self.tools = ToolService(db)
        print(f"ToolManagementApp initialized with user_id: {self.user_id}")
        self.create_dashboard_window()

    def create_dashboard_window(self):
        # Main Window
        self.window = ctk.CTk()
        self.window.geometry('1280x800')
        self.window.title('Project-LMS Dashboard')
        self.window.configure(bg="#181c24")

        # Sidebar
        sidebar = ctk.CTkFrame(self.window, width=250, fg_color="#23272f", corner_radius=18, border_width=2, border_color="#3a3f4b")
        sidebar.pack(side="left", fill="y", padx=18, pady=18)

        # Profile Section
        profile_image_path = "assets/user.png"
        profile_image = Image.open(profile_image_path).resize((120, 120))
        mask = Image.new("L", (120, 120), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 120, 120), fill=255)
        profile_image.putalpha(mask)
        self.profile_image_ctk = ctk.CTkImage(light_image=None, dark_image=profile_image)

        profile_label = ctk.CTkLabel(sidebar, image=self.profile_image_ctk, text="")
        profile_label.pack(pady=(30, 10))

        user_info = self.db._execute_query("SELECT name, email FROM users WHERE id = ?", (self.user_id,), fetch=True)
        user_name = user_info[0]['name'] if user_info else "User"
        user_email = user_info[0]['email'] if user_info else ""
        ctk.CTkLabel(sidebar, text=user_name, font=("Roboto", 18, "bold"), text_color="#f5f6fa").pack()
        ctk.CTkLabel(sidebar, text=user_email, font=("Roboto", 12), text_color="#b0b3b8").pack(pady=(0, 18))

        # Sidebar Buttons with icons
        btn_style = {
            "font": ("Roboto", 15),
            "fg_color": "#23272f",
            "hover_color": "#4f8cff",
            "text_color": "#f5f6fa",
            "corner_radius": 10,
            "height": 38
        }
        self.borrow_button = ctk.CTkButton(sidebar, text="🔄  Borrow Tool", command=self.borrow_tool, **btn_style)
        self.borrow_button.pack(pady=6, padx=20, fill="x")
        self.add_tool_button = ctk.CTkButton(sidebar, text="➕  Add Tool", command=self.add_tool, **btn_style)
        self.add_tool_button.pack(pady=6, padx=20, fill="x")
        self.view_tools_button = ctk.CTkButton(sidebar, text="📋  View Tools", command=self.view_tools, **btn_style)
        self.view_tools_button.pack(pady=6, padx=20, fill="x")
        self.delete_tool_button = ctk.CTkButton(sidebar, text="🗑️  Delete Tool", command=self.delete_tool, **btn_style)
        self.delete_tool_button.pack(pady=6, padx=20, fill="x")
        self.return_tool_button = ctk.CTkButton(sidebar, text="↩️  Return Tool", command=self.return_tool, **btn_style)
        self.return_tool_button.pack(pady=6, padx=20, fill="x")
        self.logout_button = ctk.CTkButton(sidebar, text="🚪  Logout", fg_color="#d9534f", hover_color="#b52a1d", command=self.logout, font=("Roboto", 15, "bold"), corner_radius=10, height=38)
        self.logout_button.pack(side="bottom", pady=20, padx=20, fill="x")

        # Main Dashboard Area
        dashboard_frame = ctk.CTkFrame(self.window, fg_color="#23272f", corner_radius=18, border_width=2, border_color="#3a3f4b")
        dashboard_frame.pack(side="right", fill="both", expand=True, padx=18, pady=18)

        # Dashboard Stats
        self.show_dashboard_stats(dashboard_frame)

        # Inventory Table Section
        inventory_label = ctk.CTkLabel(dashboard_frame, text="Inventory Overview", font=("Roboto", 22, "bold"), text_color="#f5f6fa")
        inventory_label.pack(pady=(18, 8))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#23272f", fieldbackground="#23272f", foreground="#f5f6fa", rowheight=32, font=("Roboto", 13))
        style.configure("Treeview.Heading", background="#3a3f4b", foreground="#4f8cff", font=("Roboto", 14, "bold"))
        style.map("Treeview", background=[("selected", "#4f8cff")])

        self.inventory_table = ttk.Treeview(
            dashboard_frame,
            columns=("ID", "Name", "Category", "Condition", "Quantity", "Status"),
            show="headings",
            selectmode="browse"
        )
        self.inventory_table.pack(pady=10, padx=20, fill="both", expand=True)

        for col in self.inventory_table["columns"]:
            self.inventory_table.heading(col, text=col, command=lambda col=col: self.sort_inventory(col))
            self.inventory_table.column(col, width=140, anchor="center")

        self.update_inventory_table()

        # Pie Chart Section
        pie_chart_label = ctk.CTkLabel(dashboard_frame, text="Tool Categories Distribution", font=("Roboto", 20, "bold"), text_color="#f5f6fa")
        pie_chart_label.pack(pady=(18, 8))

        self.pie_chart_canvas = ctk.CTkFrame(dashboard_frame, fg_color="#23272f", corner_radius=18)
        self.pie_chart_canvas.pack(pady=10, padx=20, fill="both", expand=True)

        self.update_pie_chart()
        self.window.mainloop()

    def show_dashboard_stats(self, parent):
        # Fetch stats
        tools = self.db.fetch_all_tools()
        total_tools = len(tools)
        borrowed = sum(1 for t in tools if t['status'] == 'borrowed')
        available = sum(1 for t in tools if t['status'] == 'available')
        categories = {t['category'] for t in tools}
        stats_frame = ctk.CTkFrame(parent, fg_color="#23272f", corner_radius=14)
        stats_frame.pack(pady=(18, 8), padx=20, fill="x")

        stat_style = {"font": ("Roboto", 16, "bold"), "text_color": "#4f8cff"}
        ctk.CTkLabel(stats_frame, text=f"Total Tools: {total_tools}", **stat_style).pack(side="left", padx=24)
        ctk.CTkLabel(stats_frame, text=f"Borrowed: {borrowed}", **stat_style).pack(side="left", padx=24)
        ctk.CTkLabel(stats_frame, text=f"Available: {available}", **stat_style).pack(side="left", padx=24)
        ctk.CTkLabel(stats_frame, text=f"Categories: {len(categories)}", **stat_style).pack(side="left", padx=24)

    def update_inventory_table(self):
        # Clear existing data
        for row in self.inventory_table.get_children():
            self.inventory_table.delete(row)

        # Fetch and insert new data
        tools = self.db.fetch_all_tools()
        for idx, tool in enumerate(tools):
            borrowed_status = "Borrowed" if tool['status'] == 'borrowed' else "Available"
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.inventory_table.insert(
                "", "end",
                values=(
                    tool['tool_id'],
                    tool['name'],
                    tool['category'],
                    tool['condition'],
                    tool['quantity'],
                    borrowed_status
                ),
                tags=(tag,)
            )
        # Alternate row colors
        self.inventory_table.tag_configure("evenrow", background="#23272f")
        self.inventory_table.tag_configure("oddrow", background="#262b34")

    def update_pie_chart(self):
        if not (hasattr(self, 'pie_chart_canvas') and self.pie_chart_canvas):
            return
        for widget in self.pie_chart_canvas.winfo_children():
            widget.destroy()

        tools = self.db.fetch_all_tools()
        categories = self._get_category_counts(tools)

        if not categories:
            label = ctk.CTkLabel(self.pie_chart_canvas, text="No data to display.", font=("Roboto", 16), text_color="#f5f6fa")
            label.pack(expand=True)
            return

        colors = self._get_color_palette(len(categories))
        fig, ax, wedges = self._draw_pie_chart(categories, colors)

        fig.canvas.mpl_connect('button_press_event', lambda event: self._on_pie_click(event, wedges, categories))
        fig.canvas.mpl_connect('motion_notify_event', lambda event: self._on_pie_hover(event, wedges, categories, ax, fig))

        self._draw_pie_legend(ax, wedges, categories)
        ax.axis('equal')
        fig.tight_layout()

        chart_canvas = FigureCanvasTkAgg(fig, self.pie_chart_canvas)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _get_category_counts(self, tools):
        categories = {}
        for tool in tools:
            category = tool['category']
            categories[category] = categories.get(category, 0) + 1
        return categories

    def _get_color_palette(self, n):
        color_palette = [
            "#4f8cff", "#00c9a7", "#ffb347", "#ff5e57", "#a259ff", "#43e97b", "#f67280", "#36cfc9", "#f9d423"
        ]
        return [color_palette[i % len(color_palette)] for i in range(n)]

    def _draw_pie_chart(self, categories, colors):
        fig = Figure(figsize=(5.5, 3.5), dpi=100, facecolor="#23272f")
        ax = fig.add_subplot(111)
        wedges, _, _ = ax.pie(
            categories.values(),
            labels=None,
            autopct='%1.1f%%',
            startangle=140,
            pctdistance=0.8,
            colors=colors,
            textprops={'color': "#f5f6fa", 'fontsize': 13, 'fontweight': 'bold'},
            wedgeprops={'edgecolor': '#181c24', 'linewidth': 2, 'antialiased': True}
        )
        centre_circle = plt.Circle((0, 0), 0.65, fc='#181c24', zorder=10)
        ax.add_artist(centre_circle)
        return fig, ax, wedges

    def _on_pie_click(self, event, wedges, categories):
        for i, wedge in enumerate(wedges):
            if wedge.contains_point([event.x, event.y]):
                category = list(categories.keys())[i]
                filtered = [t for t in self.db.fetch_all_tools() if t['category'] == category]
                self.update_tools_list(filtered)
                break

    def _on_pie_hover(self, event, wedges, categories, ax, fig):
        for i, wedge in enumerate(wedges):
            if wedge.contains_point([event.x, event.y]):
                ax.set_title(f"{list(categories.keys())[i]}: {list(categories.values())[i]} tools", color="#4f8cff", fontsize=15)
                fig.canvas.draw_idle()
                return
        ax.set_title("")
        fig.canvas.draw_idle()

    def _draw_pie_legend(self, ax, wedges, categories):
        ax.legend(
            wedges, categories.keys(),
            title="Categories",
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=12,
            title_fontsize=13,
            labelcolor="#f5f6fa",
            frameon=False
        )

    def borrow_tool(self):
        try:
            available_tools = self.tools.available_tools()
            if not available_tools:
                messagebox.showwarning("No Tools Available", "There are no tools available to borrow.")
                return

            tool_names = [tool['name'] for tool in available_tools]

            borrow_tool_window = ctk.CTkToplevel(self.window)
            borrow_tool_window.geometry("420x340")
            borrow_tool_window.title("Borrow Tool")
            borrow_tool_window.attributes('-topmost', True)
            borrow_tool_window.configure(bg="#181c24")

            borrow_tool_frame = ctk.CTkFrame(
                borrow_tool_window, corner_radius=18, fg_color="#23272f", border_width=2, border_color="#3a3f4b"
            )
            borrow_tool_frame.pack(pady=24, padx=24, fill='both', expand=True)

            title = ctk.CTkLabel(borrow_tool_frame, text="Borrow Tool", font=('Roboto', 20, 'bold'), text_color="#4f8cff")
            title.pack(pady=(10, 18))

            # Tool Dropdown
            tool_row = ctk.CTkFrame(borrow_tool_frame, fg_color="transparent")
            tool_row.pack(fill="x", pady=6)
            tool_icon = ctk.CTkLabel(tool_row, text="🛠️", font=('Arial', 16), width=32)
            tool_icon.pack(side="left")
            tool_var = StringVar(borrow_tool_frame)
            tool_var.set(tool_names[0])
            tool_dropdown = ctk.CTkOptionMenu(tool_row, variable=tool_var, values=tool_names)
            tool_dropdown.pack(side="left", fill="x", expand=True)

            # Borrower's Name
            borrower_row = ctk.CTkFrame(borrow_tool_frame, fg_color="transparent")
            borrower_row.pack(fill="x", pady=6)
            borrower_icon = ctk.CTkLabel(borrower_row, text="👤", font=('Arial', 16), width=32)
            borrower_icon.pack(side="left")
            borrower_entry = ctk.CTkEntry(borrower_row, font=('Roboto', 14), width=220, placeholder_text="Borrower's Name")
            borrower_entry.pack(side="left", fill="x", expand=True)

            # Borrow Date
            date_row = ctk.CTkFrame(borrow_tool_frame, fg_color="transparent")
            date_row.pack(fill="x", pady=6)
            date_icon = ctk.CTkLabel(date_row, text="📅", font=('Arial', 16), width=32)
            date_icon.pack(side="left")
            date_entry = ctk.CTkEntry(date_row, font=('Roboto', 14), width=220, placeholder_text="Borrow Date (YYYY-MM-DD)")
            date_entry.pack(side="left", fill="x", expand=True)

            # Error label
            error_label = ctk.CTkLabel(borrow_tool_frame, text="", font=('Roboto', 12), text_color="#ff4d4f")
            error_label.pack(pady=(4, 0))

            def borrow_selected_tool():
                selected_tool_name = tool_var.get()
                borrower_name = borrower_entry.get().strip()
                borrow_date = date_entry.get().strip()

                if not borrower_name or not borrow_date:
                    error_label.configure(text="Please fill in all fields.")
                    return

                try:
                    datetime.datetime.strptime(borrow_date, "%Y-%m-%d").date()
                except ValueError:
                    error_label.configure(text="Invalid date format. Use YYYY-MM-DD.")
                    return

                tool_id = next((tool['tool_id'] for tool in available_tools if tool['name'] == selected_tool_name), None)
                if tool_id is None:
                    error_label.configure(text="Selected tool not found.")
                    return

                user_id = self.user_id

                if tool_id:
                    try:
                        self.tools.borrow_tool(tool_id, self.user_id, borrow_date)
                        messagebox.showinfo("Success", f"'{selected_tool_name}' borrowed.")
                        borrow_tool_window.destroy()
                        self.update_inventory_table()
                        self.update_pie_chart()
                    except ServiceError as e:
                        error_label.configure(text=str(e))
                    except Exception as e:
                        error_label.configure(text=f"Failed to borrow tool: {e}")

            # Buttons
            btn_row = ctk.CTkFrame(borrow_tool_frame, fg_color="transparent")
            btn_row.pack(pady=(18, 0))
            borrow_button = ctk.CTkButton(btn_row, text="Borrow", command=borrow_selected_tool, width=120, fg_color="#4f8cff", hover_color="#357ae8")
            borrow_button.pack(side="left", padx=8)
            close_button = ctk.CTkButton(btn_row, text="Close", command=borrow_tool_window.destroy, width=120, fg_color="#23272f", hover_color="#444")
            close_button.pack(side="left", padx=8)
            borrower_entry.bind(RETURN_EVENT, lambda event: date_entry.focus_set())
            date_entry.bind(RETURN_EVENT, lambda event: borrow_button.invoke())
            borrower_entry.bind(RETURN_EVENT, lambda event: date_entry.focus_set())
            date_entry.bind(RETURN_EVENT, lambda event: borrow_button.invoke())

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def delete_tool(self):
        selected_item = self.inventory_table.selection()
        if not selected_item:
            messagebox.showwarning("No Tool Selected", "Please select a tool to delete.")
            return

        selected_tool = self.inventory_table.item(selected_item, 'values')
        tool_id = selected_tool[0]

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the tool '{selected_tool[1]}'?")
        if confirm:
            try:
                self.tools.delete_tool(tool_id, actor=self.user_id)
                messagebox.showinfo("Tool Deleted", f"'{selected_tool[1]}' has been deleted from the inventory.")
                self.update_inventory_table()
                self.update_pie_chart()
            except ServiceError as e:
                messagebox.showerror("Access Denied", str(e))
            
    def get_tool_columns(self):
        # Fetch column names from the database schema
        columns_info = self.db._execute_query("PRAGMA table_info(tools)", fetch=True)
        # Exclude internal columns if needed
        columns = [col['name'] for col in columns_info if col['name'] != 'tool_id']
        # Always show tool_id first
        return ['tool_id'] + columns

    def view_tools(self):
        self.current_page = 1
        self.page_size = 20
        try:
            view_window = ctk.CTkToplevel(self.window)
            view_window.title(VIEW_TOOLS_TITLE)
            view_window.geometry("900x520")
            view_window.attributes("-topmost", True)
            view_window.configure(bg="#181c24")

            view_frame = ctk.CTkFrame(view_window, corner_radius=18, fg_color="#23272f", border_width=2, border_color="#3a3f4b")
            view_frame.pack(pady=18, padx=18, fill="both", expand=True)  
            title_label = ctk.CTkLabel(view_frame, text=VIEW_TOOLS_TITLE, font=("Roboto", 20, "bold"), text_color="#4f8cff")
            title_label.pack(pady=10)

            # Dynamic columns
            columns = self.get_tool_columns()
            self.tools_listbox = ttk.Treeview(view_frame, columns=columns, show="headings")
            self.tools_listbox.pack(pady=10, padx=20, fill="both", expand=True)

            for col in columns:
                self.tools_listbox.heading(col, text=col.title(), command=lambda c=col: self.sort_tools_list(c))
                self.tools_listbox.column(col, width=120, anchor="center")

            # Pagination buttons
            next_btn = ctk.CTkButton(view_frame, text="Next", command=self.next_page)
            prev_btn = ctk.CTkButton(view_frame, text="Previous", command=self.prev_page)
            prev_btn.pack(side="left", padx=10)
            next_btn.pack(side="left", padx=10)

            self.update_tools_list(self.db.fetch_tools_paginated(self.current_page, self.page_size))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while viewing tools: {e}")

    def update_tools_list(self, tools=None):
        columns = self.get_tool_columns()
        self._clear_tools_listbox()
        if tools is None:
            tools = self.db.fetch_all_tools()
        for tool in tools:
            self.tools_listbox.insert("", "end", values=[tool.get(col, "") for col in columns])
        self._set_tooltips(tools)

    def _clear_tools_listbox(self):
        for item in self.tools_listbox.get_children():
            self.tools_listbox.delete(item)

    def _set_tooltips(self, tools):
        self._tooltips = {}
        for iid, tool in zip(self.tools_listbox.get_children(), tools):
            details = "\n".join(f"{col.title()}: {tool.get(col, '')}" for col in self.get_tool_columns())
            self._tooltips[iid] = details
        self._adv_tooltip = AdvancedToolTip(self.tools_listbox)
        self.tools_listbox.bind("<Motion>", self._on_tools_listbox_motion)
        self.tools_listbox.bind("<Leave>", lambda e: self._adv_tooltip.hide())

    def _on_tools_listbox_motion(self, event):
        region = self.tools_listbox.identify("region", event.x, event.y)
        row_id = self.tools_listbox.identify_row(event.y)
        if region == "cell" and row_id and row_id in self._tooltips:
            x = self.tools_listbox.winfo_rootx() + event.x + 20
            y = self.tools_listbox.winfo_rooty() + event.y + 10
            if getattr(self, "_active_tooltip_row", None) != row_id:
                self._adv_tooltip.show(self._tooltips[row_id], x, y)
                self._active_tooltip_row = row_id
        else:
            self._adv_tooltip.hide()
            self._active_tooltip_row = None

    def next_page(self):
        total = self.db.count_tools()
        if self.current_page * self.page_size < total:
            self.current_page += 1
            self.update_tools_list(self.db.fetch_tools_paginated(self.current_page, self.page_size))

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_tools_list(self.db.fetch_tools_paginated(self.current_page, self.page_size))

    def return_tool(self):
        try:
            # Fetch only tools this user actually borrowed (ownership-scoped).
            borrowed_tools = self.tools.my_borrowed_tools(self.user_id)
            print(f"Borrowed tools: {borrowed_tools}")

            if not borrowed_tools:
                messagebox.showwarning("No Borrowed Tools", "There are no borrowed tools to return.")
                return

            tool_names = [tool['name'] for tool in borrowed_tools]
            tool_name = simpledialog.askstring(
                "Return Tool",
                f"Borrowed tools: \n{', '.join(tool_names)}\n\nEnter the tool name you want to return:"
            )

            if tool_name and tool_name in tool_names:
                tool_id = borrowed_tools[tool_names.index(tool_name)]['tool_id']
                try:
                    # Ownership is verified inside ToolService.return_tool().
                    self.tools.return_tool(tool_id, self.user_id)
                    messagebox.showinfo("Tool Returned", f"'{tool_name}' has been returned.")
                    self.update_inventory_table()
                    self.update_pie_chart()
                except ServiceError as e:
                    messagebox.showerror("Return Failed", str(e))
            else:
                messagebox.showerror("Invalid Tool", "The selected tool is not valid for return.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while returning the tool: {e}")

    def search_tool(self):
        tool_name = simpledialog.askstring("Search Tool", "Enter the name of the tool you want to search:")

        if tool_name:
            tools = self.db.search_tool(tool_name)
            if tools:
                tool_list = '\n'.join([f"{tool[1]}: {tool[2]}" for tool in tools])
                messagebox.showinfo("Search Results", f"Found tools: \n{tool_list}")
            else:
                messagebox.showinfo("Search Results", "No tools found.")
                
    def add_tool(self):
        add_tool_window = ctk.CTkToplevel(self.window)
        add_tool_window.geometry("420x420")
        add_tool_window.title("Add New Tool")
        add_tool_window.attributes('-topmost', True)
        add_tool_window.configure(bg="#181c24")

        # Glassy frame
        add_tool_frame = ctk.CTkFrame(
            add_tool_window, corner_radius=18, fg_color="#23272f", border_width=2, border_color="#3a3f4b"
        )
        add_tool_frame.pack(pady=24, padx=24, fill='both', expand=True)

        title = ctk.CTkLabel(add_tool_frame, text="Add New Tool", font=('Roboto', 20, 'bold'), text_color="#4f8cff")
        title.pack(pady=(10, 18))

        entry_pad = {'padx': 12, 'pady': 6}

        # Tool Name
        name_row = ctk.CTkFrame(add_tool_frame, fg_color="transparent")
        name_row.pack(fill="x", **entry_pad)
        name_icon = ctk.CTkLabel(name_row, text=" ", font=('Arial', 16), width=32)
        name_icon.pack(side="left")
        name_entry = ctk.CTkEntry(name_row, font=('Roboto', 14), width=220, placeholder_text="Tool Name")
        name_entry.pack(side="left", fill="x", expand=True)

        # Category
        cat_row = ctk.CTkFrame(add_tool_frame, fg_color="transparent")
        cat_row.pack(fill="x", **entry_pad)
        cat_icon = ctk.CTkLabel(cat_row, text=" ", font=('Arial', 16), width=32)
        cat_icon.pack(side="left")
        category_entry = ctk.CTkEntry(cat_row, font=('Roboto', 14), width=220, placeholder_text="Category")
        category_entry.pack(side="left", fill="x", expand=True)

        # Condition
        cond_row = ctk.CTkFrame(add_tool_frame, fg_color="transparent")
        cond_row.pack(fill="x", **entry_pad)
        cond_icon = ctk.CTkLabel(cond_row, text=" ", font=('Arial', 16), width=32)
        cond_icon.pack(side="left")
        condition_entry = ctk.CTkEntry(cond_row, font=('Roboto', 14), width=220, placeholder_text="Condition")
        condition_entry.pack(side="left", fill="x", expand=True)

        # Quantity
        qty_row = ctk.CTkFrame(add_tool_frame, fg_color="transparent")
        qty_row.pack(fill="x", **entry_pad)
        qty_icon = ctk.CTkLabel(qty_row, text=" ", font=('Arial', 16), width=32)
        qty_icon.pack(side="left")
        quantity_entry = ctk.CTkEntry(qty_row, font=('Roboto', 14), width=220, placeholder_text="Quantity")
        quantity_entry.pack(side="left", fill="x", expand=True)

        # Location
        loc_row = ctk.CTkFrame(add_tool_frame, fg_color="transparent")
        loc_row.pack(fill="x", **entry_pad)
        loc_icon = ctk.CTkLabel(loc_row, text=" ", font=('Arial', 16), width=32)
        loc_icon.pack(side="left")
        location_entry = ctk.CTkEntry(loc_row, font=('Roboto', 14), width=220, placeholder_text="Location")
        location_entry.pack(side="left", fill="x", expand=True)

        # Error label
        error_label = ctk.CTkLabel(add_tool_frame, text="", font=('Roboto', 12), text_color="#ff4d4f")
        error_label.pack(pady=(4, 0))

        def save_tool():
            tool_name = name_entry.get().strip()
            tool_category = category_entry.get().strip()
            tool_condition = condition_entry.get().strip()
            tool_quantity = quantity_entry.get().strip()
            tool_location = location_entry.get().strip()

            if not tool_name or not tool_category or not tool_condition or not tool_quantity or not tool_location:
                error_label.configure(text="Please fill in all fields.")
                return

            try:
                self.tools.add_tool(
                    tool_name, tool_category, tool_condition, tool_quantity, tool_location, actor=self.user_id
                )
                # Remove always-on-top so messagebox appears above
                add_tool_window.attributes('-topmost', False)
                self.window.lift()  # Bring main window to front (optional)
                messagebox.showinfo("Success", f"{tool_name} added successfully.", parent=add_tool_window)
                add_tool_window.destroy()
                self.update_inventory_table()
                self.update_pie_chart()
            except ServiceError as e:
                error_label.configure(text=str(e))
            except Exception as e:
                error_label.configure(text=f"Failed to add tool: {e}")

        # Buttons
        btn_row = ctk.CTkFrame(add_tool_frame, fg_color="transparent")
        btn_row.pack(pady=(18, 0))
        save_button = ctk.CTkButton(btn_row, text="Save", command=save_tool, width=120, fg_color="#4f8cff", hover_color="#357ae8")
        save_button.pack(side="left", padx=8)
        close_button = ctk.CTkButton(btn_row, text="Close", command=add_tool_window.destroy, width=120, fg_color="#23272f", hover_color="#444")
        close_button.pack(side="left", padx=8)
        name_entry.bind(RETURN_EVENT, lambda event: category_entry.focus_set())
        category_entry.bind(RETURN_EVENT, lambda event: condition_entry.focus_set())
        condition_entry.bind(RETURN_EVENT, lambda event: quantity_entry.focus_set())
        quantity_entry.bind(RETURN_EVENT, lambda event: location_entry.focus_set())
        location_entry.bind(RETURN_EVENT, lambda event: save_button.invoke())
        quantity_entry.bind(RETURN_EVENT, lambda event: location_entry.focus_set())
        location_entry.bind(RETURN_EVENT, lambda event: save_button.invoke())

    def logout(self):
        self.window.destroy()
        LoginApp(self.db_path)


if __name__ == '__main__':
    db_path = './db/inventory.db'
    LoginApp(db_path)



