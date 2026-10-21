from __future__ import annotations

import marshal
import sys
import types
from pathlib import Path

# This is the UI bytecode extracted from the untouched 12:10 V2 build.
_BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
_ORIGINAL_UI = _BUNDLE_DIR / "original_v2_extract" / "app.pyc"


def _round_original_buttons(code):
    if not isinstance(code, types.CodeType):
        return code

    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            value = _round_original_buttons(value)
        constants.append(value)
    constants = tuple(constants)

    # In the original V2 RoundedButton._draw method, 7 is the only radius
    # constant. Increase that value without touching layout or text.
    if code.co_name == "_draw" and code.co_firstlineno == 296:
        constants = tuple(14 if value == 7 else value for value in constants)

    return code.replace(co_consts=constants)


def _draw_rounded_checkbox(self):
    self.delete("all")
    selected = bool(self.variable.get())
    background = self.master.cget("bg")
    # Tk Canvas widgets retain their creation-time background unless updated;
    # keep the canvas and its drawn square in sync when switching themes.
    self.configure(bg=background)
    scale = self.size / 16
    try:
        red, green, blue = (int(background[index:index + 2], 16) for index in (1, 3, 5))
        dark = (red * 299 + green * 587 + blue * 114) / 1000 < 128
    except (ValueError, IndexError):
        dark = False
    accent = "#79aef2" if dark else "#1685e8"
    border = accent if selected else ("#71839b" if dark else "#9aa9bc")
    self.create_rectangle(
        2 * scale, 2 * scale, self.size - 2 * scale, self.size - 2 * scale,
        fill=background, outline=border, width=1.3 * scale,
    )
    if selected:
        # A compact, crisp checkmark; layered brush strokes looked stretched
        # at this small checkbox size.
        self.create_line(
            4.3 * scale, 8.1 * scale, 6.7 * scale, 10.5 * scale, 12.0 * scale, 5.0 * scale,
            fill=accent, width=2.0 * scale, capstyle="round", joinstyle="round",
        )


def _init_larger_checkbox(self, master, variable, command, size=20):
    return _ORIGINAL_CHECKBOX_INIT(self, master, variable, command, size)


def _draw_button_fast_and_scaled(self, *args):
    # Keep the Canvas exterior identical to its current parent on every draw,
    # avoiding rectangular artifacts around rounded corners across light/dark themes.
    if getattr(self, "text", "") in ("RO", "UK"):
        language_row = self.master
        try:
            language_row.configure(bg=language_row.master.cget("bg"))
        except Exception:
            pass
    try:
        self.configure(bg=self.master.cget("bg"))
    except Exception:
        pass

    self.delete("all")
    width = max(self.winfo_width(), self.default_width)
    height = max(self.winfo_height(), self.default_height)
    margin = 1 if self.hovered else 0
    radius = min(14, max((height - 2 * margin) // 2, 1))
    fill = self.hover_fill if self.hovered else self.fill

    self._draw_rounded_shape(
        margin,
        margin,
        width - margin,
        height - margin,
        radius,
        "#6ca5ff" if self.hovered else fill,
    )
    if self.hovered:
        self._draw_rounded_shape(
            margin + 1,
            margin + 1,
            width - margin - 1,
            height - margin - 1,
            max(radius - 1, 1),
            fill,
        )

    # Dynamic button text font scaling based on button size
    btn_text = getattr(self, "text", "")
    if btn_text in ("RO", "UK"):
        font_size = 9
    elif height <= 24:
        # Browser buttons & compact utility buttons
        font_size = 8 if len(btn_text) > 7 else 9
    else:
        font_size = 10

    self.create_text(
        width / 2,
        height / 2,
        text=btn_text,
        fill=self.foreground,
        font=("Segoe UI", font_size, "bold"),
        width=max(width - 12, 1),
        justify="center",
    )


def _set_rounded_button_style(self, fill, foreground):
    self.fill = fill
    self.foreground = foreground
    self.hover_fill = self._mix(fill, "#ffffff", 0.18)
    self.configure(bg=self.master.cget("bg"))
    self._draw()


def _enhance_app(application):
    import tkinter.font as tkfont

    # 1. Clean exit: ensure no background loops/threads stay active on close
    def on_app_close():
        try:
            application.destroy()
        except Exception:
            pass
        sys.exit(0)

    application.protocol("WM_DELETE_WINDOW", on_app_close)

    # 2. Fix the layout so Vivaldi and all panels are fully visible without clipping
    try:
        if hasattr(application, "utility_panel"):
            application.utility_panel.pack_propagate(True)
            application.utility_panel.configure(width=280)
        if hasattr(application, "action_canvas"):
            application.action_canvas.configure(height=420)
        if hasattr(application, "browser_grid"):
            application.browser_grid.grid_columnconfigure((0, 1), weight=1)
    except Exception:
        pass

    if hasattr(application, "browser_buttons"):
        for btn in application.browser_buttons:
            if getattr(btn, "text", "") == "Vivaldi":
                btn.configure(height=26)
                btn.default_height = 26
                # Span both columns so Vivaldi is clean, centered and 100% visible
                btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=3, pady=(3, 2))
                btn._draw()
            else:
                btn.configure(height=24)
                btn.default_height = 24
                btn._draw()

    # 3. Dynamic font scaling across the ENTIRE PAGE
    # Store initial font specifications for all labels/widgets in the app
    orig_fonts = {}

    def register_fonts(widget):
        try:
            raw = widget.cget("font")
            if raw:
                font_obj = tkfont.Font(font=raw)
                orig_fonts[widget] = {
                    "family": font_obj.cget("family"),
                    "size": abs(font_obj.cget("size")),
                    "weight": font_obj.cget("weight"),
                    "slant": font_obj.cget("slant"),
                }
        except Exception:
            pass
        for child in widget.winfo_children():
            register_fonts(child)

    register_fonts(application)

    last_factor = [None]

    def on_window_resize(event):
        if event.widget != application:
            return
        w, h = event.width, event.height
        if w < 100 or h < 100:
            return

        # Calculate a smooth scaling ratio relative to base window size (1100x720)
        # Bounded between 0.85 (for small resolutions) and 1.35 (for 2K/4K displays)
        scale_w = w / 1100.0
        scale_h = h / 720.0
        factor = round(max(0.85, min(1.35, (scale_w * 0.6 + scale_h * 0.4))), 2)

        if last_factor[0] == factor:
            return
        last_factor[0] = factor

        # Re-register any dynamically added widgets (e.g. action rows, scans)
        register_fonts(application)

        for widget, props in list(orig_fonts.items()):
            try:
                new_size = max(7, round(props["size"] * factor))
                widget.configure(font=(props["family"], new_size, props["weight"]))
            except Exception:
                pass

        # Also scale standard Tk named fonts
        try:
            base_size = round(9 * factor)
            for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
                tkfont.nametofont(font_name).configure(size=base_size)
            tkfont.nametofont("TkHeadingFont").configure(size=base_size + 2)
            tkfont.nametofont("TkCaptionFont").configure(size=max(base_size - 1, 7))
        except Exception:
            pass

    application.bind("<Configure>", on_window_resize, add="+")


def main():
    code = marshal.loads(_ORIGINAL_UI.read_bytes())
    namespace = {
        "__name__": "original_v2",
        # The original UI resolves its icon files relative to __file__. Point
        # it at PyInstaller's extraction directory, where bundled assets live.
        "__file__": str(_BUNDLE_DIR / "app.py"),
        "__package__": None,
        "__cached__": None,
    }
    exec(_round_original_buttons(code), namespace, namespace)
    global _ORIGINAL_BUTTON_DRAW
    _ORIGINAL_BUTTON_DRAW = namespace["RoundedButton"]._draw
    namespace["RoundedButton"]._draw = _draw_button_fast_and_scaled
    namespace["RoundedButton"].set_style = _set_rounded_button_style
    global _ORIGINAL_CHECKBOX_INIT
    _ORIGINAL_CHECKBOX_INIT = namespace["CheckBoxButton"].__init__
    namespace["CheckBoxButton"].__init__ = _init_larger_checkbox
    namespace["CheckBoxButton"]._draw = _draw_rounded_checkbox
    application = namespace["WinTweakerApp"]()
    _enhance_app(application)
    application.mainloop()


if __name__ == "__main__":
    main()
