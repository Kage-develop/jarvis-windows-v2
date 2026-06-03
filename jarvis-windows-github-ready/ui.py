"""
JARVIS Windows — Modern UI v5.0
Next Gen · Glassmorphism · Particle System · Sübhan Sultanli
"""

import os, time, math, random, threading, ctypes
from pathlib import Path
from collections import deque

# ── PYQT6 IMPORTLARI ────────────────────────────────────────────────────────
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QFrame, QLabel, QLineEdit, QPushButton, QScrollArea,
        QSizePolicy, QTextEdit, QStackedWidget, QGraphicsOpacityEffect,
        QGraphicsDropShadowEffect, QMenu
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPoint, QPointF, QRect, QRectF, QSize,
        pyqtSignal, QThread, QPropertyAnimation, QEasingCurve,
        QParallelAnimationGroup, QEvent
    )
    from PyQt6.QtGui import (
        QPainter, QColor, QPen, QBrush, QFont, QFontDatabase,
        QLinearGradient, QRadialGradient, QConicalGradient,
        QPolygonF, QPainterPath, QIcon, QPixmap, QCursor,
        QKeyEvent, QMouseEvent, QPaintEvent, QResizeEvent, QAction, QActionGroup, QRegion
    )
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    print("[WARN] PyQt6 bulunamadı. Lütfen: pip install PyQt6")

# ── YARDIMCI IMPORTLAR ────────────────────────────────────────────────────
try:
    from app_config import has_gemini_api_key, load_app_config, save_app_config
    from tray import TrayManager
except ImportError:
    # Eğer modüller yoksa dummy fonksiyonlar
    def has_gemini_api_key(): return False
    def load_app_config(): return {}
    def save_app_config(cfg): pass
    class TrayManager:
        def __init__(self, **kw): pass
        def start(self): pass
        def set_muted(self, v): pass
        def set_paused(self, v): pass
        def hide_to_tray(self): pass
        def is_hidden(self): return False

try:
    import psutil
except ImportError:
    psutil = None

BASE_DIR = Path(__file__).resolve().parent

SYSTEM_NAME   = "J.A.R.V.I.S"
MODEL_BADGE   = "VOICE CORE · WINDOWS"
AUTHOR_NAME   = "Sübhan Sultanli"

# ── RENK PALETİ ─────────────────────────────────────────────────────────────
class Colors:
    BG_PRIMARY    = QColor(2, 4, 8)
    BG_SECONDARY  = QColor(5, 10, 18)
    BG_TERTIARY   = QColor(8, 16, 28)
    BG_CARD       = QColor(10, 20, 32)
    BG_CARD_HOVER = QColor(14, 26, 42)
    
    CYAN       = QColor(0, 240, 255)
    CYAN_DIM   = QColor(0, 160, 168)
    CYAN_GLOW  = QColor(0, 240, 255, 100)
    
    BLUE       = QColor(59, 130, 246)
    BLUE_DIM   = QColor(29, 78, 216)
    BLUE_GLOW  = QColor(59, 130, 246, 90)
    
    PURPLE     = QColor(139, 92, 246)
    PURPLE_DIM = QColor(109, 40, 217)
    PURPLE_GLOW= QColor(139, 92, 246, 90)
    
    GOLD       = QColor(251, 191, 36)
    GOLD_DIM   = QColor(217, 119, 6)
    GOLD_GLOW  = QColor(251, 191, 36, 90)
    
    GREEN      = QColor(16, 185, 129)
    GREEN_DIM  = QColor(5, 150, 105)
    GREEN_GLOW = QColor(16, 185, 129, 90)
    
    RED        = QColor(239, 68, 68)
    RED_DIM    = QColor(220, 38, 38)
    RED_GLOW   = QColor(239, 68, 68, 90)
    
    ORANGE     = QColor(249, 115, 22)
    
    TEXT_PRIMARY   = QColor(226, 232, 240)
    TEXT_SECONDARY = QColor(148, 163, 184)
    TEXT_MUTED     = QColor(71, 85, 105)
    TEXT_DIM       = QColor(51, 65, 85)
    
    BORDER       = QColor(0, 240, 255, 20)
    BORDER_GLOW  = QColor(0, 240, 255, 40)
    
    @staticmethod
    def with_alpha(color: QColor, alpha: int) -> QColor:
        return QColor(color.red(), color.green(), color.blue(), alpha)


# ── PARTİKÜL SİSTEMİ ────────────────────────────────────────────────────────
class Particle:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = (random.random() - 0.5) * 0.4
        self.vy = (random.random() - 0.5) * 0.4
        self.size = random.uniform(0.8, 2.5)
        self.alpha = random.uniform(0.1, 0.6)
        self.color_idx = random.choice([0, 1])
        self.pulse_phase = random.uniform(0, math.tau)
        
    def update(self, w, h, mouse_x, mouse_y):
        dx = mouse_x - self.x
        dy = mouse_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 200 and dist > 0:
            force = (200 - dist) / 200 * 0.02
            self.vx += (dx / dist) * force
            self.vy += (dy / dist) * force
        
        self.x += self.vx
        self.y += self.vy
        
        if self.x < -50: self.x = w + 50
        if self.x > w + 50: self.x = -50
        if self.y < -50: self.y = h + 50
        if self.y > h + 50: self.y = -50
        
        self.vx *= 0.999
        self.vy *= 0.999


class HexagonGrid:
    def __init__(self, w, h):
        self.hexagons = []
        size = 45
        hex_h = size * math.sqrt(3)
        for row in range(int(h / hex_h) + 3):
            for col in range(int(w / (size * 1.5)) + 3):
                x = col * size * 1.5 + (row % 2) * size * 0.75
                y = row * hex_h * 0.5
                self.hexagons.append({
                    'x': x, 'y': y, 'size': size,
                    'base_alpha': random.uniform(0.02, 0.08),
                    'phase': random.uniform(0, math.tau)
                })


# ── ARKA PLAN WIDGET ──────────────────────────────────────────────────────
class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.hex_grid = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.tick = 0
        self.setMouseTracking(False)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update)
        
    def init_system(self, w, h):
        self.particles = []
        self.hex_grid = None
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() > 100 and self.height() > 100:
            self.init_system(self.width(), self.height())
            
    def mouseMoveEvent(self, event):
        self.mouse_x = event.pos().x()
        self.mouse_y = event.pos().y()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(self.rect(), QColor(2, 4, 8, 210))
        
        grad1 = QRadialGradient(QPointF(w*0.2, h*0.5), w*0.6)
        grad1.setColorAt(0, QColor(0, 240, 255, 8))
        grad1.setColorAt(1, QColor(0, 240, 255, 0))
        painter.fillRect(self.rect(), grad1)
        
        grad2 = QRadialGradient(QPointF(w*0.8, h*0.5), w*0.6)
        grad2.setColorAt(0, QColor(139, 92, 246, 6))
        grad2.setColorAt(1, QColor(139, 92, 246, 0))
        painter.fillRect(self.rect(), grad2)
        
        if self.hex_grid:
            pen = QPen(Colors.CYAN)
            pen.setWidthF(0.5)
            for hex_item in self.hex_grid.hexagons:
                dist = math.sqrt((hex_item['x'] - self.mouse_x)**2 + 
                               (hex_item['y'] - self.mouse_y)**2)
                glow = max(0, 1 - dist / 180) * 0.25
                alpha = int((hex_item['base_alpha'] + glow) * 255)
                alpha = min(255, max(0, alpha))
                pen.setColor(Colors.with_alpha(Colors.CYAN, alpha))
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
                points = []
                for i in range(6):
                    angle = (math.pi / 3) * i - math.pi / 6
                    hx = hex_item['x'] + hex_item['size'] * math.cos(angle)
                    hy = hex_item['y'] + hex_item['size'] * math.sin(angle)
                    points.append(QPointF(hx, hy))
                painter.drawPolygon(QPolygonF(points))
        
        for p in self.particles:
            p.update(w, h, self.mouse_x, self.mouse_y)
            pulse = math.sin(self.tick * 0.02 + p.pulse_phase) * 0.3 + 0.7
            alpha = int(p.alpha * pulse * 255)
            
            if p.color_idx == 0:
                color = Colors.with_alpha(Colors.CYAN, alpha)
                glow_color = Colors.with_alpha(Colors.CYAN, int(alpha * 0.1))
            else:
                color = Colors.with_alpha(Colors.PURPLE, alpha)
                glow_color = Colors.with_alpha(Colors.PURPLE, int(alpha * 0.1))
            
            painter.setBrush(glow_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p.x, p.y), p.size * 3, p.size * 3)
            
            painter.setBrush(color)
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
        
        pen = QPen(Colors.with_alpha(Colors.CYAN, 15))
        pen.setWidthF(0.5)
        painter.setPen(pen)
        for i, p1 in enumerate(self.particles):
            if i % 2:
                continue
            for p2 in self.particles[i+1::3]:
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 140:
                    alpha = int(15 * (1 - dist / 140))
                    pen.setColor(Colors.with_alpha(Colors.CYAN, alpha))
                    painter.setPen(pen)
                    painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))
        
        self.tick += 1


# ── ORB WIDGET ──────────────────────────────────────────────────────────────
class OrbWidget(QWidget):
    stateChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.tick = 0
        self.orb_state = "LISTENING"
        self.is_speaking = False
        self.is_user_speaking = False
        self.is_paused = False
        self.scale = 1.0
        self.target_scale = 1.0
        self.halo_alpha = 60
        self.target_halo = 60
        
        self.orb_particles = []
        self.ring_angles = [0.0, 45.0, 90.0, 200.0]
        self.pulse_rings = []
        self._init_orb_particles()
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate)
        self.anim_timer.start(110)
        
    def _init_orb_particles(self):
        self.orb_particles = []
        for _ in range(18):
            self.orb_particles.append({
                'angle': random.uniform(0, math.tau),
                'orbit': random.uniform(0.08, 0.95),
                'speed': random.uniform(-0.025, 0.025),
                'size': random.uniform(0.8, 2.8),
                'phase': random.uniform(0, math.tau),
                'wobble': random.uniform(0.008, 0.035),
                'depth': random.uniform(0.3, 1.0)
            })
    
    def set_state(self, state):
        self.orb_state = state
        self.is_speaking = (state == "SPEAKING")
        self.stateChanged.emit(state)
        self.update()
        
    def _animate(self):
        self.tick += 1
        t = self.tick
        
        if self.is_paused:
            self.target_scale = random.uniform(0.58, 0.64)
            self.target_halo = random.uniform(5, 12)
        elif self.is_speaking:
            self.target_scale = random.uniform(0.98, 1.12)
            self.target_halo = random.uniform(180, 260)
        elif self.is_user_speaking:
            self.target_scale = random.uniform(0.88, 0.98)
            self.target_halo = random.uniform(120, 180)
        elif self.orb_state in ("THINKING", "INITIALISING"):
            self.target_scale = random.uniform(0.80, 0.90)
            self.target_halo = random.uniform(100, 150)
        else:
            self.target_scale = random.uniform(0.74, 0.82)
            self.target_halo = random.uniform(35, 60)
        
        sp = 0.34 if self.is_speaking else 0.18
        self.scale += (self.target_scale - self.scale) * sp
        self.halo_alpha += (self.target_halo - self.halo_alpha) * sp
        
        speeds = [0,0,0,0] if self.is_paused else (
            [1.8, -1.2, 2.6, -0.8] if self.is_speaking else 
            [0.5, -0.3, 0.8, -0.25]
        )
        for i, spd in enumerate(speeds):
            self.ring_angles[i] = (self.ring_angles[i] + spd) % 360
        
        pspd = 4.0 if self.is_speaking else 1.6
        limit = min(self.width(), self.height()) * 0.35
        self.pulse_rings = [r + pspd for r in self.pulse_rings if r + pspd < limit]
        if len(self.pulse_rings) < 3 and random.random() < (0.06 if self.is_speaking else 0.018):
            self.pulse_rings.append(0.0)
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        base_r = min(w, h) * 0.35
        radius = int(base_r * self.scale)
        
        state_colors = {
            "LISTENING": Colors.CYAN,
            "SPEAKING": Colors.BLUE,
            "THINKING": Colors.GOLD,
            "INITIALISING": Colors.ORANGE,
            "ERROR": Colors.RED,
            "PAUSED": Colors.TEXT_MUTED,
            "MUTED": Colors.RED
        }
        color = state_colors.get(self.orb_state, Colors.CYAN)
        
        if self.orb_state in ("THINKING", "INITIALISING"):
            accent = Colors.GOLD
        elif self.is_speaking:
            accent = Colors.BLUE
        elif self.is_user_speaking:
            accent = Colors.with_alpha(Colors.BLUE, 200)
        else:
            accent = Colors.with_alpha(Colors.CYAN, 180)
        
        activity = (
            0.10 if self.is_paused else
            1.00 if self.is_speaking else
            0.78 if self.is_user_speaking else
            0.62 if self.orb_state in ("THINKING", "INITIALISING") else
            0.28
        )
        
        if not self.is_paused:
            for i in range(6, 0, -1):
                frac = i / 6
                r = int(radius * (1.02 + 0.06 * frac))
                alpha = int(self.halo_alpha * 0.1 * frac)
                pen = QPen(Colors.with_alpha(color, alpha))
                pen.setWidthF(2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), r, r)
        
        for frac, width, alpha_mult in (
            (1.00, 2, 0.40), (0.88, 2, 0.28), (0.72, 1, 0.20),
            (0.58, 1, 0.14), (0.44, 1, 0.10)
        ):
            r = int(radius * frac)
            alpha = int(self.halo_alpha * alpha_mult * (0.35 if self.is_paused else 1.0))
            pen = QPen(Colors.with_alpha(color, alpha))
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.drawEllipse(QPointF(cx, cy), r, r)
        
        for pr in self.pulse_rings:
            alpha = max(0, int(140 * (1.0 - pr / (radius * 0.75))))
            rr = int(pr + radius * 0.95)
            pen = QPen(Colors.with_alpha(color, alpha))
            pen.setWidthF(1)
            painter.setPen(pen)
            painter.drawEllipse(QPointF(cx, cy), rr, rr)
        
        arc_configs = [
            (self.ring_angles[0], 50 if self.is_speaking else 32, 3, False),
            ((self.ring_angles[0] + 150) % 360, 24, 2, True),
            ((self.ring_angles[2] + 30) % 360, 60 if self.is_user_speaking else 36, 3, False),
            ((self.ring_angles[2] + 210) % 360, 16, 2, True),
        ]
        
        for start, extent, width, is_accent in arc_configs:
            rr = int(radius * 0.94) if width == 3 else int(radius * 0.78)
            if is_accent and not self.is_paused:
                arc_color = Colors.with_alpha(accent, int(100 + 70 * activity))
            else:
                arc_color = Colors.with_alpha(color, int(self.halo_alpha * (1.1 if width == 3 else 0.65)))
            pen = QPen(arc_color)
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.drawArc(
                int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2),
                int(start * 16), int(extent * 16)
            )
        
        field_limit = int(radius * 0.82 * (0.75 if self.is_paused else 
                          1.35 if self.is_speaking else 
                          1.15 if self.is_user_speaking else 1.0))
        
        for idx, p in enumerate(self.orb_particles):
            speed_mult = 0.08 if self.is_paused else (
                3.0 if self.is_speaking else 
                1.9 if self.is_user_speaking else 1.0
            )
            angle = p['angle'] + self.tick * p['speed'] * speed_mult
            wobble = 1.0 + (0.28 if self.is_speaking else 0.16) * math.sin(self.tick * p['wobble'] + p['phase'])
            orbit = field_limit * p['orbit'] * wobble
            depth = 0.5 + 0.5 * math.sin(angle * 2.0 + self.tick * 0.012 + p['phase'])
            y_squash = 0.62 + depth * 0.38
            drift = (7.0 if self.is_speaking else 4.5 if self.is_user_speaking else 3.5) * p['depth']
            
            x = cx + math.cos(angle) * orbit + math.sin(self.tick * 0.011 + p['phase']) * drift
            y = cy + math.sin(angle) * orbit * y_squash + math.cos(self.tick * 0.010 + p['phase']) * drift
            
            base_alpha = int((16 + 140 * p['depth']) * (0.22 + activity * 0.88) * (0.45 + depth * 0.75))
            if self.is_paused:
                base_alpha = int(base_alpha * 0.38)
            
            if idx % 10 == 0 and not self.is_paused:
                pcolor = Colors.with_alpha(accent, min(255, base_alpha + 22))
            elif self.is_user_speaking and idx % 6 == 0:
                pcolor = Colors.with_alpha(Colors.BLUE, min(255, base_alpha + 18))
            else:
                pcolor = Colors.with_alpha(color, base_alpha)
            
            psize = p['size'] * (0.70 if self.is_paused else 0.88 + depth * 0.62 + 0.28 * activity * p['depth'])
            
            painter.setBrush(pcolor)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), psize, psize)
        
        void_r = max(2, int(radius * 0.12 * (0.6 if self.is_paused else 0.35)))
        painter.setBrush(Colors.BG_PRIMARY)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), void_r, void_r)
        
        glow_r = int(void_r * 2.5)
        grad = QRadialGradient(QPointF(cx, cy), glow_r)
        grad.setColorAt(0, Colors.with_alpha(color, 60))
        grad.setColorAt(1, Colors.with_alpha(color, 0))
        painter.setBrush(grad)
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)


# ── MODERN KART WIDGET ──────────────────────────────────────────────────────
class VoiceWaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.18
        self.target_level = 0.18
        self.active = False
        self.tick = 0
        self.setFixedHeight(70)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(300)

    def set_active(self, active):
        self.active = bool(active)
        self.target_level = 0.86 if self.active else 0.18
        self.timer.start(90 if self.active else 300)

    def _animate(self):
        self.tick += 1
        if self.active:
            self.target_level = random.uniform(0.48, 0.98)
        else:
            self.target_level = 0.16 + 0.04 * math.sin(self.tick * 0.08)
        self.level += (self.target_level - self.level) * 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid = h / 2
        bars = 16
        gap = 4
        bar_w = max(3, (w - gap * (bars - 1)) / bars)
        color = Colors.GREEN if self.active else Colors.CYAN

        for i in range(bars):
            phase = self.tick * (0.22 if self.active else 0.06) + i * 0.72
            wave = 0.35 + 0.65 * abs(math.sin(phase))
            amp = 8 + (h * 0.38) * self.level * wave
            x = i * (bar_w + gap)
            alpha = 210 if self.active else 88
            painter.setBrush(Colors.with_alpha(color, alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, mid - amp / 2, bar_w, amp), 2, 2)

        pen = QPen(Colors.with_alpha(color, 42 if self.active else 22))
        pen.setWidthF(1)
        painter.setPen(pen)
        painter.drawLine(QPointF(0, mid), QPointF(w, mid))


class ModernCard(QFrame):
    def __init__(self, title, accent_color=None, parent=None):
        super().__init__(parent)
        self.card_title = title
        self.accent = accent_color or Colors.CYAN
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.setStyleSheet(f"""
            ModernCard {{
                background-color: {Colors.BG_CARD.name()};
                border: 1px solid rgba(0, 240, 255, 20);
                border-radius: 8px;
            }}
            ModernCard:hover {{
                border: 1px solid rgba(0, 240, 255, 60);
                background-color: {Colors.BG_CARD_HOVER.name()};
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)
        
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED.name()};
            font-family: 'JetBrains Mono';
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
        """)
        header.addWidget(title_label)
        header.addStretch()
        self.layout.addLayout(header)
        
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {self.accent.name()}, stop:1 transparent);
            border-radius: 1px;
        """)
        line.setMaximumWidth(120)
        self.layout.addWidget(line)
        
        self.content = QVBoxLayout()
        self.content.setSpacing(8)
        self.layout.addLayout(self.content)
        self.layout.addStretch()
        
    def add_widget(self, widget):
        self.content.addWidget(widget)
        
    def add_layout(self, layout):
        self.content.addLayout(layout)


# ── STAT BAR WIDGET ─────────────────────────────────────────────────────────
class StatBar(QWidget):
    def __init__(self, label, color, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.bar_color = color
        self._value = 0
        self.setMinimumHeight(40)
        
    def set_value(self, value):
        self._value = max(0, min(100, value))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        
        painter.setPen(Colors.TEXT_MUTED)
        font = QFont("JetBrains Mono", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, 12, self.label_text)
        
        val_text = f"{self._value:.0f}%"
        painter.setPen(self.bar_color)
        painter.drawText(w - 40, 12, val_text)
        
        bar_y = 20
        bar_h = 4
        painter.setBrush(Colors.BG_TERTIARY)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, bar_y, w, bar_h, 2, 2)
        
        fill_w = max(1, int(w * self._value / 100))
        gradient = QLinearGradient(0, bar_y, fill_w, bar_y)
        gradient.setColorAt(0, self.bar_color)
        gradient.setColorAt(1, Colors.with_alpha(self.bar_color, 150))
        painter.setBrush(gradient)
        painter.drawRoundedRect(0, bar_y, fill_w, bar_h, 2, 2)
        
        if fill_w > 20:
            shine = QLinearGradient(fill_w - 20, bar_y, fill_w, bar_y)
            shine.setColorAt(0, QColor(255, 255, 255, 0))
            shine.setColorAt(1, QColor(255, 255, 255, 60))
            painter.setBrush(shine)
            painter.drawRoundedRect(fill_w - 20, bar_y, 20, bar_h, 2, 2)


# ── ANA PENCERE ─────────────────────────────────────────────────────────────
class RadarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.setFixedSize(108, 108)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(80)

    def _tick(self):
        self.angle = (self.angle + 3) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.42

        painter.setBrush(Qt.BrushStyle.NoBrush)
        for idx, alpha in enumerate((70, 42, 24)):
            pen = QPen(Colors.with_alpha(Colors.CYAN, alpha))
            pen.setWidthF(1)
            painter.setPen(pen)
            rr = r * (1 - idx * 0.28)
            painter.drawEllipse(QPointF(cx, cy), rr, rr)

        pen = QPen(Colors.with_alpha(Colors.CYAN, 38))
        pen.setWidthF(1)
        painter.setPen(pen)
        painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        painter.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))

        rad = math.radians(self.angle)
        end = QPointF(cx + math.cos(rad) * r, cy + math.sin(rad) * r)
        sweep = QPen(Colors.with_alpha(Colors.GREEN, 180))
        sweep.setWidthF(2)
        painter.setPen(sweep)
        painter.drawLine(QPointF(cx, cy), end)

        painter.setBrush(Colors.with_alpha(Colors.GREEN, 210))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx + r * 0.34, cy - r * 0.18), 2.5, 2.5)
        painter.drawEllipse(QPointF(cx - r * 0.22, cy + r * 0.28), 1.8, 1.8)


class JarvisModernWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S — Next Gen")
        self.setMinimumSize(940, 620)
        self.resize(1020, 660)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.94)
        self._drag_position = None
        self._window_radius = 22
        self._allow_close = False
        self._widget_mode = False
        
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.central.setObjectName("jarvisRoot")
        self.central.setStyleSheet(f"""
            QWidget#jarvisRoot {{
                background: rgba(2, 4, 8, 218);
                border: 1px solid rgba(0, 240, 255, 30);
                border-radius: {self._window_radius}px;
            }}
        """)
        
        main_layout = QGridLayout(self.central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.bg_widget = BackgroundWidget(self.central)
        self.bg_widget.setGeometry(0, 0, 1920, 1080)
        
        self.content = QWidget(self.central)
        self.content.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        content_layout = QGridLayout(self.content)
        self.content_layout = content_layout
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.header = self._create_header()
        content_layout.addWidget(self.header, 0, 0, 1, 3)
        
        self.left_panel = self._create_left_panel()
        content_layout.addWidget(self.left_panel, 1, 0)
        
        self.center_panel = self._create_center_panel()
        content_layout.addWidget(self.center_panel, 1, 1)
        
        self.right_panel = self._create_right_panel()
        content_layout.addWidget(self.right_panel, 1, 2)
        
        self.footer = self._create_footer()
        content_layout.addWidget(self.footer, 2, 0, 1, 3)
        
        content_layout.setColumnStretch(0, 0)
        content_layout.setColumnStretch(1, 1)
        content_layout.setColumnStretch(2, 0)
        content_layout.setRowStretch(1, 1)
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(1000)

        self.voice_decay_timer = QTimer(self)
        self.voice_decay_timer.timeout.connect(self._update_voice_decay)
        self.voice_decay_timer.start(250)

        self.apps_timer = QTimer(self)
        self.apps_timer.timeout.connect(self._update_active_apps)
        self.apps_timer.start(10000)
        self._last_sys_update = 0.0

        self._update_ui()
        self._update_active_apps()
        
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_stop_command = None
        self.on_voice_change = None
        self.on_effects_state_change = None
        
        self.speaking = False
        self.user_speaking = False
        self.muted = False
        self.paused = False
        self._jarvis_state = "INITIALISING"
        self._user_speaking_until = 0.0
        self._started_at = time.time()
        QTimer.singleShot(0, lambda: self._set_widget_mode(False))
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_widget.setGeometry(0, 0, self.width(), self.height())
        self.content.setGeometry(0, 0, self.width(), self.height())
        self._update_window_mask()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and not self.isMinimized():
            self._fade_to(0.94, 160)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._set_animation_timers(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._set_animation_timers(True)

    def _set_animation_timers(self, enabled):
        timers = [
            getattr(self.bg_widget, "anim_timer", None),
            getattr(getattr(self, "orb", None), "anim_timer", None),
            getattr(getattr(self, "voice_wave", None), "timer", None),
            getattr(self, "update_timer", None),
            getattr(self, "voice_decay_timer", None),
            getattr(self, "apps_timer", None),
        ]
        for timer in timers:
            if not timer:
                continue
            if enabled:
                if timer is getattr(getattr(self, "orb", None), "anim_timer", None):
                    timer.start(110)
                elif timer is getattr(getattr(self, "voice_wave", None), "timer", None):
                    timer.start(90 if getattr(self.voice_wave, "active", False) else 300)
                elif timer is getattr(self, "update_timer", None):
                    timer.start(1000)
                elif timer is getattr(self, "voice_decay_timer", None):
                    timer.start(250)
                elif timer is getattr(self, "apps_timer", None):
                    timer.start(10000)
            else:
                timer.stop()
        
    def _create_header(self):
        header = QFrame()
        header.setObjectName("titleBar")
        header.setFixedHeight(58)
        header.setProperty("titlebar", True)
        header.installEventFilter(self)
        header.setStyleSheet(f"""
            QFrame#titleBar {{
                background: rgba(8, 16, 28, 174);
                border-top-left-radius: {self._window_radius}px;
                border-top-right-radius: {self._window_radius}px;
                border-bottom: 1px solid rgba(0, 240, 255, 18);
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(12)

        settings_btn = QPushButton("⋯")
        settings_btn.setFixedSize(38, 38)
        settings_btn.setToolTip("Settings")
        settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        settings_btn.setStyleSheet(self._chrome_button_style("settings"))
        settings_btn.clicked.connect(self._open_settings_menu)
        layout.addWidget(settings_btn)
        
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand_icon = QLabel("J")
        brand_icon.setFixedSize(36, 36)
        brand_icon.setProperty("titlebar", True)
        brand_icon.installEventFilter(self)
        brand_icon.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {Colors.CYAN.name()}, stop:1 {Colors.BLUE.name()});
            border-radius: 10px;
            color: {Colors.BG_PRIMARY.name()};
            font-family: 'Orbitron';
            font-size: 18px;
            font-weight: bold;
            padding: 0;
        """)
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.hide()
        
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        title = QLabel("J.A.R.V.I.S")
        title.setProperty("titlebar", True)
        title.installEventFilter(self)
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY.name()};
            font-family: 'Orbitron';
            font-size: 18px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        subtitle = QLabel("VOICE CORE · WINDOWS")
        subtitle.setProperty("titlebar", True)
        subtitle.installEventFilter(self)
        subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED.name()};
            font-family: 'JetBrains Mono';
            font-size: 10px;
            letter-spacing: 3px;
        """)
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand.addLayout(brand_text)
        
        layout.addLayout(brand)
        layout.addStretch(1)
        
        self.status_label = QLabel("● INITIALISING")
        self.status_label.setProperty("titlebar", True)
        self.status_label.installEventFilter(self)
        self.status_label.setStyleSheet(f"""
            color: {Colors.ORANGE.name()};
            font-family: 'JetBrains Mono';
            font-size: 12px;
            font-weight: 600;
            padding: 5px 18px;
            background: rgba(10, 20, 32, 118);
            border: 1px solid rgba(249, 115, 22, 120);
            border-radius: 14px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch(1)
        
        for icon, tooltip, role, handler in [
            ("−", "Minimize", "minimize", self._animated_minimize),
            ("□", "Maximize / Restore", "maximize", self._toggle_max_restore),
            ("×", "Hide to tray", "close", self._shutdown),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(38, 38)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(self._chrome_button_style(role))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(handler)
            if role == "maximize":
                self.max_btn = btn
            layout.addWidget(btn)
        
        return header

    def _chrome_button_style(self, role="default"):
        border = "rgba(0, 240, 255, 38)"
        hover_bg = "rgba(0, 240, 255, 24)"
        hover_color = Colors.CYAN.name()
        if role == "close":
            border = "rgba(239, 68, 68, 55)"
            hover_bg = "rgba(239, 68, 68, 42)"
            hover_color = Colors.RED.name()
        elif role == "settings":
            border = "rgba(148, 163, 184, 36)"
            hover_bg = "rgba(148, 163, 184, 24)"
            hover_color = Colors.TEXT_PRIMARY.name()

        return f"""
            QPushButton {{
                background: rgba(10, 20, 32, 190);
                border: 1px solid {border};
                border-radius: 11px;
                color: {Colors.TEXT_SECONDARY.name()};
                font-family: 'Inter';
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {hover_bg};
                border-color: {hover_color};
                color: {hover_color};
            }}
            QPushButton:pressed {{
                background: rgba(0, 240, 255, 34);
                padding-top: 1px;
            }}
        """

    def _open_settings_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: rgba(8, 16, 28, 245);
                border: 1px solid rgba(0, 240, 255, 60);
                border-radius: 10px;
                color: {Colors.TEXT_PRIMARY.name()};
                padding: 8px;
                font-family: 'Inter';
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 8px 26px 8px 12px;
                border-radius: 7px;
            }}
            QMenu::item:selected {{
                background: rgba(0, 240, 255, 28);
                color: {Colors.CYAN.name()};
            }}
        """)

        mute_action = QAction("Mute microphone" if not self.muted else "Unmute microphone", self)
        mute_action.triggered.connect(self._toggle_mute)
        pause_action = QAction("Pause assistant" if not self.paused else "Resume assistant", self)
        pause_action.triggered.connect(self._toggle_pause)
        voice_menu = menu.addMenu("Voice")
        voice_group = QActionGroup(self)
        voice_group.setExclusive(True)
        current_voice = str(load_app_config().get("voice", "Charon") or "Charon")
        for voice in ["Charon", "Kore", "Fenrir", "Puck", "Aoede", "Leda", "Orus", "Zephyr"]:
            voice_action = QAction(voice, self)
            voice_action.setCheckable(True)
            voice_action.setChecked(voice == current_voice)
            voice_action.triggered.connect(lambda checked=False, v=voice: self._change_voice(v))
            voice_group.addAction(voice_action)
            voice_menu.addAction(voice_action)
        fullscreen_action = QAction("Fullscreen / Restore", self)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_action = QAction("Open dashboard" if self._widget_mode else "Widget mode", self)
        view_action.triggered.connect(lambda: self._set_widget_mode(not self._widget_mode))
        hide_action = QAction("Hide to tray", self)
        hide_action.triggered.connect(self._shutdown)
        quit_action = QAction("Exit JARVIS", self)
        quit_action.triggered.connect(self._real_shutdown)

        for action in [mute_action, pause_action, view_action, fullscreen_action, hide_action]:
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.exec(QCursor.pos())

    def _change_voice(self, voice):
        save_app_config({"voice": voice})
        self._add_chat_message(f"[VOICE] Voice changed to {voice}. Reconnect may be needed.", "system")
        if self.on_voice_change:
            threading.Thread(target=self.on_voice_change, args=(voice,), daemon=True).start()

    def _fade_to(self, target, duration=180, finished=None):
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(duration)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(target)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if finished:
            self._opacity_anim.finished.connect(finished)
        self._opacity_anim.start()

    def _animated_minimize(self):
        self._fade_to(0.35, 150, self.showMinimized)

    def _toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
            if hasattr(self, "max_btn"):
                self.max_btn.setText("□")
        else:
            self.showMaximized()
            if hasattr(self, "max_btn"):
                self.max_btn.setText("❐")
        QTimer.singleShot(0, self._update_window_mask)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        QTimer.singleShot(0, self._update_window_mask)

    def _set_widget_mode(self, enabled):
        self._widget_mode = enabled
        self.left_panel.setVisible(not enabled)
        self.right_panel.setVisible(not enabled)
        self.footer.setVisible(not enabled)

        if enabled:
            self.setMinimumSize(440, 560)
            if not self.isMaximized() and not self.isFullScreen():
                self.resize(520, 640)
        else:
            self.setMinimumSize(940, 620)
            if not self.isMaximized() and not self.isFullScreen():
                self.resize(1020, 660)
        QTimer.singleShot(0, self._update_window_mask)

    def _update_window_mask(self):
        if self.isMaximized() or self.isFullScreen():
            self.clearMask()
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), self._window_radius, self._window_radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def eventFilter(self, obj, event):
        if obj.property("titlebar"):
            if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                self._toggle_max_restore()
                return True
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_position is not None:
                if self.isMaximized():
                    ratio = event.position().x() / max(1, obj.width())
                    self.showNormal()
                    self._drag_position = QPoint(int(self.width() * ratio), event.position().toPoint().y())
                self.move(event.globalPosition().toPoint() - self._drag_position)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_position = None
                return True
        return super().eventFilter(obj, event)
    def _create_left_panel(self):
        panel = QWidget()
        panel.setFixedWidth(250)
        panel.setObjectName("leftPanel")
        panel.setStyleSheet(f"""
            QWidget#leftPanel {{
                background: rgba(5, 10, 18, 132);
                border-right: 1px solid rgba(0, 240, 255, 18);
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("LIVE LOG")
        title.setStyleSheet(f"""
            color: {Colors.CYAN.name()};
            font-family: 'JetBrains Mono';
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        header.addWidget(title)
        header.addStretch()
        self.log_count_label = QLabel("00")
        self.log_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-family: 'JetBrains Mono'; font-size: 10px;")
        header.addWidget(self.log_count_label)
        layout.addLayout(header)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.document().setMaximumBlockCount(80)
        self.chat_area.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(2, 4, 8, 132);
                border: 1px solid rgba(0, 240, 255, 26);
                border-radius: 8px;
                color: {Colors.TEXT_SECONDARY.name()};
                font-family: 'JetBrains Mono';
                font-size: 11px;
                padding: 12px;
            }}
        """)
        self.chat_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.chat_area, 1)

        self._log_count = 0
        self._add_chat_message("[AI] Core online", "system")
        self._add_chat_message("[VOICE] Listening channel ready", "system")
        return panel

        panel = QWidget()
        panel.setFixedWidth(320)
        panel.setObjectName("leftPanel")
        panel.setStyleSheet(f"""
            QWidget#leftPanel {{
                background: rgba(5, 10, 18, 180);
                border-right: 1px solid rgba(0, 240, 255, 20);
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(16)
        
        time_card = ModernCard("TIME", Colors.CYAN)
        self.time_display = QLabel("14:32")
        self.time_display.setStyleSheet(f"""
            color: {Colors.CYAN.name()};
            font-family: 'Orbitron';
            font-size: 42px;
            font-weight: bold;
        """)
        time_card.add_widget(self.time_display)
        
        self.date_display = QLabel("27 May 2026 • Pazartesi")
        self.date_display.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 12px;")
        time_card.add_widget(self.date_display)
        layout.addWidget(time_card)
        
        weather_card = ModernCard("WEATHER", Colors.BLUE)
        self.weather_temp = QLabel("24°C")
        self.weather_temp.setStyleSheet(f"""
            color: {Colors.BLUE.name()};
            font-family: 'Orbitron';
            font-size: 32px;
            font-weight: bold;
        """)
        weather_card.add_widget(self.weather_temp)
        self.weather_detail = QLabel("Parçalı Bulutlı • Nem %65")
        self.weather_detail.setStyleSheet(f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 11px;")
        weather_card.add_widget(self.weather_detail)
        layout.addWidget(weather_card)
        
        sys_card = ModernCard("SYSTEM", Colors.GREEN)
        
        self.cpu_bar = StatBar("CPU", Colors.CYAN)
        self.cpu_bar.set_value(32)
        sys_card.add_widget(self.cpu_bar)
        
        self.ram_bar = StatBar("RAM", Colors.PURPLE)
        self.ram_bar.set_value(58)
        sys_card.add_widget(self.ram_bar)
        
        self.disk_bar = StatBar("DISK", Colors.GOLD)
        self.disk_bar.set_value(71)
        sys_card.add_widget(self.disk_bar)
        
        self.batt_bar = StatBar("BATTERY", Colors.GREEN)
        self.batt_bar.set_value(87)
        sys_card.add_widget(self.batt_bar)
        
        net_layout = QHBoxLayout()
        self.net_up = QLabel("▲ 1.2 MB/s")
        self.net_up.setStyleSheet(f"color: {Colors.ORANGE.name()}; font-size: 10px; font-family: 'JetBrains Mono';")
        self.net_down = QLabel("▼ 4.8 MB/s")
        self.net_down.setStyleSheet(f"color: {Colors.GREEN.name()}; font-size: 10px; font-family: 'JetBrains Mono';")
        net_layout.addWidget(self.net_up)
        net_layout.addStretch()
        net_layout.addWidget(self.net_down)
        sys_card.add_layout(net_layout)
        
        layout.addWidget(sys_card)
        layout.addStretch()
        
        return panel
    
    def _create_center_panel(self):
        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.orb = OrbWidget()
        self.orb.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.orb_state_label = QLabel("INITIALISING")
        self.orb_state_label.setStyleSheet(f"""
            color: {Colors.ORANGE.name()};
            font-family: 'Orbitron';
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 4px;
        """)
        self.orb_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orb_state_label.hide()
        
        hint = QLabel("Voice core ready")
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 11px; font-family: 'JetBrains Mono';")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.hide()
        
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.mute_btn = QPushButton("LIVE")
        self.mute_btn.setFixedHeight(36)
        self.mute_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mute_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_CARD.name()};
                border: 1px solid {Colors.GREEN.name()};
                border-radius: 8px;
                color: {Colors.GREEN.name()};
                font-family: 'JetBrains Mono';
                font-size: 11px;
                font-weight: 600;
                padding: 0 20px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {Colors.with_alpha(Colors.GREEN, 20).name()};
            }}
        """)
        self.mute_btn.clicked.connect(self._toggle_mute)
        controls.addWidget(self.mute_btn)
        
        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pause_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_CARD.name()};
                border: 1px solid {Colors.BLUE.name()};
                border-radius: 8px;
                color: {Colors.BLUE.name()};
                font-family: 'JetBrains Mono';
                font-size: 11px;
                font-weight: 600;
                padding: 0 20px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {Colors.with_alpha(Colors.BLUE, 20).name()};
            }}
        """)
        self.pause_btn.clicked.connect(self._toggle_pause)
        controls.addWidget(self.pause_btn)
        
        self.exit_btn = QPushButton("EXIT")
        self.exit_btn.setFixedHeight(36)
        self.exit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.exit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_CARD.name()};
                border: 1px solid {Colors.RED.name()};
                border-radius: 8px;
                color: {Colors.RED.name()};
                font-family: 'JetBrains Mono';
                font-size: 11px;
                font-weight: 600;
                padding: 0 20px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {Colors.with_alpha(Colors.RED, 20).name()};
            }}
        """)
        self.exit_btn.clicked.connect(self._real_shutdown)
        controls.addWidget(self.exit_btn)
        
        layout.addLayout(controls)
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self):
        panel = QWidget()
        panel.setFixedWidth(250)
        panel.setObjectName("rightPanel")
        panel.setStyleSheet(f"""
            QWidget#rightPanel {{
                background: rgba(5, 10, 18, 132);
                border-left: 1px solid rgba(0, 240, 255, 18);
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(10)

        state_card = ModernCard("STATUS", Colors.CYAN)
        state_card.setMinimumHeight(228)
        state_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.mic_status_label = QLabel("MIC  LISTENING")
        self.mic_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mic_status_label.setWordWrap(False)
        self.mic_status_label.setFixedHeight(20)
        self.mic_status_label.setStyleSheet(f"""
            color: {Colors.CYAN.name()};
            font-family: 'JetBrains Mono';
            font-size: 12px;
            font-weight: 700;
        """)
        state_card.add_widget(self.mic_status_label)
        self.voice_wave = VoiceWaveWidget()
        self.voice_wave.setFixedHeight(52)
        state_card.add_widget(self.voice_wave)
        self.voice_detect_label = QLabel("VOICE  IDLE")
        self.voice_detect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_detect_label.setFixedHeight(16)
        self.voice_detect_label.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 10px; font-family: 'JetBrains Mono';")
        state_card.add_widget(self.voice_detect_label)
        self.time_display = QLabel("--:--")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setFixedHeight(36)
        self.time_display.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY.name()};
            font-family: 'Orbitron';
            font-size: 26px;
            font-weight: 700;
        """)
        state_card.add_widget(self.time_display)
        self.date_display = QLabel("")
        self.date_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_display.setWordWrap(True)
        self.date_display.setMinimumHeight(24)
        self.date_display.setMaximumHeight(32)
        self.date_display.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 10px; font-family: 'JetBrains Mono';")
        state_card.add_widget(self.date_display)
        layout.addWidget(state_card)

        sys_card = ModernCard("SYSTEM", Colors.GREEN)
        sys_card.setFixedHeight(132)
        sys_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cpu_bar = StatBar("CPU", Colors.CYAN)
        self.ram_bar = StatBar("RAM", Colors.PURPLE)
        self.cpu_bar.setMinimumHeight(34)
        self.ram_bar.setMinimumHeight(34)
        self.cpu_bar.set_value(0)
        self.ram_bar.set_value(0)
        sys_card.add_widget(self.cpu_bar)
        sys_card.add_widget(self.ram_bar)
        self.uptime_label = QLabel("UPTIME 00:00")
        self.uptime_label.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 10px; font-family: 'JetBrains Mono';")
        sys_card.add_widget(self.uptime_label)
        layout.addWidget(sys_card)

        apps_card = ModernCard("ACTIVE APPS", Colors.BLUE)
        apps_card.setMinimumHeight(104)
        self.active_apps_label = QLabel("Scanning...")
        self.active_apps_label.setWordWrap(True)
        self.active_apps_label.setMinimumHeight(34)
        self.active_apps_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY.name()};
            font-family: 'JetBrains Mono';
            font-size: 10px;
            line-height: 1.35;
        """)
        apps_card.add_widget(self.active_apps_label)
        self.active_apps_hint = QLabel("updates every 10s")
        self.active_apps_hint.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 9px; font-family: 'JetBrains Mono';")
        apps_card.add_widget(self.active_apps_hint)
        layout.addWidget(apps_card)
        layout.addStretch()
        return panel

        radar_card = ModernCard("RADAR", Colors.BLUE)
        radar_row = QHBoxLayout()
        radar_row.addStretch()
        radar_row.addWidget(RadarWidget())
        radar_row.addStretch()
        radar_card.add_layout(radar_row)
        self.radar_caption = QLabel("LOW POWER SWEEP")
        self.radar_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.radar_caption.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-size: 10px; font-family: 'JetBrains Mono';")
        radar_card.add_widget(self.radar_caption)
        layout.addWidget(radar_card)
        layout.addStretch()
        return panel

        panel = QWidget()
        panel.setFixedWidth(380)
        panel.setObjectName("rightPanel")
        panel.setStyleSheet(f"""
            QWidget#rightPanel {{
                background: rgba(5, 10, 18, 180);
                border-left: 1px solid rgba(0, 240, 255, 20);
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        chat_header = QFrame()
        chat_header.setFixedHeight(56)
        chat_header.setStyleSheet(f"""
            QFrame {{
                border-bottom: 1px solid rgba(0, 240, 255, 20);
            }}
        """)
        header_layout = QHBoxLayout(chat_header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        chat_title = QLabel("CONVERSATION")
        chat_title.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED.name()};
            font-family: 'JetBrains Mono';
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(chat_title)
        header_layout.addStretch()
        
        online = QLabel("● Online")
        online.setStyleSheet(f"color: {Colors.GREEN.name()}; font-family: 'JetBrains Mono'; font-size: 10px;")
        header_layout.addWidget(online)
        layout.addWidget(chat_header)
        
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {Colors.TEXT_SECONDARY.name()};
                font-family: 'Inter';
                font-size: 13px;
                padding: 16px 20px;
            }}
        """)
        self.chat_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.chat_area)
        
        input_frame = QFrame()
        input_frame.setFixedHeight(70)
        input_frame.setStyleSheet(f"""
            QFrame {{
                border-top: 1px solid rgba(0, 240, 255, 20);
            }}
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 12, 20, 12)
        input_layout.setSpacing(10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Komut yazın...")
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Colors.BG_CARD.name()};
                border: 1px solid rgba(0, 240, 255, 30);
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY.name()};
                font-family: 'Inter';
                font-size: 13px;
                padding: 10px 14px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.CYAN.name()};
            }}
        """)
        self.chat_input.returnPressed.connect(self._on_input_submit)
        input_layout.addWidget(self.chat_input)
        
        send_btn = QPushButton("➤")
        send_btn.setFixedSize(36, 36)
        send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Colors.CYAN.name()}, stop:1 {Colors.BLUE.name()});
                border: none;
                border-radius: 8px;
                color: {Colors.BG_PRIMARY.name()};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Colors.with_alpha(Colors.CYAN, 200).name()}, 
                    stop:1 {Colors.with_alpha(Colors.BLUE, 200).name()});
            }}
        """)
        send_btn.clicked.connect(self._on_input_submit)
        input_layout.addWidget(send_btn)
        
        layout.addWidget(input_frame)
        
        self._add_chat_message("J.A.R.V.I.S aktif. Dinliyorum...", "system")
        self._add_chat_message("Merhaba! Size nasıl yardımcı olabilirim?", "ai")
        
        return panel
    
    def _create_footer(self):
        footer = QFrame()
        footer.setObjectName("footerBar")
        footer.setFixedHeight(76)
        footer.setStyleSheet(f"""
            QFrame#footerBar {{
                background: rgba(8, 16, 28, 150);
                border-top: 1px solid rgba(0, 240, 255, 16);
                border-bottom-left-radius: {self._window_radius}px;
                border-bottom-right-radius: {self._window_radius}px;
            }}
        """)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        prompt = QLabel("")
        prompt.hide()
        prompt.setStyleSheet(f"""
            color: {Colors.CYAN.name()};
            font-family: 'JetBrains Mono';
            font-size: 12px;
            font-weight: 800;
            padding: 0 4px;
        """)
        layout.addWidget(prompt)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Mesaj yaz...")
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(2, 4, 8, 112);
                border: 1px solid rgba(0, 240, 255, 24);
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY.name()};
                font-family: 'JetBrains Mono';
                font-size: 13px;
                padding: 11px 14px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.CYAN.name()};
                background: rgba(5, 10, 18, 170);
            }}
        """)
        self.chat_input.returnPressed.connect(self._on_input_submit)
        layout.addWidget(self.chat_input, 1)

        send_btn = QPushButton("SEND")
        send_btn.setFixedSize(72, 40)
        send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 240, 255, 30);
                border: 1px solid {Colors.CYAN.name()};
                border-radius: 8px;
                color: {Colors.CYAN.name()};
                font-family: 'JetBrains Mono';
                font-size: 11px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: rgba(0, 240, 255, 48);
            }}
        """)
        send_btn.clicked.connect(self._on_input_submit)
        layout.addWidget(send_btn)
        return footer

        footer = QFrame()
        footer.setObjectName("footerBar")
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"""
            QFrame#footerBar {{
                background: rgba(8, 16, 28, 220);
                border-top: 1px solid rgba(0, 240, 255, 20);
                border-bottom-left-radius: {self._window_radius}px;
                border-bottom-right-radius: {self._window_radius}px;
            }}
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 0, 24, 0)
        
        left = QLabel(f"{AUTHOR_NAME}  |  JARVIS Windows Edition")
        left.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-family: 'JetBrains Mono'; font-size: 10px;")
        layout.addWidget(left)
        
        layout.addStretch()
        
        center = QLabel("● Core Active    F4 Mute    F5 Pause    F11 Fullscreen")
        center.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-family: 'JetBrains Mono'; font-size: 10px;")
        layout.addWidget(center)
        
        layout.addStretch()
        
        right = QLabel("v5.0 Next Gen")
        right.setStyleSheet(f"color: {Colors.TEXT_MUTED.name()}; font-family: 'JetBrains Mono'; font-size: 10px;")
        layout.addWidget(right)
        
        return footer
    
    def _update_ui(self):
        now = time.localtime()
        if hasattr(self, "time_display"):
            self.time_display.setText(f"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}")
        months = ["", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
                  "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"]
        days = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
        if hasattr(self, "date_display"):
            self.date_display.setText(f"{days[now.tm_wday]} / {now.tm_mday} {months[now.tm_mon]}")
        sys_due = (time.time() - getattr(self, "_last_sys_update", 0.0)) >= 4.0
        if psutil and sys_due:
            if hasattr(self, "cpu_bar"):
                self.cpu_bar.set_value(psutil.cpu_percent(interval=None))
            if hasattr(self, "ram_bar"):
                self.ram_bar.set_value(psutil.virtual_memory().percent)
            self._last_sys_update = time.time()
        if hasattr(self, "uptime_label"):
            uptime = int(time.time() - getattr(self, "_started_at", time.time()))
            minutes, seconds = divmod(uptime, 60)
            hours, minutes = divmod(minutes, 60)
            self.uptime_label.setText(f"UPTIME {hours:02d}:{minutes:02d}:{seconds:02d}")
        return
        self.time_display.setText(f"{now.tm_hour:02d}:{now.tm_min:02d}")
        months = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        day_idx = (now.tm_wday + 6) % 7
        self.date_display.setText(f"{now.tm_mday} {months[now.tm_mon]} {now.tm_year} • {days[day_idx]}")
        
    def _update_voice_decay(self):
        if self.user_speaking and time.time() > self._user_speaking_until:
            self.set_user_speaking(False)

    def _update_active_apps(self):
        if not hasattr(self, "active_apps_label"):
            return
        if not psutil:
            self.active_apps_label.setText("psutil unavailable")
            return

        skip = {
            "system", "registry", "idle", "svchost.exe", "runtimebroker.exe",
            "conhost.exe", "dllhost.exe", "fontdrvhost.exe", "audiodg.exe",
            "searchindexer.exe", "securityhealthservice.exe", "wmiprvse.exe",
            "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
            "lsass.exe", "smss.exe", "system idle process", "gameinputredistservice.exe",
            "lsaiso.exe", "wudfhost.exe", "msedgewebview2.exe", "intelcphdcpsvc.exe",
        }
        seen = []
        seen_lower = set()

        pids = []
        if os.name == "nt":
            try:
                user32 = ctypes.windll.user32
                callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

                def enum_window(hwnd, _):
                    if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        if pid.value:
                            pids.append(pid.value)
                    return True

                user32.EnumWindows(callback_type(enum_window), 0)
            except Exception:
                pids = []

        proc_source = []
        if pids:
            for pid in pids[:24]:
                try:
                    proc_source.append(psutil.Process(pid))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        elif os.name != "nt":
            proc_source = list(psutil.process_iter(["name"]))

        for proc in proc_source:
            try:
                info = getattr(proc, "info", None)
                name = ((info or {}).get("name") or proc.name() or "").strip()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if not name:
                continue
            low = name.lower()
            if low in skip or low.startswith("python") or low in seen_lower:
                continue
            display = name[:-4] if low.endswith(".exe") else name
            seen.append(display)
            seen_lower.add(low)
            if len(seen) >= 4:
                break

        if seen:
            self.active_apps_label.setText("\n".join(f"- {name}" for name in seen))
        else:
            self.active_apps_label.setText("No foreground apps")

    def _on_state_changed(self, state):
        self.status_label.setText(f"● {state}")
        self.orb_state_label.setText(state)
        
        colors = {
            "LISTENING": Colors.CYAN, "SPEAKING": Colors.BLUE,
            "THINKING": Colors.GOLD, "PAUSED": Colors.TEXT_MUTED,
            "ERROR": Colors.RED, "INITIALISING": Colors.ORANGE
        }
        color = colors.get(state, Colors.CYAN)
        if hasattr(self, "mic_status_label"):
            mic_state = "MUTED" if self.muted else ("IDLE" if state in ("PAUSED", "INITIALISING") else state)
            self.mic_status_label.setText(f"MIC  {mic_state}")
            self.mic_status_label.setStyleSheet(f"""
                color: {color.name()};
                font-family: 'JetBrains Mono';
                font-size: 13px;
                font-weight: 700;
            """)
        self.status_label.setStyleSheet(f"""
            color: {color.name()};
            font-family: 'JetBrains Mono';
            font-size: 12px;
            font-weight: 600;
            padding: 5px 18px;
            background: rgba(10, 20, 32, 118);
            border: 1px solid rgba({color.red()}, {color.green()}, {color.blue()}, 120);
            border-radius: 14px;
        """)
        self.orb_state_label.setStyleSheet(f"""
            color: {color.name()};
            font-family: 'Orbitron';
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 4px;
        """)
        
    def _add_chat_message(self, text, msg_type):
        colors = {
            "user": Colors.CYAN.name(),
            "ai": Colors.TEXT_SECONDARY.name(),
            "system": Colors.TEXT_MUTED.name(),
            "error": Colors.RED.name()
        }
        prefixes = {"user": "[YOU] ", "ai": "[AI] ", "system": "[SYS] ", "error": "[ERR] "}
        color = colors.get(msg_type, Colors.TEXT_SECONDARY.name())
        prefix = prefixes.get(msg_type, "")
        
        self.chat_area.append(f'<span style="color: {color};">{prefix}{text}</span>')
        if hasattr(self, "_log_count"):
            self._log_count = min(99, self._log_count + 1)
            if hasattr(self, "log_count_label"):
                self.log_count_label.setText(f"{self._log_count:02d}")
        
    def _on_input_submit(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self._add_chat_message(text, "user")
        self.chat_input.clear()
        
        if text.lower() in ("sus", "dur", "stop", "kes"):
            self._add_chat_message("Stopped.", "system")
            if self.on_stop_command:
                threading.Thread(target=self.on_stop_command, daemon=True).start()
            return
        
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()
        
        self.set_state("THINKING")
        
    def _toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.mute_btn.setText("MUTED")
            self._add_chat_message("[VOICE] Mic muted", "system")
        else:
            self.mute_btn.setText("LIVE")
            self._add_chat_message("[VOICE] Mic live", "system")
        if hasattr(self, "mic_status_label"):
            self.mic_status_label.setText("MIC  MUTED" if self.muted else "MIC  LISTENING")
        return
        if self.muted:
            self.mute_btn.setText("🔇 MUTED")
            self._add_chat_message("Mic muted.", "system")
        else:
            self.mute_btn.setText("🎙 LIVE")
            self._add_chat_message("Mic live.", "system")
        
    def set_paused_state(self, paused, notify=True):
        self.paused = bool(paused)
        if self.paused:
            self.pause_btn.setText("RESUME")
            self.set_state("PAUSED")
            self._add_chat_message("[AI] Paused", "system")
        else:
            self.pause_btn.setText("PAUSE")
            self.set_state("LISTENING")
            self._add_chat_message("[AI] Resumed", "system")
        tray = getattr(self, "tray", None)
        if tray:
            tray.set_paused(self.paused)
        if notify and self.on_pause_toggle:
            threading.Thread(target=self.on_pause_toggle, args=(self.paused,), daemon=True).start()

    def _toggle_pause(self):
        self.set_paused_state(not self.paused)
        return
        if self.paused:
            self.pause_btn.setText("▶ RESUME")
            self.set_state("PAUSED")
            self._add_chat_message("Paused.", "system")
        else:
            self.pause_btn.setText("⏸ PAUSE")
            self.set_state("LISTENING")
            self._add_chat_message("Resumed.", "system")
        if self.on_pause_toggle:
            threading.Thread(target=self.on_pause_toggle, args=(self.paused,), daemon=True).start()
        
    def _shutdown(self):
        tray = getattr(self, "tray", None)
        if tray:
            tray.hide_to_tray()
        self._fade_to(0.18, 170, self.hide)
        
    def _real_shutdown(self):
        self._add_chat_message("Sistem kapatılıyor...", "system")
        self._allow_close = True
        QTimer.singleShot(1000, self.close)

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
            return
        event.ignore()
        self._shutdown()
        
    def set_state(self, state):
        previous = getattr(self, "_jarvis_state", "")
        self._jarvis_state = state
        self.speaking = (state == "SPEAKING")
        self.orb.set_state(state)
        
    def set_user_speaking(self, value):
        self.user_speaking = value
        self.orb.is_user_speaking = value
        self._user_speaking_until = time.time() + (0.9 if value else 0.0)
        if hasattr(self, "voice_wave"):
            self.voice_wave.set_active(value)
        if hasattr(self, "voice_detect_label"):
            self.voice_detect_label.setText("VOICE  DETECTED" if value else "VOICE  IDLE")
            self.voice_detect_label.setStyleSheet(f"""
                color: {(Colors.GREEN if value else Colors.TEXT_MUTED).name()};
                font-size: 10px;
                font-family: 'JetBrains Mono';
            """)
        
    def write_log(self, text):
        tl = text.lower()
        if tl.startswith("siz:") or tl.startswith("you:"):
            self._add_chat_message(text, "user")
            self.set_user_speaking(True)
            self.set_state("THINKING")
        elif tl.startswith("err:") or "error" in tl:
            self._add_chat_message(text, "error")
            self.set_state("ERROR")
        else:
            self._add_chat_message(text, "ai")
            
    def write_debug(self, text, level="INFO"):
        clean = " ".join(str(text or "").split())
        if clean:
            self._add_chat_message(f"[{level}] {clean}", "system")
            
    def wake_up(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._fade_to(0.94, 160)

    def is_hidden_to_tray(self):
        tray = getattr(self, "tray", None)
        return bool(tray and tray.is_hidden())
        
    def focus_panel(self, section, duration_ms=4200):
        pass
        
    def get_effects_volume(self):
        return 0.5
        
    def effects_enabled(self):
        return True
        
    def play_success_sfx(self):
        pass
        
    def play_error_sfx(self):
        pass
        
    def show_health_hologram(self, query, data_str):
        self.write_log(f"SYS: {data_str[:120]}")
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4:
            self._toggle_mute()
        elif event.key() == Qt.Key.Key_F5:
            self._toggle_pause()
        elif event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self._shutdown()
        else:
            super().keyPressEvent(event)


# ── ESKİ API UYUMLULUK SINIFI ──────────────────────────────────────────────
class JarvisUI:
    """Eski tkinter API'si ile uyumlu wrapper."""

    _CALLBACK_NAMES = {
        "on_text_command",
        "on_pause_toggle",
        "on_stop_command",
        "on_voice_change",
        "on_effects_state_change",
    }
    _PROXY_ATTR_NAMES = {"muted", "paused"}

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name in self._CALLBACK_NAMES and "window" in self.__dict__:
            setattr(self.window, name, value)
        elif name in self._PROXY_ATTR_NAMES and "window" in self.__dict__:
            setattr(self.window, name, value)

    def __getattr__(self, name):
        if name in self._PROXY_ATTR_NAMES and "window" in self.__dict__:
            return getattr(self.window, name)
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication([])
        self.window = JarvisModernWindow()
        
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_stop_command = None
        self.on_voice_change = None
        self.on_effects_state_change = None
        
        self.window.on_text_command = self.on_text_command
        self.window.on_pause_toggle = self.on_pause_toggle
        self.window.on_stop_command = self.on_stop_command
        self.window.on_voice_change = self.on_voice_change
        self.window.on_effects_state_change = self.on_effects_state_change
        
        self.tray = None
        try:
            self.tray = TrayManager(show_fn=self.window.wake_up, quit_fn=self.window._real_shutdown)
            self.window.tray = self.tray
            self.tray.start()
            self.tray.on_mute_toggle = self.window._toggle_mute
            self.tray.on_pause_toggle = self.window._toggle_pause
        except:
            pass
            
    def set_state(self, state):
        self.window.set_state(state)
        
    def set_user_speaking(self, value):
        self.window.set_user_speaking(value)

    def mark_user_activity(self, value=True):
        self.window.set_user_speaking(value)
        
    def write_log(self, text):
        self.window.write_log(text)
        
    def write_debug(self, text, level="INFO"):
        self.window.write_debug(text, level)
        
    def wake_up(self):
        self.window.wake_up()

    def is_hidden_to_tray(self):
        return self.window.is_hidden_to_tray()

    def set_paused_state(self, paused, notify=True):
        self.window.set_paused_state(paused, notify)
        
    def focus_panel(self, section, duration_ms=4200):
        self.window.focus_panel(section, duration_ms)
        
    def get_effects_volume(self):
        return self.window.get_effects_volume()
        
    def effects_enabled(self):
        return self.window.effects_enabled()
        
    def play_success_sfx(self):
        self.window.play_success_sfx()
        
    def play_error_sfx(self):
        self.window.play_error_sfx()
        
    def show_health_hologram(self, query, data_str):
        self.window.show_health_hologram(query, data_str)

    def wait_for_api_key(self):
        if has_gemini_api_key():
            return

        self.write_log("ERR: Gemini API key ayarlanmamis. Config dosyasina gemini_api_key ekleyin.")
        while not has_gemini_api_key():
            time.sleep(1)
        
    def run(self):
        self.window.show()
        self.app.exec()
