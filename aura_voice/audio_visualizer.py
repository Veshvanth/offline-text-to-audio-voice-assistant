import math
import random
import tkinter as tk


class AudioVisualizer(tk.Canvas):
    """
    Animated audio visualizer bar widget that reacts while the AI Voice Assistant is speaking.
    """
    def __init__(self, parent, width: int = 240, height: int = 40, bar_count: int = 16, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=kwargs.get("bg", "#0f172a"),
            highlightthickness=0
        )
        self.width = width
        self.height = height
        self.bar_count = bar_count
        self.is_active = False
        self._animation_id = None
        self.bar_heights = [4.0] * bar_count
        self.target_heights = [4.0] * bar_count
        self.colors = [
            "#38bdf8", "#0ea5e9", "#0284c7", "#3b82f6",
            "#6366f1", "#8b5cf6", "#a855f7", "#d946ef",
            "#a855f7", "#8b5cf6", "#6366f1", "#3b82f6",
            "#0284c7", "#0ea5e9", "#38bdf8", "#7dd3fc"
        ]
        self._draw_bars()

    def start_animation(self):
        """Start active equalizer wave bounce."""
        self.is_active = True
        self._update_frame()

    def stop_animation(self):
        """Calm down to idle baseline."""
        self.is_active = False
        self.target_heights = [4.0] * self.bar_count
        self._draw_bars()

    def _update_frame(self):
        if not self.is_active:
            # Gradually decay heights to baseline
            all_idle = True
            for i in range(self.bar_count):
                diff = 4.0 - self.bar_heights[i]
                if abs(diff) > 0.5:
                    self.bar_heights[i] += diff * 0.25
                    all_idle = False
                else:
                    self.bar_heights[i] = 4.0
            self._draw_bars()
            if not all_idle:
                self._animation_id = self.after(35, self._update_frame)
            return

        # Generate animated heights with sinusoids + jitter
        center = self.bar_count / 2.0
        max_h = self.height - 8
        for i in range(self.bar_count):
            dist = 1.0 - (abs(i - center) / center) * 0.4
            jitter = random.uniform(0.3, 1.0)
            target = max(6.0, dist * jitter * max_h)
            self.bar_heights[i] += (target - self.bar_heights[i]) * 0.45

        self._draw_bars()
        self._animation_id = self.after(45, self._update_frame)

    def _draw_bars(self):
        self.delete("all")
        spacing = self.width / float(self.bar_count)
        bar_w = max(4.0, spacing * 0.65)
        cy = self.height / 2.0

        for i in range(self.bar_count):
            h = self.bar_heights[i]
            x0 = i * spacing + (spacing - bar_w) / 2.0
            x1 = x0 + bar_w
            y0 = cy - (h / 2.0)
            y1 = cy + (h / 2.0)
            color = self.colors[i % len(self.colors)] if self.is_active else "#334155"

            # Draw smooth rounded-look bar
            self.create_rectangle(
                x0, y0, x1, y1,
                fill=color,
                outline="",
                width=0
            )

