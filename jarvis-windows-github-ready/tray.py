import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

TRAY_BG_GREY = (92, 96, 104, 255)


def _make_icon():
    size = 64
    img = Image.new("RGBA", (size, size), TRAY_BG_GREY)
    draw = ImageDraw.Draw(img)

    for y in range(size):
        mix = y / max(1, size - 1)
        r = int(74 + 34 * mix)
        g = int(78 + 34 * mix)
        b = int(86 + 34 * mix)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    draw.ellipse([4, 4, size - 4, size - 4], outline=(0, 232, 208, 255), width=4)
    draw.arc([10, 10, size - 10, size - 10], 205, 335, fill=(123, 97, 255, 255), width=5)
    draw.arc([10, 10, size - 10, size - 10], 25, 150, fill=(255, 184, 76, 255), width=4)
    draw.ellipse([20, 20, size - 20, size - 20], fill=(0, 232, 208, 210))
    draw.ellipse([27, 27, size - 27, size - 27], fill=(246, 255, 252, 245))
    draw.ellipse([14, 12, 24, 22], fill=(255, 255, 255, 95))
    return img


def _with_grey_background(icon: Image.Image) -> Image.Image:
    icon = icon.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", icon.size, TRAY_BG_GREY)
    bg.alpha_composite(icon)
    return bg


def _load_icon():
    candidates = [
        Path(__file__).parent / "assets" / "icons" / "jarvis_tray.png",
        Path(__file__).parent / "assets" / "icons" / "jarvis.png",
        Path(__file__).parent / "assets" / "icons" / "icon.png",
        Path(__file__).parent / "assets" / "icon.ico",
        Path(__file__).parent / "assets" / "icon.png",
        Path(__file__).parent / "icon.ico",
        Path(__file__).parent / "icon.png",
    ]
    for p in candidates:
        if p.exists():
            try:
                return _with_grey_background(Image.open(p))
            except Exception:
                pass
    return _make_icon()


class TrayManager:
    def __init__(self, show_fn, quit_fn):
        self._show_fn = show_fn
        self._quit_fn = quit_fn
        self._icon = None
        self._hidden = False
        self._started = False
        self._muted = False
        self._paused = False

        self.on_mute_toggle = None
        self.on_pause_toggle = None

    def _status_text(self):
        if self._paused:
            return "🟡 Durum: Duraklatıldı"
        if self._muted:
            return "🔵 Durum: Dinliyor, ses kapalı"
        return "🟢 Durum: Dinliyor"

    def _title_text(self):
        if self._paused:
            return "J.A.R.V.I.S — Duraklatıldı"
        if self._muted:
            return "J.A.R.V.I.S — Sessiz"
        return "J.A.R.V.I.S — Dinliyor"

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(lambda item: self._status_text(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✨ JARVIS'i Aç", self._on_open, default=True),
            pystray.MenuItem(
                lambda item: "🔊 Sesi Aç" if self._muted else "🔇 Sesi Kapat",
                self._on_mute_toggle,
            ),
            pystray.MenuItem(
                lambda item: "▶ Devam Et" if self._paused else "⏸ Duraklat",
                self._on_pause_toggle,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙ Ayarlar", lambda i, item: None, enabled=False),
            pystray.MenuItem("📊 Sistem Durumu", lambda i, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ Tamamen Kapat", self._on_quit),
        )

    def _refresh(self):
        if self._icon:
            self._icon.title = self._title_text()
            self._icon.update_menu()

    def start(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._run, daemon=True, name="TrayManager").start()

    def _run(self):
        self._icon = pystray.Icon(
            name="JARVIS",
            icon=_load_icon(),
            title=self._title_text(),
            menu=self._build_menu(),
        )
        self._icon.run()

    def hide_to_tray(self):
        self._hidden = True
        if self._icon:
            self._icon.title = self._title_text()
            self._icon.visible = True

    def show_from_tray(self):
        if not self._hidden:
            return
        self._hidden = False
        if self._icon:
            self._icon.title = "J.A.R.V.I.S — Aktif"
        self._show_fn()

    def set_muted(self, muted: bool):
        self._muted = muted
        self._refresh()

    def set_paused(self, paused: bool):
        self._paused = paused
        self._refresh()

    def is_hidden(self):
        return self._hidden

    def _on_open(self, icon, item):
        self.show_from_tray()

    def _on_mute_toggle(self, icon, item):
        self._muted = not self._muted
        self._refresh()
        if self.on_mute_toggle:
            threading.Thread(target=self.on_mute_toggle, daemon=True).start()

    def _on_pause_toggle(self, icon, item):
        self._paused = not self._paused
        self._refresh()
        if self.on_pause_toggle:
            threading.Thread(target=self.on_pause_toggle, daemon=True).start()

    def _on_quit(self, icon, item):
        icon.stop()
        self._quit_fn()
