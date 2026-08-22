"""Single source of truth for the Project-LMS color palette.

Both `project-lms.py` (the application shell) and `gui/dialogs.py` (the
reusable dialogs) import their colors from here. Keep this in sync with
any visual design changes; do NOT redefine the same constants in either
caller file.
"""

# Backgrounds and surfaces
COLOR_BG_DARK = "#12161f"
COLOR_CARD = "#1c212d"
COLOR_CARD_BORDER = "#2e3545"

# Accent / interactive
COLOR_ACCENT = "#4f8cff"
COLOR_ACCENT_HOVER = "#3b73e0"

# Text
COLOR_TEXT_PRIMARY = "#f5f6fa"
COLOR_TEXT_MUTED = "#a0a5b5"

# Status
COLOR_SUCCESS = "#2ecc71"
COLOR_DANGER = "#e05655"
COLOR_DANGER_HOVER = "#c0392b"
