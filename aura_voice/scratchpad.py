import tkinter as tk
from typing import Callable
from PIL import Image, ImageDraw, ImageFont


class HandwritingScratchpad(tk.Toplevel):
    """
    Built-in interactive canvas for writing with a mouse or stylus
    to instantly test handwriting-to-speech without needing external apps.
    """
    def __init__(self, parent: tk.Tk, on_submit: Callable[[Image.Image], None]):
        super().__init__(parent)
        self.title("✍️ Handwriting Test Canvas & Scratchpad")
        self.geometry("680x560")
        self.configure(bg="#0f172a")
        self.on_submit = on_submit

        self.pen_color = "#000000"
        self.pen_size = 4
        self.last_x, self.last_y = None, None

        # Underlying PIL image matching canvas size
        self.canvas_w = 640
        self.canvas_h = 380
        self.pil_image = Image.new("RGB", (self.canvas_w, self.canvas_h), color="#ffffff")
        self.pil_draw = ImageDraw.Draw(self.pil_image)

        self._build_ui()

    def _build_ui(self):
        # Top Header
        header = tk.Frame(self, bg="#0f172a")
        header.pack(fill=tk.X, padx=20, pady=(15, 10))

        tk.Label(
            header,
            text="✍️ Practice or Test Handwriting",
            font=("Segoe UI", 14, "bold"),
            bg="#0f172a",
            fg="#f8fafc"
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text="Write with your mouse, stylus, or pen below",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8"
        ).pack(side=tk.RIGHT)

        # Drawing Canvas
        canvas_frame = tk.Frame(self, bg="#334155", bd=2, relief=tk.SOLID)
        canvas_frame.pack(padx=20, pady=5)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#ffffff",
            cursor="pencil",
            highlightthickness=0
        )
        self.canvas.pack()

        # Canvas Event bindings
        self.canvas.bind("<Button-1>", self._start_draw)
        self.canvas.bind("<B1-Motion>", self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._stop_draw)

        # Draw light ruling lines (like notebook paper) to guide handwriting
        self._draw_guidelines()

        # Controls Toolbar
        toolbar = tk.Frame(self, bg="#0f172a")
        toolbar.pack(fill=tk.X, padx=20, pady=12)

        # Pen Size
        tk.Label(toolbar, text="Pen Width:", bg="#0f172a", fg="#cbd5e1", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        for sz, label in [(2, "Fine"), (4, "Normal"), (7, "Thick")]:
            btn = tk.Button(
                toolbar,
                text=label,
                font=("Segoe UI", 8),
                bg="#1e293b",
                fg="#f8fafc",
                relief=tk.FLAT,
                padx=8,
                command=lambda s=sz: self._set_pen_size(s)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Pen Colors
        tk.Label(toolbar, text="Color:", bg="#0f172a", fg="#cbd5e1", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(12, 4))
        for col, label in [("#000000", "Black"), ("#1d4ed8", "Blue"), ("#b91c1c", "Red")]:
            btn = tk.Button(
                toolbar,
                text=label,
                font=("Segoe UI", 8),
                bg=col,
                fg="#ffffff",
                relief=tk.FLAT,
                padx=6,
                command=lambda c=col: self._set_pen_color(c)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Clear button
        clear_btn = tk.Button(
            toolbar,
            text="🗑️ Clear",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=10,
            command=self._clear_canvas
        )
        clear_btn.pack(side=tk.LEFT, padx=(16, 4))

        # Sample Handwritten Presets
        sample_btn = tk.Button(
            toolbar,
            text="📝 Load Sample",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#38bdf8",
            relief=tk.FLAT,
            padx=10,
            command=self._load_sample
        )
        sample_btn.pack(side=tk.LEFT, padx=4)

        # Bottom Action Bar
        action_bar = tk.Frame(self, bg="#0f172a")
        action_bar.pack(fill=tk.X, padx=20, pady=(5, 15))

        submit_btn = tk.Button(
            action_bar,
            text="🔊 Convert Handwriting to Speech",
            font=("Segoe UI", 11, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=8,
            command=self._submit
        )
        submit_btn.pack(fill=tk.X)

    def _draw_guidelines(self):
        # Draw light ruling lines
        for y in range(60, self.canvas_h, 50):
            self.canvas.create_line(0, y, self.canvas_w, y, fill="#e2e8f0", width=1)
            self.pil_draw.line([(0, y), (self.canvas_w, y)], fill="#e2e8f0", width=1)

    def _start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _draw(self, event):
        if self.last_x is not None and self.last_y is not None:
            # Draw on Tkinter canvas
            self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.pen_color, width=self.pen_size,
                capstyle=tk.ROUND, smooth=True
            )
            # Draw on PIL image
            self.pil_draw.line(
                [(self.last_x, self.last_y), (event.x, event.y)],
                fill=self.pen_color, width=self.pen_size
            )
            self.last_x, self.last_y = event.x, event.y

    def _stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def _set_pen_size(self, size: int):
        self.pen_size = size

    def _set_pen_color(self, color: str):
        self.pen_color = color

    def _clear_canvas(self):
        self.canvas.delete("all")
        self.pil_image = Image.new("RGB", (self.canvas_w, self.canvas_h), color="#ffffff")
        self.pil_draw = ImageDraw.Draw(self.pil_image)
        self._draw_guidelines()

    def _load_sample(self):
        """Draw an informative handwritten cursive sample on the canvas."""
        self._clear_canvas()
        try:
            # Draw text sample representing handwritten note
            self.pil_draw.text((30, 45), "Hello! This is a handwritten note.", fill="#0f172a", font_size=24)
            self.pil_draw.text((30, 95), "Artificial Intelligence can now see handwriting", fill="#1e3a8a", font_size=20)
            self.pil_draw.text((30, 145), "and turn it into natural spoken voice!", fill="#1e3a8a", font_size=20)
            self.pil_draw.text((30, 205), "Math note: E = m c^2 and Area = pi * r^2", fill="#991b1b", font_size=20)
            self.pil_draw.text((30, 265), "Speed is fully adjustable from 0.5x to 2.5x.", fill="#047857", font_size=20)

            # Mirror onto Tkinter canvas
            self.canvas.create_text(30, 55, text="Hello! This is a handwritten note.", fill="#0f172a", font=("Segoe Script", 16, "bold"), anchor="w")
            self.canvas.create_text(30, 105, text="Artificial Intelligence can now see handwriting", fill="#1e3a8a", font=("Segoe Script", 14), anchor="w")
            self.canvas.create_text(30, 155, text="and turn it into natural spoken voice!", fill="#1e3a8a", font=("Segoe Script", 14), anchor="w")
            self.canvas.create_text(30, 215, text="Math note: E = m c^2 and Area = pi * r^2", fill="#991b1b", font=("Segoe Script", 14), anchor="w")
            self.canvas.create_text(30, 275, text="Speed is fully adjustable from 0.5x to 2.5x.", fill="#047857", font=("Segoe Script", 14), anchor="w")
        except Exception as e:
            print(f"Error loading sample: {e}")

    def _submit(self):
        img_copy = self.pil_image.copy()
        self.destroy()
        self.on_submit(img_copy)

