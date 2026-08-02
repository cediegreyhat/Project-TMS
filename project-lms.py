"""
Project-LMS Modern Desktop Application
======================================

A sleek, responsive customtkinter GUI for the Learner's Tool Management System.

Features:
- Glassmorphic login/signup windows with background image support
- Modern single-window dashboard with tabbed/inline view switching
- Reusable asset integration (user profile avatar + dark/light background wallpapers)
- Stat cards (Total Tools, Borrowed, Available, Categories)
- Modern Treeview theme matching customtkinter dark theme
- Interactive category breakdown donut chart (matplotlib)
- Integrated search bar + status/category filters
- Complete service layer delegation (AuthService + ToolService)
- Clean, non-blocking dialogs for borrow/return/add/delete
"""

import datetime
import os
import tkinter as tk
from tkinter import StringVar, messagebox, simpledialog, ttk

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageDraw, ImageTk

from database import DatabaseManager
from service import AuthService, ServiceError, ToolService

RETURN_EVENT = "<Return>"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Theme Palette (Deep Navy / Glassmorphic)
COLOR_BG_DARK = "#12161f"
COLOR_CARD = "#1c212d"
COLOR_CARD_BORDER = "#2e3545"
COLOR_ACCENT = "#4f8cff"
COLOR_ACCENT_HOVER = "#3b73e0"
COLOR_TEXT_PRIMARY = "#f5f6fa"
COLOR_TEXT_MUTED = "#a0a5b5"
COLOR_DANGER = "#e05655"
COLOR_DANGER_HOVER = "#c0392b"
COLOR_SUCCESS = "#2ecc71"


class AdvancedToolTip:
    """Hover tooltip for treeview rows."""

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None

    def show(self, text, x, y):
        self.hide()
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=text,
            background="#23272f",
            foreground=COLOR_ACCENT,
            relief="solid",
            borderwidth=1,
            font=("Roboto", 10),
            justify="left",
            anchor="w",
        )
        label.pack(ipadx=8, ipady=4)

    def hide(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class LoginApp:
    """Modern Glassmorphic Login & Registration Flow."""

    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.db = DatabaseManager(self.db_path)
        self.auth = AuthService(self.db)
        self.create_login_window()

    def create_login_window(self):
        root = tk.Tk()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()

        ww, wh = int(sw * 0.32), int(sh * 0.52)
        ww, wh = max(420, ww), max(520, wh)

        self.login_window = ctk.CTk()
        self.login_window.geometry(f"{ww}x{wh}")
        self.login_window.title("Login | Project-LMS")
        self.login_window.resizable(False, False)
        self.login_window.configure(bg=COLOR_BG_DARK)

        # Center window
        x, y = (sw // 2) - (ww // 2), (sh // 2) - (wh // 2)
        self.login_window.geometry(f"+{x}+{y}")

        # Set background wallpaper if present
        bg_path = os.path.join("assets", "background_image.jpg")
        if os.path.exists(bg_path):
            try:
                bg_img = Image.open(bg_path).resize((ww, wh), Image.Resampling.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(bg_img)
                bg_label = tk.Label(self.login_window, image=self.bg_photo, borderwidth=0)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        # Glassy Login Frame
        login_frame = ctk.CTkFrame(
            self.login_window,
            corner_radius=20,
            fg_color=COLOR_CARD,
            border_width=2,
            border_color=COLOR_CARD_BORDER,
            width=int(ww * 0.88),
            height=int(wh * 0.88),
        )
        login_frame.place(relx=0.5, rely=0.5, anchor="center")

        logo = ctk.CTkLabel(login_frame, text="🛠️", font=("Arial", 42))
        logo.pack(pady=(28, 2))

        title = ctk.CTkLabel(
            login_frame, text="Welcome Back", font=("Roboto", 24, "bold"), text_color=COLOR_TEXT_PRIMARY
        )
        title.pack(pady=(2, 2))

        sub = ctk.CTkLabel(
            login_frame, text="Sign in to continue to Project-LMS", font=("Roboto", 13), text_color=COLOR_TEXT_MUTED
        )
        sub.pack(pady=(0, 20))

        # Username Field
        user_row = ctk.CTkFrame(login_frame, fg_color="transparent")
        user_row.pack(fill="x", padx=32, pady=6)
        ctk.CTkLabel(user_row, text="👤", font=("Arial", 16), width=32).pack(side="left")
        self.username_entry = ctk.CTkEntry(
            user_row, font=("Roboto", 14), placeholder_text="Username"
        )
        self.username_entry.pack(side="left", fill="x", expand=True)

        # Password Field
        pw_row = ctk.CTkFrame(login_frame, fg_color="transparent")
        pw_row.pack(fill="x", padx=32, pady=6)
        ctk.CTkLabel(pw_row, text="🔒", font=("Arial", 16), width=32).pack(side="left")
        self.password_entry = ctk.CTkEntry(
            pw_row, show="*", font=("Roboto", 14), placeholder_text="Password"
        )
        self.password_entry.pack(side="left", fill="x", expand=True)

        self.show_pw = False

        def toggle_pw():
            self.show_pw = not self.show_pw
            self.password_entry.configure(show="" if self.show_pw else "*")
            pw_btn.configure(text="🙈" if self.show_pw else "👁️")

        pw_btn = ctk.CTkButton(
            pw_row, text="👁️", width=32, command=toggle_pw, fg_color="#333", hover_color="#555"
        )
        pw_btn.pack(side="left", padx=(4, 0))

        self.error_label = ctk.CTkLabel(
            login_frame, text="", font=("Roboto", 12), text_color=COLOR_DANGER
        )
        self.error_label.pack(pady=(6, 0))

        # Login Button
        self.login_btn = ctk.CTkButton(
            login_frame,
            text="Sign In",
            font=("Roboto", 15, "bold"),
            command=self.login,
            width=220,
            height=40,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        )
        self.login_btn.pack(pady=(16, 8))

        signup_link = ctk.CTkLabel(
            login_frame,
            text="New User? Create an Account",
            font=("Roboto", 12, "underline"),
            text_color=COLOR_ACCENT,
            cursor="hand2",
        )
        signup_link.pack(pady=(6, 16))
        signup_link.bind("<Button-1>", self.signup_transition)

        self.username_entry.focus_set()
        self.username_entry.bind(RETURN_EVENT, lambda e: self.password_entry.focus())
        self.password_entry.bind(RETURN_EVENT, lambda e: self.login())
        self.login_window.mainloop()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Please enter both username and password")
            return

        try:
            user = self.auth.login(username, password)
            self.user_id = user["id"]
            self.login_window.destroy()
            ToolManagementApp(self.user_id, self.db, self.db_path)
        except ServiceError as e:
            self.error_label.configure(text=str(e))

    def create_signup_window(self):
        self.signup_window = ctk.CTk()
        self.signup_window.geometry("440x620")
        self.signup_window.title("Sign Up | Project-LMS")
        self.signup_window.resizable(False, False)
        self.signup_window.configure(bg=COLOR_BG_DARK)

        bg_path = os.path.join("assets", "background_image_light.jpg")
        if os.path.exists(bg_path):
            try:
                bg_img = Image.open(bg_path).resize((440, 620), Image.Resampling.LANCZOS)
                self.signup_bg_photo = ImageTk.PhotoImage(bg_img)
                bg_label = tk.Label(self.signup_window, image=self.signup_bg_photo, borderwidth=0)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        signup_frame = ctk.CTkFrame(
            self.signup_window,
            corner_radius=20,
            fg_color=COLOR_CARD,
            border_width=2,
            border_color=COLOR_CARD_BORDER,
            width=380,
            height=540,
        )
        signup_frame.place(relx=0.5, rely=0.5, anchor="center")

        title = ctk.CTkLabel(
            signup_frame, text="Create Account", font=("Roboto", 24, "bold"), text_color=COLOR_TEXT_PRIMARY
        )
        title.pack(pady=(24, 2))

        sub = ctk.CTkLabel(
            signup_frame, text="Join Project-LMS today", font=("Roboto", 13), text_color=COLOR_TEXT_MUTED
        )
        sub.pack(pady=(0, 16))

        pad = {"padx": 24, "pady": 4}

        self.signup_username = ctk.CTkEntry(signup_frame, font=("Roboto", 13), placeholder_text="Username")
        self.signup_username.pack(fill="x", **pad)

        self.signup_pw = ctk.CTkEntry(signup_frame, show="*", font=("Roboto", 13), placeholder_text="Password")
        self.signup_pw.pack(fill="x", **pad)

        self.signup_cpw = ctk.CTkEntry(signup_frame, show="*", font=("Roboto", 13), placeholder_text="Confirm Password")
        self.signup_cpw.pack(fill="x", **pad)

        self.signup_name = ctk.CTkEntry(signup_frame, font=("Roboto", 13), placeholder_text="Full Name")
        self.signup_name.pack(fill="x", **pad)

        self.signup_age = ctk.CTkEntry(signup_frame, font=("Roboto", 13), placeholder_text="Age")
        self.signup_age.pack(fill="x", **pad)

        self.signup_email = ctk.CTkEntry(signup_frame, font=("Roboto", 13), placeholder_text="Email Address")
        self.signup_email.pack(fill="x", **pad)

        self.signup_error = ctk.CTkLabel(
            signup_frame, text="", font=("Roboto", 12), text_color=COLOR_DANGER
        )
        self.signup_error.pack(pady=(6, 0))

        signup_btn = ctk.CTkButton(
            signup_frame,
            text="Register",
            font=("Roboto", 15, "bold"),
            command=self.register_user,
            width=220,
            height=38,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        )
        signup_btn.pack(pady=(12, 6))

        back_btn = ctk.CTkButton(
            signup_frame,
            text="Back to Login",
            font=("Roboto", 13),
            command=self.back_to_login,
            width=220,
            fg_color="transparent",
            hover_color="#333",
            text_color=COLOR_TEXT_MUTED,
        )
        back_btn.pack(pady=(0, 16))

        self.signup_username.focus_set()
        self.signup_window.mainloop()

    def register_user(self):
        u = self.signup_username.get().strip()
        p = self.signup_pw.get()
        cp = self.signup_cpw.get()
        n = self.signup_name.get().strip()
        a = self.signup_age.get().strip()
        e = self.signup_email.get().strip()

        try:
            self.auth.register(u, p, cp, n, a, e)
            self.signup_error.configure(text="Signup successful! Returning to login...", text_color=COLOR_SUCCESS)
            self.signup_window.after(1000, self.back_to_login)
        except ServiceError as err:
            self.signup_error.configure(text=str(err), text_color=COLOR_DANGER)

    def back_to_login(self):
        self.signup_window.destroy()
        self.create_login_window()

    def signup_transition(self, event=None):
        self.login_window.destroy()
        self.create_signup_window()


class ToolManagementApp:
    """Remodeled Single-Window Dashboard Application."""

    def __init__(self, user_id, db, db_path):
        self.user_id = user_id
        self.db = db
        self.db_path = db_path
        self.tools = ToolService(db)
        self.create_dashboard_window()

    def create_dashboard_window(self):
        self.window = ctk.CTk()
        self.window.geometry("1280x820")
        self.window.title("Project-LMS | Modern Dashboard")
        self.window.configure(bg=COLOR_BG_DARK)

        # Main Layout: Left Sidebar + Right Workspace
        self.sidebar = ctk.CTkFrame(
            self.window, width=260, fg_color=COLOR_CARD, corner_radius=0, border_width=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._build_sidebar()

        self.workspace = ctk.CTkFrame(
            self.window, fg_color=COLOR_BG_DARK, corner_radius=0
        )
        self.workspace.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # Build workspace sections
        self._build_stats_section()
        self._build_controls_section()
        self._build_table_section()
        self._build_chart_section()

        self.refresh_dashboard()
        self.window.mainloop()

    def _build_sidebar(self):
        # User Avatar Profile
        user_info = self.db._execute_query(
            "SELECT name, email, is_admin FROM users WHERE id = ?", (self.user_id,), fetch=True
        )
        name = user_info[0]["name"] if user_info else "User"
        email = user_info[0]["email"] if user_info else ""
        is_admin = bool(user_info[0].get("is_admin")) if user_info else False

        profile_img_path = os.path.join("assets", "user.png")
        if os.path.exists(profile_img_path):
            try:
                raw_img = Image.open(profile_img_path).resize((100, 100), Image.Resampling.LANCZOS)
                mask = Image.new("L", (100, 100), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 100, 100), fill=255)
                raw_img.putalpha(mask)
                self.avatar_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(100, 100))
                avatar_lbl = ctk.CTkLabel(self.sidebar, image=self.avatar_img, text="")
                avatar_lbl.pack(pady=(28, 10))
            except Exception:
                pass

        ctk.CTkLabel(
            self.sidebar, text=name, font=("Roboto", 18, "bold"), text_color=COLOR_TEXT_PRIMARY
        ).pack()

        role_badge = "ADMIN" if is_admin else "USER"
        ctk.CTkLabel(
            self.sidebar, text=f"[{role_badge}]  {email}", font=("Roboto", 11), text_color=COLOR_TEXT_MUTED
        ).pack(pady=(0, 20))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_CARD_BORDER).pack(fill="x", padx=16, pady=(0, 20))

        # Action Buttons
        btn_opts = {
            "font": ("Roboto", 14),
            "fg_color": "transparent",
            "hover_color": "#2c3345",
            "text_color": COLOR_TEXT_PRIMARY,
            "anchor": "w",
            "height": 40,
            "corner_radius": 8,
        }

        ctk.CTkButton(self.sidebar, text="🔄  Borrow Tool", command=self.action_borrow, **btn_opts).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self.sidebar, text="↩️  Return Tool", command=self.action_return, **btn_opts).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self.sidebar, text="➕  Add Tool", command=self.action_add, **btn_opts).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self.sidebar, text="🗑️  Delete Tool", command=self.action_delete, **btn_opts).pack(fill="x", padx=16, pady=4)

        # Logout at bottom
        ctk.CTkButton(
            self.sidebar,
            text="🚪  Logout",
            font=("Roboto", 14, "bold"),
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            command=self.logout,
            height=38,
            corner_radius=8,
        ).pack(side="bottom", fill="x", padx=16, pady=24)

    def _build_stats_section(self):
        self.stats_frame = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=(0, 16))

        self.stat_cards = {}
        cards = [
            ("total", "📦 Total Tools", "0", COLOR_ACCENT),
            ("available", "✅ Available", "0", COLOR_SUCCESS),
            ("borrowed", "🔄 Borrowed", "0", "#f39c12"),
            ("categories", "🏷️ Categories", "0", "#9b59b6"),
        ]

        for idx, (key, title, init_val, accent_color) in enumerate(cards):
            card = ctk.CTkFrame(
                self.stats_frame,
                fg_color=COLOR_CARD,
                corner_radius=14,
                border_width=1,
                border_color=COLOR_CARD_BORDER,
            )
            card.pack(side="left", fill="both", expand=True, padx=(0 if idx == 0 else 10, 0))

            ctk.CTkLabel(card, text=title, font=("Roboto", 13), text_color=COLOR_TEXT_MUTED).pack(
                anchor="w", padx=16, pady=(14, 2)
            )
            val_lbl = ctk.CTkLabel(card, text=init_val, font=("Roboto", 24, "bold"), text_color=accent_color)
            val_lbl.pack(anchor="w", padx=16, pady=(0, 14))
            self.stat_cards[key] = val_lbl

    def _build_controls_section(self):
        ctrl = ctk.CTkFrame(self.workspace, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 12))

        # Integrated Search
        self.search_entry = ctk.CTkEntry(
            ctrl,
            placeholder_text="🔍 Search tools by name or category...",
            font=("Roboto", 13),
            height=36,
            corner_radius=10,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search_keyup())

        # Category filter dropdown
        self.category_var = StringVar(value="All Categories")
        self.category_menu = ctk.CTkOptionMenu(
            ctrl,
            variable=self.category_var,
            values=["All Categories"],
            command=lambda c: self.apply_filters(),
            height=36,
            corner_radius=10,
            fg_color=COLOR_CARD,
            button_color=COLOR_CARD_BORDER,
        )
        self.category_menu.pack(side="left", padx=(0, 10))

        # Status filter dropdown
        self.status_var = StringVar(value="All Statuses")
        self.status_menu = ctk.CTkOptionMenu(
            ctrl,
            variable=self.status_var,
            values=["All Statuses", "Available", "Borrowed"],
            command=lambda s: self.apply_filters(),
            height=36,
            corner_radius=10,
            fg_color=COLOR_CARD,
            button_color=COLOR_CARD_BORDER,
        )
        self.status_menu.pack(side="left")

    def _build_table_section(self):
        table_card = ctk.CTkFrame(
            self.workspace,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        table_card.pack(fill="both", expand=True, pady=(0, 16))

        # Treeview Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=COLOR_CARD,
            fieldbackground=COLOR_CARD,
            foreground=COLOR_TEXT_PRIMARY,
            rowheight=32,
            font=("Roboto", 11),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#252b38",
            foreground=COLOR_ACCENT,
            font=("Roboto", 12, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", COLOR_ACCENT_HOVER)])

        cols = ("ID", "Name", "Category", "Condition", "Quantity", "Location", "Status")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")
        self.tree.pack(fill="both", expand=True, padx=14, pady=14)

        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            width = 60 if col == "ID" else (160 if col == "Name" else 110)
            self.tree.column(col, width=width, anchor="center")

        self.tree.tag_configure("evenrow", background=COLOR_CARD)
        self.tree.tag_configure("oddrow", background="#222836")

        self.tooltip = AdvancedToolTip(self.tree)
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", lambda e: self.tooltip.hide())

    def _build_chart_section(self):
        self.chart_card = ctk.CTkFrame(
            self.workspace,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            height=200,
        )
        self.chart_card.pack(fill="x")
        self.chart_card.pack_propagate(False)

    def refresh_dashboard(self):
        all_tools = self.db.fetch_all_tools()

        # Update Stat Cards
        total_count = len(all_tools)
        borrowed_count = sum(1 for t in all_tools if t["status"] == "borrowed" or t.get("borrower"))
        available_count = sum(1 for t in all_tools if t["status"] == "available" and not t.get("borrower"))
        categories = sorted({t["category"] for t in all_tools})

        self.stat_cards["total"].configure(text=str(total_count))
        self.stat_cards["available"].configure(text=str(available_count))
        self.stat_cards["borrowed"].configure(text=str(borrowed_count))
        self.stat_cards["categories"].configure(text=str(len(categories)))

        # Update Category Filter Menu
        curr_cat = self.category_var.get()
        new_cats = ["All Categories"] + categories
        self.category_menu.configure(values=new_cats)
        if curr_cat not in new_cats:
            self.category_var.set("All Categories")

        self.apply_filters()
        self._update_donut_chart(all_tools)

    def apply_filters(self):
        tools = self.db.fetch_all_tools()

        # Keyword filter
        query = self.search_entry.get().strip().lower()
        if query:
            tools = [
                t for t in tools
                if query in t["name"].lower() or query in t["category"].lower()
            ]

        # Category filter
        cat = self.category_var.get()
        if cat != "All Categories":
            tools = [t for t in tools if t["category"] == cat]

        # Status filter
        st = self.status_var.get()
        if st == "Available":
            tools = [t for t in tools if t["status"] == "available" and not t.get("borrower")]
        elif st == "Borrowed":
            tools = [t for t in tools if t["status"] == "borrowed" or t.get("borrower")]

        # Populate tree
        for row in self.tree.get_children():
            self.tree.delete(row)

        self._row_tooltips = {}
        for idx, t in enumerate(tools):
            status_text = "Borrowed" if (t["status"] == "borrowed" or t.get("borrower")) else "Available"
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    t["tool_id"],
                    t["name"],
                    t["category"],
                    t["condition"],
                    t["quantity"],
                    t.get("location", ""),
                    status_text,
                ),
                tags=(tag,),
            )
            # Hover detail text
            self._row_tooltips[item_id] = (
                f"ID: {t['tool_id']} | {t['name']}\n"
                f"Category: {t['category']} | Condition: {t['condition']}\n"
                f"Qty: {t['quantity']} | Location: {t.get('location','')}\n"
                f"Status: {status_text}"
                + (f"\nBorrower: {t.get('borrower')} ({t.get('borrow_date')})" if t.get('borrower') else "")
            )

    def on_search_keyup(self):
        self.apply_filters()

    def sort_by_column(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(key=lambda x: int(x[0]))
        except ValueError:
            items.sort(key=lambda x: str(x[0]).lower())
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)

    def _on_tree_motion(self, event):
        item = self.tree.identify_row(event.y)
        if item and hasattr(self, "_row_tooltips") and item in self._row_tooltips:
            x = self.tree.winfo_rootx() + event.x + 15
            y = self.tree.winfo_rooty() + event.y + 10
            self.tooltip.show(self._row_tooltips[item], x, y)
        else:
            self.tooltip.hide()

    def _update_donut_chart(self, tools):
        for w in self.chart_card.winfo_children():
            w.destroy()

        cat_counts = {}
        for t in tools:
            c = t["category"]
            cat_counts[c] = cat_counts.get(c, 0) + 1

        if not cat_counts:
            ctk.CTkLabel(
                self.chart_card, text="No inventory data for chart", font=("Roboto", 12), text_color=COLOR_TEXT_MUTED
            ).pack(expand=True)
            return

        fig = Figure(figsize=(8, 1.8), dpi=100, facecolor=COLOR_CARD)
        ax = fig.add_subplot(111)
        colors = ["#4f8cff", "#2ecc71", "#f39c12", "#9b59b6", "#e74c3c", "#1abc9c", "#34495e"]

        wedges, texts, autotexts = ax.pie(
            cat_counts.values(),
            labels=None,
            autopct="%1.0f%%",
            pctdistance=0.75,
            colors=colors[: len(cat_counts)],
            wedgeprops=dict(width=0.4, edgecolor=COLOR_CARD, linewidth=2),
            textprops=dict(color=COLOR_TEXT_PRIMARY, fontsize=9, fontweight="bold"),
        )

        ax.legend(
            wedges,
            cat_counts.keys(),
            title="Categories",
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=9,
            title_fontsize=10,
            labelcolor=COLOR_TEXT_PRIMARY,
            frameon=False,
        )
        ax.axis("equal")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.chart_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # -- Action Dialogs --------------------------------------------------------
    def action_borrow(self):
        available = self.tools.available_tools()
        if not available:
            messagebox.showwarning("Borrow Tool", "No tools are currently available to borrow.")
            return

        tool_names = [t["name"] for t in available]
        top = ctk.CTkToplevel(self.window)
        top.geometry("380x280")
        top.title("Borrow Tool")
        top.attributes("-topmost", True)
        top.configure(bg=COLOR_BG_DARK)

        frame = ctk.CTkFrame(top, fg_color=COLOR_CARD, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Select Tool to Borrow", font=("Roboto", 16, "bold"), text_color=COLOR_ACCENT).pack(pady=(12, 16))

        tool_var = StringVar(value=tool_names[0])
        ctk.CTkOptionMenu(frame, variable=tool_var, values=tool_names, width=280).pack(pady=8)

        err_lbl = ctk.CTkLabel(frame, text="", font=("Roboto", 11), text_color=COLOR_DANGER)
        err_lbl.pack(pady=4)

        def do_borrow():
            name = tool_var.get()
            selected = next((t for t in available if t["name"] == name), None)
            if not selected:
                err_lbl.configure(text="Selected tool not found")
                return
            try:
                self.tools.borrow_tool(selected["tool_id"], self.user_id)
                top.destroy()
                messagebox.showinfo("Success", f"'{name}' borrowed successfully!")
                self.refresh_dashboard()
            except ServiceError as err:
                err_lbl.configure(text=str(err))

        ctk.CTkButton(frame, text="Confirm Borrow", command=do_borrow, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, width=200).pack(pady=12)

    def action_return(self):
        borrowed = self.tools.my_borrowed_tools(self.user_id)
        if not borrowed:
            messagebox.showwarning("Return Tool", "You have no borrowed tools to return.")
            return

        tool_names = [t["name"] for t in borrowed]
        top = ctk.CTkToplevel(self.window)
        top.geometry("380x280")
        top.title("Return Tool")
        top.attributes("-topmost", True)

        frame = ctk.CTkFrame(top, fg_color=COLOR_CARD, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Select Tool to Return", font=("Roboto", 16, "bold"), text_color=COLOR_ACCENT).pack(pady=(12, 16))

        tool_var = StringVar(value=tool_names[0])
        ctk.CTkOptionMenu(frame, variable=tool_var, values=tool_names, width=280).pack(pady=8)

        err_lbl = ctk.CTkLabel(frame, text="", font=("Roboto", 11), text_color=COLOR_DANGER)
        err_lbl.pack(pady=4)

        def do_return():
            name = tool_var.get()
            selected = next((t for t in borrowed if t["name"] == name), None)
            if not selected:
                err_lbl.configure(text="Selected tool not found")
                return
            try:
                self.tools.return_tool(selected["tool_id"], self.user_id)
                top.destroy()
                messagebox.showinfo("Success", f"'{name}' returned successfully!")
                self.refresh_dashboard()
            except ServiceError as err:
                err_lbl.configure(text=str(err))

        ctk.CTkButton(frame, text="Confirm Return", command=do_return, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, width=200).pack(pady=12)

    def action_add(self):
        top = ctk.CTkToplevel(self.window)
        top.geometry("400x420")
        top.title("Add New Tool")
        top.attributes("-topmost", True)

        frame = ctk.CTkFrame(top, fg_color=COLOR_CARD, corner_radius=14, border_width=1, border_color=COLOR_CARD_BORDER)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Add New Inventory Item", font=("Roboto", 16, "bold"), text_color=COLOR_ACCENT).pack(pady=(10, 12))

        pad = {"fill": "x", "padx": 20, "pady": 4}
        e_name = ctk.CTkEntry(frame, placeholder_text="Tool Name", font=("Roboto", 13))
        e_name.pack(**pad)

        e_cat = ctk.CTkEntry(frame, placeholder_text="Category", font=("Roboto", 13))
        e_cat.pack(**pad)

        e_cond = ctk.CTkEntry(frame, placeholder_text="Condition (Good/Fair/Poor)", font=("Roboto", 13))
        e_cond.pack(**pad)

        e_qty = ctk.CTkEntry(frame, placeholder_text="Quantity", font=("Roboto", 13))
        e_qty.pack(**pad)

        e_loc = ctk.CTkEntry(frame, placeholder_text="Location / Shelf", font=("Roboto", 13))
        e_loc.pack(**pad)

        err_lbl = ctk.CTkLabel(frame, text="", font=("Roboto", 11), text_color=COLOR_DANGER)
        err_lbl.pack(pady=2)

        def do_add():
            try:
                self.tools.add_tool(
                    e_name.get(),
                    e_cat.get(),
                    e_cond.get(),
                    e_qty.get(),
                    e_loc.get(),
                    actor=self.user_id,
                )
                top.destroy()
                messagebox.showinfo("Success", f"Tool '{e_name.get().strip()}' added!")
                self.refresh_dashboard()
            except ServiceError as err:
                err_lbl.configure(text=str(err))

        ctk.CTkButton(frame, text="Save Tool", command=do_add, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, width=200).pack(pady=10)

    def action_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Delete Tool", "Please select a tool from the table to delete.")
            return

        values = self.tree.item(sel[0], "values")
        tool_id, tool_name = values[0], values[1]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{tool_name}' (ID: {tool_id})?"):
            try:
                self.tools.delete_tool(tool_id, actor=self.user_id)
                messagebox.showinfo("Success", f"Tool '{tool_name}' deleted.")
                self.refresh_dashboard()
            except ServiceError as err:
                messagebox.showerror("Access Denied", str(err))

    def logout(self):
        self.window.destroy()
        LoginApp(self.db_path)


if __name__ == "__main__":
    db_path = "./db/inventory.db"
    LoginApp(db_path)
