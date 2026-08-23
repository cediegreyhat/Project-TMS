"""Single source of truth for the Project-LMS visual design system.

Both `project-lms.py` (the application shell) and `gui/dialogs.py` (the
reusable dialogs) import their colors and fonts from here. Keep this in
sync with any visual design changes; do NOT redefine the same constants
in either caller file.

Design language
---------------
* Deep obsidian / charcoal surfaces inspired by GitHub's dark palette.
* One high-impact accent: electric cyber-emerald, used ONLY for
  interactive or attention-worthy elements (active nav, primary
  buttons, focus rings, positive deltas).
* Pure-white primary text, muted slate-gray secondary text.
* Inter for UI type, JetBrains Mono for IDs / codes / metric numerals.
"""

# ---------------------------------------------------------------------------
# Surfaces (backgrounds, cards, borders)
# ---------------------------------------------------------------------------
COLOR_WINDOW = "#0d1117"        # App window / canvas background (deep obsidian)
COLOR_BG_DARK = COLOR_WINDOW    # Legacy alias — dialogs still import this name
COLOR_SIDEBAR = "#010409"       # Sidebar rail sits one step darker than canvas
COLOR_CARD = "#161b22"          # Card / container surface (charcoal)
COLOR_CARD_ALT = "#1c2129"      # Hover surface + alternating row tint
COLOR_CARD_BORDER = "#21262d"   # Hairline card borders
COLOR_DIVIDER = "#30363d"       # Slightly stronger divider lines

# ---------------------------------------------------------------------------
# Accent / interactive
# ---------------------------------------------------------------------------
COLOR_ACCENT = "#00ff88"        # Electric cyber-emerald (primary actions)
COLOR_ACCENT_HOVER = "#00c96f"  # Pressed / hovered accent state
COLOR_ACCENT_SOFT = "#0e4429"   # Dim emerald wash (selected rows, badges)
COLOR_INDIGO = "#6366f1"        # Secondary accent (charts, info highlights)

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
COLOR_TEXT_PRIMARY = "#ffffff"  # Headers, primary copy
COLOR_TEXT_MUTED = "#8b949e"    # Labels, secondary copy, placeholders

# ---------------------------------------------------------------------------
# Status semantics
# ---------------------------------------------------------------------------
COLOR_SUCCESS = "#3fb950"
COLOR_WARNING = "#d29922"
COLOR_DANGER = "#f85149"
COLOR_DANGER_HOVER = "#c93c37"

# Categorical palette for the donut chart (accent-first ordering).
CHART_PALETTE = [
    COLOR_ACCENT,
    COLOR_INDIGO,
    "#f78166",
    COLOR_WARNING,
    "#bc8cff",
    "#39c5cf",
    "#8b949e",
]

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
# Preferred families with graceful fallbacks. resolve_fonts() swaps these
# globals for the best family actually installed on the machine; it must be
# called once AFTER the first CTk window exists (tkfont needs a root).
FONT_CANDIDATES = ["Inter", "Segoe UI Variable Display", "SF Pro Text", "Roboto"]
MONO_CANDIDATES = ["JetBrains Mono", "Cascadia Code", "Consolas"]

FONT_FAMILY = FONT_CANDIDATES[0]
FONT_MONO = MONO_CANDIDATES[0]


def resolve_fonts():
    """Detect installed fonts and upgrade FONT_FAMILY / FONT_MONO in place.

    Safe to call repeatedly. Silently keeps defaults when the probe fails
    (e.g. no default Tk root yet) — callers always get a usable tuple.
    """
    global FONT_FAMILY, FONT_MONO
    try:
        import tkinter.font as tkfont

        families = set(tkfont.families())
        for candidate in FONT_CANDIDATES:
            if candidate in families:
                FONT_FAMILY = candidate
                break
        for candidate in MONO_CANDIDATES:
            if candidate in families:
                FONT_MONO = candidate
                break
    except Exception:
        pass


def F(size, weight=None):
    """Build a UI font tuple in the active body family."""
    return (FONT_FAMILY, size, weight) if weight else (FONT_FAMILY, size)


def FM(size=11, weight=None):
    """Build a monospace font tuple for IDs, codes, and metric numerals."""
    return (FONT_MONO, size, weight) if weight else (FONT_MONO, size)
