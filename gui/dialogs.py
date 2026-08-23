"""
Reusable dialog classes for Project-LMS dashboard.

Extracted from project-lms.py so the main module stays focused on app shell,
layout, and dashboard logic. Each dialog receives a parent window, the
tool service, the current user_id, and an on_success callback (typically
`refresh_dashboard`). The dialogs are self-contained CTkToplevel windows
with consistent theming and inline error display.
"""

import tkinter as tk
from tkinter import StringVar, messagebox

import customtkinter as ctk

from gui.theme import (
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_BG_DARK,
    COLOR_CARD,
    COLOR_CARD_BORDER,
    COLOR_DANGER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    F,
)
from service import ServiceError


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
            font=F(10),
            justify="left",
            anchor="w",
        )
        label.pack(ipadx=8, ipady=4)

    def hide(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class _BaseDialog:
    """Shared layout for all single-form dialogs."""

    GEOMETRY = "380x280"
    TITLE = "Dialog"

    def __init__(self, parent, tools, user_id, on_success, title=None):
        self.tools = tools
        self.user_id = user_id
        self.on_success = on_success
        self.top = ctk.CTkToplevel(parent)
        self.top.geometry(self.GEOMETRY)
        self.top.title(title or self.TITLE)
        self.top.attributes("-topmost", True)
        self.top.configure(bg=COLOR_BG_DARK)
        self._build()

    def _build(self):
        frame = ctk.CTkFrame(
            self.top,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
        )
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        self.frame = frame
        self._build_body(frame)

    def _build_body(self, frame):
        raise NotImplementedError

    def _err_label(self, frame):
        lbl = ctk.CTkLabel(
            frame, text="", font=F(11), text_color=COLOR_DANGER
        )
        lbl.pack(pady=4)
        return lbl

    def _success(self, msg):
        self.top.destroy()
        messagebox.showinfo("Success", msg)
        if self.on_success:
            self.on_success()


class BorrowDialog(_BaseDialog):
    GEOMETRY = "380x280"
    TITLE = "Borrow Tool"

    def _build_body(self, frame):
        available = self.tools.available_tools()
        if not available:
            messagebox.showwarning(
                "Borrow Tool", "No tools are currently available to borrow."
            )
            self.top.destroy()
            return

        self._tools = available
        # Prefix labels with tool IDs so duplicate names can never make the
        # dropdown resolve to the wrong row.
        tool_names = [f"#{t['tool_id']} · {t['name']}" for t in available]

        ctk.CTkLabel(
            frame,
            text="Select Tool to Borrow",
            font=F(16, "bold"),
            text_color=COLOR_ACCENT,
        ).pack(pady=(12, 16))

        self._tool_var = StringVar(value=tool_names[0])
        ctk.CTkOptionMenu(
            frame, variable=self._tool_var, values=tool_names, width=280
        ).pack(pady=8)

        err = self._err_label(frame)

        def do_borrow():
            label = self._tool_var.get()
            selected = next(
                (t for t in self._tools if f"#{t['tool_id']} · {t['name']}" == label),
                None,
            )
            if not selected:
                err.configure(text="Selected tool not found")
                return
            try:
                self.tools.borrow_tool(selected["tool_id"], self.user_id)
                self._success(f"'{selected['name']}' borrowed successfully!")
            except ServiceError as ex:
                err.configure(text=str(ex))

        ctk.CTkButton(
            frame,
            text="Confirm Borrow",
            command=do_borrow,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            width=200,
        ).pack(pady=12)


class ReturnDialog(_BaseDialog):
    GEOMETRY = "380x280"
    TITLE = "Return Tool"

    def _build_body(self, frame):
        borrowed = self.tools.my_borrowed_tools(self.user_id)
        if not borrowed:
            messagebox.showwarning(
                "Return Tool", "You have no borrowed tools to return."
            )
            self.top.destroy()
            return

        self._tools = borrowed
        # ID-prefixed labels — same duplicate-name protection as BorrowDialog.
        tool_names = [f"#{t['tool_id']} · {t['name']}" for t in borrowed]

        ctk.CTkLabel(
            frame,
            text="Select Tool to Return",
            font=F(16, "bold"),
            text_color=COLOR_ACCENT,
        ).pack(pady=(12, 16))

        self._tool_var = StringVar(value=tool_names[0])
        ctk.CTkOptionMenu(
            frame, variable=self._tool_var, values=tool_names, width=280
        ).pack(pady=8)

        err = self._err_label(frame)

        def do_return():
            label = self._tool_var.get()
            selected = next(
                (t for t in self._tools if f"#{t['tool_id']} · {t['name']}" == label),
                None,
            )
            if not selected:
                err.configure(text="Selected tool not found")
                return
            try:
                self.tools.return_tool(selected["tool_id"], self.user_id)
                self._success(f"'{selected['name']}' returned successfully!")
            except ServiceError as ex:
                err.configure(text=str(ex))

        ctk.CTkButton(
            frame,
            text="Confirm Return",
            command=do_return,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            width=200,
        ).pack(pady=12)


class AddToolDialog(_BaseDialog):
    GEOMETRY = "400x420"
    TITLE = "Add New Tool"

    def _build_body(self, frame):
        ctk.CTkLabel(
            frame,
            text="Add New Inventory Item",
            font=F(16, "bold"),
            text_color=COLOR_ACCENT,
        ).pack(pady=(10, 12))

        pad = {"fill": "x", "padx": 20, "pady": 4}
        self.e_name = ctk.CTkEntry(frame, placeholder_text="Tool Name", font=F(13))
        self.e_name.pack(**pad)
        self.e_cat = ctk.CTkEntry(frame, placeholder_text="Category", font=F(13))
        self.e_cat.pack(**pad)
        self.e_cond = ctk.CTkEntry(
            frame, placeholder_text="Condition (Good/Fair/Poor)", font=F(13)
        )
        self.e_cond.pack(**pad)
        self.e_qty = ctk.CTkEntry(frame, placeholder_text="Quantity", font=F(13))
        self.e_qty.pack(**pad)
        self.e_loc = ctk.CTkEntry(
            frame, placeholder_text="Location / Shelf", font=F(13)
        )
        self.e_loc.pack(**pad)

        err = ctk.CTkLabel(
            frame, text="", font=F(11), text_color=COLOR_DANGER
        )
        err.pack(pady=2)

        def do_add():
            try:
                self.tools.add_tool(
                    self.e_name.get(),
                    self.e_cat.get(),
                    self.e_cond.get(),
                    self.e_qty.get(),
                    self.e_loc.get(),
                    actor=self.user_id,
                )
                self._success(f"Tool '{self.e_name.get().strip()}' added!")
            except ServiceError as ex:
                err.configure(text=str(ex))

        ctk.CTkButton(
            frame,
            text="Save Tool",
            command=do_add,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            width=200,
        ).pack(pady=10)


class DeleteToolDialog:
    """Delete dialog is a confirmation flow rather than a form window."""

    def __init__(self, parent, tools, user_id, on_success, tree):
        self.tools = tools
        self.user_id = user_id
        self.on_success = on_success
        sel = tree.selection()
        if not sel:
            messagebox.showwarning(
                "Delete Tool", "Please select a tool from the table to delete."
            )
            return
        values = tree.item(sel[0], "values")
        tool_id, tool_name = values[0], values[1]
        if not tool_id:  # placeholder "No tools match…" row
            messagebox.showwarning(
                "Delete Tool", "Please select a real tool row to delete."
            )
            return
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete '{tool_name}' (ID: {tool_id})?",
        ):
            return
        try:
            tools.delete_tool(tool_id, actor=user_id)
            messagebox.showinfo("Success", f"Tool '{tool_name}' deleted.")
            if on_success:
                on_success()
        except ServiceError as ex:
            messagebox.showerror("Access Denied", str(ex))
