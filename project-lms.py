"""
Project-LMS — Enterprise Inventory Command Center
=================================================

Modernized CustomTkinter frontend, organized as composable frame classes
instead of a monolithic build script:

    LoginApp                  -- obsidian login / sign-up flow
    MainApp(ctk.CTk)          -- application shell (grid master-detail)
    ├─ SidebarFrame           -- fixed-width navigation rail
    ├─ HeaderBar              -- global search, notification bell, profile badge
    └─ DashboardView          -- KPI cards, filter chips, data grid, chart

All colors and typography come from `gui/theme.py`; dialogs in
`gui/dialogs.py` consume the same design system unchanged.
"""

import datetime
import logging
import os
import tkinter as tk
from tkinter import StringVar, ttk

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")  # Headless-style embedding of Figures into Tk.
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PIL import Image, ImageDraw, ImageTk

logger = logging.getLogger("project_lms.gui")

from database import DatabaseManager
from gui import theme
from gui.theme import (
    CHART_PALETTE,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_SOFT,
    COLOR_BG_DARK,
    COLOR_CARD,
    COLOR_CARD_ALT,
    COLOR_CARD_BORDER,
    COLOR_DANGER,
    COLOR_DANGER_HOVER,
    COLOR_DIVIDER,
    COLOR_SIDEBAR,
    COLOR_SUCCESS,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_WARNING,
    COLOR_WINDOW,
    F,
    FM,
)
from gui.dialogs import (
    AdvancedToolTip,
    AddToolDialog,
    BorrowDialog,
    DeleteToolDialog,
    ReturnDialog,
)
from service import AuthService, ServiceError, ToolService

RETURN_EVENT = "<Return>"
DB_PATH = "./db/inventory.db"

ctk.set_appearance_mode("dark")  # Force dark chrome on every CTk widget.


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def load_ctk_circle_avatar(image_path, size):
    """Load `image_path` center-cropped to a circle as a CTkImage.

    Returns None when the asset is missing so callers can fall back to an
    initials badge instead of crashing on first run.
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        side = min(img.size)  # Center-crop to square before masking.
        left = (img.width - side) // 2
        top = (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize(
            (size, size), Image.Resampling.LANCZOS
        )
        # 4x supersampled circular mask keeps the edge smooth.
        mask = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * 4, size * 4), fill=255)
        img.putalpha(mask.resize((size, size), Image.Resampling.LANCZOS))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        logger.warning("Avatar not loaded from %s", image_path, exc_info=True)
        return None


def make_card(parent):
    """Factory for the standard rounded card container used across the UI."""
    return ctk.CTkFrame(
        parent,
        fg_color=COLOR_CARD,
        corner_radius=12,
        border_width=1,
        border_color=COLOR_CARD_BORDER,
    )


def initials_badge(parent, text, size=48):
    """Fallback avatar: accent-on-emerald initial inside a soft round chip."""
    return ctk.CTkLabel(
        parent,
        text=(text or "?")[0].upper(),
        font=F(size // 2, "bold"),
        text_color=COLOR_ACCENT,
        fg_color=COLOR_ACCENT_SOFT,
        corner_radius=size // 2,
        width=size,
        height=size,
    )


# ---------------------------------------------------------------------------
# Authentication flow
# ---------------------------------------------------------------------------
class LoginApp:
    """Obsidian-styled login / registration flow shown before the shell."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.db = DatabaseManager(self.db_path)
        self.auth = AuthService(self.db)
        self.create_login_window()

    # -- login window ----------------------------------------------------------
    def create_login_window(self):
        """Build the centered glass-card login form over the obsidian canvas."""
        probe = tk.Tk()
        sw, sh = probe.winfo_screenwidth(), probe.winfo_screenheight()
        probe.destroy()

        ww, wh = max(420, int(sw * 0.32)), max(520, int(sh * 0.52))

        self.login_window = ctk.CTk(fg_color=COLOR_WINDOW)
        self.login_window.geometry(f"{ww}x{wh}")
        self.login_window.title("Login | Project-LMS")
        self.login_window.resizable(False, False)

        theme.resolve_fonts()  # Font detection needs this fresh Tk root.

        x, y = (sw // 2) - (ww // 2), (sh // 2) - (wh // 2)
        self.login_window.geometry(f"+{x}+{y}")

        # Optional wallpaper behind the card.
        bg_path = os.path.join("assets", "background_image.jpg")
        if os.path.exists(bg_path):
            try:
                bg_img = Image.open(bg_path).resize((ww, wh), Image.Resampling.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(bg_img)  # GC-safe reference
                tk.Label(self.login_window, image=self.bg_photo, borderwidth=0).place(
                    x=0, y=0, relwidth=1, relheight=1
                )
            except Exception:
                logger.warning("Failed to load login wallpaper.", exc_info=True)

        card = make_card(self.login_window)
        card.place(relx=0.5, rely=0.5, anchor="center")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=44, pady=40)

        ctk.CTkLabel(inner, text="◆ PROJECT-LMS", font=F(22, "bold"),
                     text_color=COLOR_ACCENT).pack(pady=(0, 2))
        ctk.CTkLabel(inner, text="Sign in to continue", font=F(12),
                     text_color=COLOR_TEXT_MUTED).pack(pady=(0, 26))

        self.username_entry = self._field(inner, "Username")
        self.password_entry = self._field(inner, "Password", show="•")

        self.error_label = ctk.CTkLabel(inner, text="", font=F(11),
                                        text_color=COLOR_DANGER, wraplength=300)
        self.error_label.pack(pady=(0, 10))

        ctk.CTkButton(
            inner, text="Sign In", command=self.login, font=F(14, "bold"),
            height=42, corner_radius=10, fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER, text_color="#04150c",
        ).pack(fill="x", pady=(0, 12))

        signup_link = ctk.CTkLabel(
            inner, text="New User? Create an Account", font=F(12, "underline"),
            text_color=COLOR_ACCENT, cursor="hand2",
        )
        signup_link.pack()
        signup_link.bind("<Button-1>", lambda e: self.signup_transition())

        self.username_entry.focus_set()
        self.username_entry.bind(RETURN_EVENT, lambda e: self.password_entry.focus())
        self.password_entry.bind(RETURN_EVENT, lambda e: self.login())
        self.login_window.mainloop()

    def _field(self, parent, placeholder, **entry_kwargs):
        """One labeled input group: muted uppercase label + dark rounded entry."""
        ctk.CTkLabel(parent, text=placeholder.upper(), font=F(10, "bold"),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", pady=(0, 4))
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder, font=F(13), height=42,
            corner_radius=10, fg_color=COLOR_CARD_ALT,
            border_color=COLOR_DIVIDER, **entry_kwargs,
        )
        entry.pack(fill="x", pady=(0, 16), ipadx=0)
        return entry

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
            MainApp(self.user_id, self.db, self.db_path)
        except ServiceError as exc:
            self.error_label.configure(text=str(exc))

    # -- signup window -----------------------------------------------------------
    def create_signup_window(self):
        self.signup_window = ctk.CTk(fg_color=COLOR_WINDOW)
        self.signup_window.geometry("460x680")
        self.signup_window.title("Sign Up | Project-LMS")
        self.signup_window.resizable(False, False)

        bg_path = os.path.join("assets", "background_image_light.jpg")
        if os.path.exists(bg_path):
            try:
                bg_img = Image.open(bg_path).resize((460, 680), Image.Resampling.LANCZOS)
                self.signup_bg_photo = ImageTk.PhotoImage(bg_img)
                tk.Label(self.signup_window, image=self.signup_bg_photo, borderwidth=0).place(
                    x=0, y=0, relwidth=1, relheight=1
                )
            except Exception:
                logger.warning("Failed to load signup wallpaper.", exc_info=True)

        card = make_card(self.signup_window)
        card.place(relx=0.5, rely=0.5, anchor="center")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=40, pady=32)

        ctk.CTkLabel(inner, text="Create Account", font=F(20, "bold"),
                     text_color=COLOR_TEXT_PRIMARY).pack(pady=(0, 18))

        pad = {"fill": "x", "padx": 4}
        self.signup_username = self._field(inner, "Username"); self.signup_username.pack(**pad)
        self.signup_pw = self._field(inner, "Password", show="•"); self.signup_pw.pack(**pad)
        self.signup_cpw = self._field(inner, "Confirm Password", show="•"); self.signup_cpw.pack(**pad)
        self.signup_name = self._field(inner, "Full Name"); self.signup_name.pack(**pad)
        self.signup_age = self._field(inner, "Age"); self.signup_age.pack(**pad)
        self.signup_email = self._field(inner, "Email Address"); self.signup_email.pack(**pad)

        self.signup_error = ctk.CTkLabel(inner, text="", font=F(11), text_color=COLOR_DANGER)
        self.signup_error.pack(pady=(4, 6))

        ctk.CTkButton(
            inner, text="Register", command=self.register_user, font=F(13, "bold"),
            height=42, corner_radius=10, fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER, text_color="#04150c",
        ).pack(fill="x", padx=4, pady=(0, 8))
        ctk.CTkButton(
            inner, text="Back to Login", command=self.back_to_login, font=F(12),
            height=34, corner_radius=10, fg_color="transparent",
            hover_color=COLOR_CARD_ALT, text_color=COLOR_TEXT_MUTED,
        ).pack(fill="x", padx=4, pady=(0, 8))

        self.signup_username.focus_set()
        self.signup_window.mainloop()

    def register_user(self):
        try:
            self.auth.register(
                self.signup_username.get().strip(),
                self.signup_pw.get(),
                self.signup_cpw.get(),
                self.signup_name.get().strip(),
                self.signup_age.get().strip(),
                self.signup_email.get().strip(),
            )
            self.signup_error.configure(
                text="Signup successful! Returning to login…", text_color=COLOR_SUCCESS
            )
            self.signup_window.after(1000, self.back_to_login)
        except ServiceError as err:
            self.signup_error.configure(text=str(err), text_color=COLOR_DANGER)

    def back_to_login(self):
        self.signup_window.destroy()
        self.create_login_window()

    def signup_transition(self):
        self.login_window.destroy()
        self.create_signup_window()


# ---------------------------------------------------------------------------
# Shell components
# ---------------------------------------------------------------------------
class SidebarFrame(ctk.CTkFrame):
    """Fixed-width master rail: brand block, profile card, nav, actions."""

    WIDTH = 240

    def __init__(self, master, user_info, actions):
        super().__init__(
            master, width=self.WIDTH, corner_radius=0, fg_color=COLOR_SIDEBAR
        )
        self.grid_propagate(False)  # Honor the fixed width during resize.

        # -- brand -----------------------------------------------------------------
        ctk.CTkLabel(self, text="◆ PROJECT-LMS", font=F(17, "bold"),
                     text_color=COLOR_ACCENT).pack(pady=(28, 2))
        ctk.CTkLabel(self, text="INVENTORY COMMAND CENTER", font=F(9, "bold"),
                     text_color=COLOR_TEXT_MUTED).pack(pady=(0, 20))

        # -- current-user profile ----------------------------------------------------
        avatar = load_ctk_circle_avatar(os.path.join("assets", "user.png"), 56)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(0, 20), padx=18)
        if avatar:
            ctk.CTkLabel(row, image=avatar, text="").pack(side="left", padx=(0, 10))
        else:
            initials_badge(row, user_info["name"], 56).pack(side="left", padx=(0, 10))
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text=user_info["name"] if user_info else "User",
                     font=F(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        role = "ADMIN" if (user_info and user_info.get("is_admin")) else "USER"
        ctk.CTkLabel(info, text=role, font=F(9, "bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        ctk.CTkFrame(self, height=1, fg_color=COLOR_DIVIDER).pack(fill="x", padx=18, pady=(0, 16))

        # -- navigation (active state managed by set_active) ----------------------------
        ctk.CTkLabel(self, text="NAVIGATION", font=F(10, "bold"),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=24, pady=(0, 8))
        self.nav_buttons = {}
        dash_btn = ctk.CTkButton(
            self, text="   ◫  Dashboard", anchor="w", height=40, corner_radius=8,
            font=F(12), fg_color=COLOR_ACCENT_SOFT, hover_color=COLOR_CARD_ALT,
            text_color=COLOR_ACCENT,
        )
        dash_btn.pack(fill="x", padx=14, pady=3)
        self.nav_buttons["dashboard"] = dash_btn

        # -- inventory quick actions --------------------------------------------------------
        ctk.CTkLabel(self, text="QUICK ACTIONS", font=F(10, "bold"),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=24, pady=(18, 8))
        for label, cmd in (
            ("⟳  Borrow Tool", actions["borrow"]),
            ("↩  Return Tool", actions["return"]),
            ("＋  Add Tool", actions["add"]),
            ("✕  Delete Tool", actions["delete"]),
        ):
            ctk.CTkButton(
                self, text=f"   {label}", anchor="w", height=38, corner_radius=8,
                font=F(12), fg_color="transparent", hover_color=COLOR_CARD_ALT,
                text_color=COLOR_TEXT_PRIMARY, command=cmd,
            ).pack(fill="x", padx=14, pady=3)

        # -- logout pinned to bottom -------------------------------------------------------------
        ctk.CTkButton(
            self, text="⏻  Log Out", command=actions["logout"], height=38,
            corner_radius=8, font=F(12, "bold"), fg_color="transparent",
            hover_color=COLOR_DANGER_HOVER, text_color=COLOR_DANGER,
        ).pack(side="bottom", fill="x", padx=14, pady=16)


class HeaderBar(ctk.CTkFrame):
    """Workspace top bar: global search, notification bell, profile badge."""

    def __init__(self, master, user_info, on_search):
        super().__init__(master, height=64, corner_radius=0, fg_color=COLOR_WINDOW)
        self.grid_columnconfigure(0, weight=1)

        # -- global search field -----------------------------------------------------
        box = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10,
                           border_width=1, border_color=COLOR_CARD_BORDER)
        box.grid(row=0, column=0, sticky="ew", pady=12, padx=(24, 12))
        ctk.CTkLabel(box, text="⌕", font=F(15), text_color=COLOR_TEXT_MUTED).pack(
            side="left", padx=(12, 4)
        )
        self.search_var = StringVar()
        self.search_entry = ctk.CTkEntry(
            box, placeholder_text="Search tools by name or category…",
            font=F(12), border_width=0, fg_color="transparent",
            textvariable=self.search_var,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, pady=7, padx=(2, 12))
        # Live filter on every keystroke, matching legacy behavior.
        self.search_entry.bind("<KeyRelease>", lambda e: on_search())

        # -- notification bell with live badge -----------------------------------------
        self.bell_btn = ctk.CTkButton(
            self, text="🔔", width=40, height=40, corner_radius=10,
            fg_color=COLOR_CARD, hover_color=COLOR_CARD_ALT,
            border_width=1, border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT_PRIMARY, command=self.show_notifications,
        )
        self.bell_btn.grid(row=0, column=1, pady=12, padx=(0, 14))
        self.badge = ctk.CTkLabel(
            self, text="0", font=FM(10, "bold"), fg_color=COLOR_DANGER,
            text_color="#ffffff", corner_radius=8, width=18, height=18,
        )
        # Overlap the count chip onto the bell's top-right corner.
        self.badge.place(in_=self.bell_btn, relx=0.70, rely=0.04)
        # Hover summary of currently borrowed items.
        self._bell_text = "0 item(s) currently borrowed"
        self.tooltip_bell = AdvancedToolTip(self.bell_btn)
        self.bell_btn.bind("<Enter>", self._show_bell_tip)
        self.bell_btn.bind("<Leave>", lambda e: self.tooltip_bell.hide())

        # -- profile badge ------------------------------------------------------------------
        avatar = load_ctk_circle_avatar(os.path.join("assets", "user.png"), 34)
        prof = ctk.CTkFrame(self, fg_color="transparent")
        prof.grid(row=0, column=2, pady=12, padx=(0, 24))
        if avatar:
            ctk.CTkLabel(prof, image=avatar, text="").pack(side="left", padx=(0, 8))
        else:
            initials_badge(prof, user_info["name"] if user_info else "?", 34).pack(
                side="left", padx=(0, 8)
            )
        meta = ctk.CTkFrame(prof, fg_color="transparent")
        meta.pack(side="left")
        ctk.CTkLabel(meta, text=user_info["name"] if user_info else "",
                     font=F(12, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(meta, text=user_info["email"] if user_info else "",
                     font=F(9), text_color=COLOR_TEXT_MUTED).pack(anchor="w")

    # -- public API ----------------------------------------------------------------------
    def show_notifications(self):
        """Bell click: summarize the user's currently borrowed items."""
        from tkinter import messagebox

        count = self.badge.cget("text")
        messagebox.showinfo(
            "Notifications",
            f"You are currently borrowing {count} item(s).\n"
            "Use Return Tool to give items back.",
        )

    def get_query(self):
        return self.search_var.get().strip().lower()

    def _show_bell_tip(self, event):
        x = self.bell_btn.winfo_rootx() + self.bell_btn.winfo_width() // 2
        y = self.bell_btn.winfo_rooty() + self.bell_btn.winfo_height() + 6
        self.tooltip_bell.show(self._bell_text, x, y)

    def set_notification_count(self, count):
        """Update the bell badge and its hover text."""
        self.badge.configure(text=str(count))
        self._bell_text = f"{count} item(s) currently borrowed"


class StatCard(ctk.CTkFrame):
    """Compact metric card: muted label + large mono numeral + delta chip."""

    def __init__(self, master, title, accent):
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=12,
                         border_width=1, border_color=COLOR_CARD_BORDER)
        ctk.CTkLabel(self, text=title.upper(), font=F(10, "bold"),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=18, pady=(14, 2))
        self.value_label = ctk.CTkLabel(self, text="0", font=FM(26, "bold"),
                                        text_color=accent, anchor="w")
        self.value_label.pack(fill="x", padx=18)
        self.delta_label = ctk.CTkLabel(self, text="", font=F(11),
                                        text_color=COLOR_TEXT_MUTED, anchor="w")
        self.delta_label.pack(fill="x", padx=18, pady=(2, 14))

    def set_delta(self, current, previous):
        """▲ / ▼ / steady chip comparing against the previous refresh."""
        if current > previous:
            self.delta_label.configure(text=f"▲ +{current - previous}", text_color=COLOR_SUCCESS)
        elif current < previous:
            self.delta_label.configure(text=f"▼ {current - previous}", text_color=COLOR_DANGER)
        else:
            self.delta_label.configure(text="— steady", text_color=COLOR_TEXT_MUTED)


class DashboardView(ctk.CTkFrame):
    """Main workspace: KPI strip, filters, data grid, donut chart, footer."""

    COLUMNS = ("ID", "Name", "Category", "Condition", "Quantity", "Location", "Status")

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._prev_stats = {"total": 0, "available": 0, "borrowed": 0, "categories": 0}
        self.sort_descending = False
        self._last_tooltip_row = None
        self._row_tooltips = {}

        self._configure_tree_style()
        self._build_stat_strip()
        self._build_filter_bar()
        self._build_table_card()
        self._build_chart_card()
        self._build_footer()

        # Grid weights: the table row absorbs all extra vertical space.
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # -- ttk Treeview theming ------------------------------------------------------
    def _configure_tree_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Dashboard.Treeview",
            background=COLOR_CARD,
            fieldbackground=COLOR_CARD,
            foreground=COLOR_TEXT_PRIMARY,
            rowheight=32,
            font=F(11),
            borderwidth=0,
        )
        style.configure(
            "Dashboard.Treeview.Heading",
            background=COLOR_CARD_ALT,
            foreground=COLOR_ACCENT,
            font=F(11, "bold"),
            relief="flat",
        )
        # Emerald wash keeps white selection text readable.
        style.map(
            "Dashboard.Treeview",
            background=[("selected", COLOR_ACCENT_HOVER)],
            foreground=[("selected", "#ffffff")],
        )

    # -- row 0: KPI cards ---------------------------------------------------------------
    def _build_stat_strip(self):
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        for col in range(4):
            strip.grid_columnconfigure(col, weight=1, uniform="stat")

        self.total_card = StatCard(strip, "Total Tools", COLOR_ACCENT)
        self.available_card = StatCard(strip, "Available", COLOR_SUCCESS)
        self.borrowed_card = StatCard(strip, "Borrowed", COLOR_WARNING)
        self.categories_card = StatCard(strip, "Categories", "#bc8cff")
        for i, card in enumerate(
            (self.total_card, self.available_card, self.borrowed_card, self.categories_card)
        ):
            strip_pad = (0, 12) if i < 3 else (0, 0)
            card.grid(row=0, column=i, sticky="nsew", padx=strip_pad)

    def update_stats(self, total, available, borrowed, categories):
        """Push computed KPI numbers into the cards and render delta chips."""
        for key, card, value in (
            ("total", self.total_card, total),
            ("available", self.available_card, available),
            ("borrowed", self.borrowed_card, borrowed),
            ("categories", self.categories_card, categories),
        ):
            card.value_label.configure(text=str(value))
            card.set_delta(value, self._prev_stats[key])
            self._prev_stats[key] = value

    # -- row 1: filter chips --------------------------------------------------------------
    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))

        self.category_var = StringVar(value="All Categories")
        self.status_var = StringVar(value="All Statuses")
        menu_opts = dict(
            height=34, corner_radius=10, font=F(11), fg_color=COLOR_CARD,
            button_color=COLOR_CARD_ALT, button_hover_color=COLOR_DIVIDER,
            dropdown_fg_color=COLOR_CARD_ALT, dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_hover_color=COLOR_ACCENT_SOFT,
        )
        self.category_menu = ctk.CTkOptionMenu(
            bar, variable=self.category_var, values=["All Categories"],
            width=170, command=lambda _c: self.apply_filters(), **menu_opts,
        )
        self.category_menu.pack(side="left", padx=(0, 10))
        self.status_menu = ctk.CTkOptionMenu(
            bar, variable=self.status_var,
            values=["All Statuses", "Available", "Borrowed"],
            width=150, command=lambda _s: self.apply_filters(), **menu_opts,
        )
        self.status_menu.pack(side="left")

    def update_category_options(self, categories):
        """Refresh the category dropdown without resetting the user's choice."""
        current = self.category_var.get()
        values = ["All Categories"] + list(categories)
        self.category_menu.configure(values=values)
        if current not in values:
            self.category_var.set("All Categories")

    # -- row 2: data grid -------------------------------------------------------------------
    def _build_table_card(self):
        card = make_card(self)
        card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 14))

        self.tree = ttk.Treeview(
            card, columns=self.COLUMNS, show="headings",
            style="Dashboard.Treeview", selectmode="browse",
        )
        self.tree.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=14)
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=14)

        widths = {"ID": 60, "Name": 170, "Category": 110, "Condition": 90,
                  "Quantity": 70, "Location": 100, "Status": 90}
        for col in self.COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=widths[col], anchor="center", stretch=True)

        # Alternating tints + semantic emphasis.
        self.tree.tag_configure("evenrow", background=COLOR_CARD)
        self.tree.tag_configure("oddrow", background=COLOR_CARD_ALT)
        self.tree.tag_configure("empty", background=COLOR_CARD, foreground=COLOR_TEXT_MUTED)

        self.tooltip = AdvancedToolTip(self.tree)
        self.tree.bind("<Motion>", self.on_tree_motion)
        self.tree.bind("<Leave>", self.on_tree_leave)

    def populate_table(self, tools):
        """Re-render the grid with zebra tinting and per-row hover details."""
        self.tree.delete(*self.tree.get_children())
        self._row_tooltips.clear()
        if not tools:
            # Single muted placeholder row keeps the grid visually anchored.
            self.tree.insert("", "end", values=(
                "", "📭  No tools match the current filters.", "", "", "", "", "",
            ), tags=("empty",))
            return
        for idx, t in enumerate(tools):
            borrowed = t["status"] == "borrowed" or t.get("borrower")
            status_text = "Borrowed" if borrowed else "Available"
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            item_id = self.tree.insert("", "end", values=(
                t["tool_id"], t["name"], t["category"], t["condition"],
                t["quantity"], t.get("location", ""), status_text,
            ), tags=(tag,))
            self._row_tooltips[item_id] = (
                f"ID: {t['tool_id']} | {t['name']}\n"
                f"Category: {t['category']} | Condition: {t['condition']}\n"
                f"Qty: {t['quantity']} | Location: {t.get('location', '')}\n"
                f"Status: {status_text}"
                + (f"\nBorrower: {t.get('borrower')} ({t.get('borrow_date')})" if t.get("borrower") else "")
            )

    # -- sorting (tree-move approach, proven in the legacy app) -------------------------------
    def sort_by_column(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(key=lambda x: int(x[0]), reverse=self.sort_descending)
        except ValueError:
            items.sort(key=lambda x: str(x[0]).lower(), reverse=self.sort_descending)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        # Arrow indicator on the active heading.
        for c in self.COLUMNS:
            suffix = ""
            if c == col:
                suffix = " ↓" if self.sort_descending else " ↑"
            self.tree.heading(c, text=c + suffix)
        self.sort_descending = not self.sort_descending

    # -- row hover tooltips -----------------------------------------------------------------
    def on_tree_motion(self, event):
        item = self.tree.identify_row(event.y)
        # Only re-show when the hovered row actually changes; rebuilding the
        # Toplevel per motion event would flicker dozens of times a second.
        if item == self._last_tooltip_row:
            return
        self._last_tooltip_row = item
        if item and item in self._row_tooltips:
            self.tooltip.show(
                self._row_tooltips[item],
                self.tree.winfo_rootx() + event.x + 15,
                self.tree.winfo_rooty() + event.y + 10,
            )
        else:
            self.tooltip.hide()

    def on_tree_leave(self, event):
        # Reset cache so re-entering the same row re-shows its tooltip.
        self._last_tooltip_row = None
        self.tooltip.hide()

    # -- row 3: analytics chart ---------------------------------------------------------------
    def _build_chart_card(self):
        self.chart_card = make_card(self)
        self.chart_card.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))
        self.chart_card.grid_rowconfigure(0, weight=1)
        self.chart_card.grid_columnconfigure(0, weight=1)
        self.chart_card.configure(height=190)
        self.chart_card.grid_propagate(False)

        # One long-lived figure redrawn in place — never leaks matplotlib
        # resources across refreshes (the legacy bug fixed for good).
        self.chart_fig = Figure(figsize=(8, 1.8), dpi=100, facecolor=COLOR_CARD)
        self.chart_ax = self.chart_fig.add_subplot(111)
        self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, master=self.chart_card)
        self.chart_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def update_chart(self, tools):
        counts = {}
        for t in tools:
            counts[t["category"]] = counts.get(t["category"], 0) + 1

        self.chart_ax.clear()
        if not counts:
            self.chart_ax.text(0.5, 0.5, "No inventory data", ha="center", va="center",
                               color=COLOR_TEXT_MUTED, fontsize=10)
            self.chart_ax.axis("off")
        else:
            colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(counts))]
            wedges, _, autotexts = self.chart_ax.pie(
                counts.values(), labels=None, autopct="%1.0f%%", pctdistance=0.75,
                colors=colors,
                wedgeprops=dict(width=0.4, edgecolor=COLOR_CARD, linewidth=2),
                textprops=dict(color=COLOR_TEXT_PRIMARY, fontsize=9, fontweight="bold"),
            )
            self.chart_ax.legend(
                wedges, counts.keys(), title="Categories", loc="center left",
                bbox_to_anchor=(1.02, 0.5), fontsize=9, title_fontsize=10,
                labelcolor=COLOR_TEXT_PRIMARY, frameon=False,
            )
            self.chart_ax.axis("equal")
        self.chart_fig.tight_layout(pad=0.4)
        self.chart_canvas.draw_idle()

    # -- row 4: footer ---------------------------------------------------------------------------
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10,
                              border_width=1, border_color=COLOR_CARD_BORDER, height=34)
        footer.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 16))
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        self.footer_status = ctk.CTkLabel(footer, text="", font=F(11),
                                          text_color=COLOR_TEXT_MUTED, anchor="w")
        self.footer_status.grid(row=0, column=0, sticky="w", padx=14, pady=6)
        self.footer_sync = ctk.CTkLabel(footer, text="", font=FM(10),
                                        text_color=COLOR_TEXT_MUTED, anchor="e")
        self.footer_sync.grid(row=0, column=1, sticky="e", padx=14, pady=6)

    def set_footer(self, total, available, borrowed, categories, loading=False):
        if loading:
            self.footer_sync.configure(text="● Refreshing…", text_color=COLOR_ACCENT)
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.footer_status.configure(text=(
            f"{total} total · {available} available · "
            f"{borrowed} borrowed · {categories} categories"
        ))
        if not loading:
            self.footer_sync.configure(text=f"✓ Last refresh {stamp}", text_color=COLOR_SUCCESS)


# ---------------------------------------------------------------------------
# Main application shell
# ---------------------------------------------------------------------------
class MainApp(ctk.CTk):
    """Root window: grid master-detail — sidebar rail + fluid workspace."""

    def __init__(self, user_id, db, db_path=DB_PATH):
        super().__init__(fg_color=COLOR_WINDOW)
        theme.resolve_fonts()

        self.user_id = user_id
        self.db = db
        self.db_path = db_path
        self.tools = ToolService(db)

        self.title("Project-LMS | Inventory Command Center")
        self.geometry("1280x820")
        self.minsize(1100, 720)

        # Public seam — no raw SQL from the GUI layer.
        user_info = db.fetch_user_by_id(user_id)
        if not user_info:
            logger.error("User %s vanished between login and dashboard.", user_id)
            self.destroy()
            return

        self._build_layout(user_info)
        self.refresh_dashboard()
        self.mainloop()

    # -- layout ------------------------------------------------------------------------
    def _build_layout(self, user_info):
        """Grid skeleton: column 0 sidebar (fixed), column 1 workspace (fluid)."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = SidebarFrame(self, user_info, actions={
            "borrow": self.action_borrow,
            "return": self.action_return,
            "add": self.action_add,
            "delete": self.action_delete,
            "logout": self.logout,
        })
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        workspace = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_rowconfigure(1, weight=1)  # View absorbs vertical growth.
        workspace.grid_rowconfigure(0, weight=0)
        workspace.grid_columnconfigure(0, weight=1)

        self.header = HeaderBar(workspace, user_info, on_search=self.apply_filters)
        self.header.grid(row=0, column=0, sticky="ew")

        self.view = DashboardView(workspace)
        self.view.grid(row=1, column=0, sticky="nsew")
        self.view.apply_filters = self.apply_filters  # Filter chips hook back.

    # -- data pipeline ---------------------------------------------------------------------
    def refresh_dashboard(self):
        """Recompute every surface after any inventory mutation."""
        all_tools = self.db.fetch_all_tools()
        # Snapshot so keystroke-driven search filters the cached list instead
        # of re-hitting SQLite per keypress.
        self._all_tools_cache = all_tools

        total_count = len(all_tools)
        borrowed_count = sum(1 for t in all_tools if t["status"] == "borrowed" or t.get("borrower"))
        available_count = sum(
            1 for t in all_tools if t["status"] == "available" and not t.get("borrower")
        )
        categories = sorted({t["category"] for t in all_tools})

        self.view.update_stats(total_count, available_count, borrowed_count, len(categories))
        self.header.set_notification_count(borrowed_count)
        self.view.update_category_options(categories)
        self.view.set_footer(total_count, available_count, borrowed_count, len(categories),
                             loading=True)
        self.update_idletasks()  # Let the "Refreshing…" state paint once.
        self.apply_filters()
        self.view.update_chart(all_tools)
        self.view.set_footer(total_count, available_count, borrowed_count, len(categories))

    def apply_filters(self):
        tools = getattr(self, "_all_tools_cache", None)
        if tools is None:
            tools = self.db.fetch_all_tools()

        query = self.header.get_query()
        if query:
            tools = [t for t in tools
                     if query in t["name"].lower() or query in t["category"].lower()]

        cat = self.view.category_var.get()
        if cat != "All Categories":
            tools = [t for t in tools if t["category"] == cat]

        st = self.view.status_var.get()
        if st == "Available":
            tools = [t for t in tools if t["status"] == "available" and not t.get("borrower")]
        elif st == "Borrowed":
            tools = [t for t in tools if t["status"] == "borrowed" or t.get("borrower")]

        self.view.populate_table(tools)

    # -- dialog launchers (bound into the sidebar quick actions) ------------------------------
    def action_borrow(self):
        BorrowDialog(self, self.tools, self.user_id, self.refresh_dashboard)

    def action_return(self):
        ReturnDialog(self, self.tools, self.user_id, self.refresh_dashboard)

    def action_add(self):
        AddToolDialog(self, self.tools, self.user_id, self.refresh_dashboard)

    def action_delete(self):
        DeleteToolDialog(self, self.tools, self.user_id, self.refresh_dashboard, self.view.tree)

    # -- session lifecycle -------------------------------------------------------------------------
    def logout(self):
        logger.info("Logout requested.")
        self.destroy()
        # Release this session's WAL connection before the login window opens
        # its own DatabaseManager on the same file.
        try:
            self.db.close()
        except Exception:
            logger.warning("Failed to close DB connection on logout", exc_info=True)
        LoginApp(self.db_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    LoginApp(DB_PATH)
