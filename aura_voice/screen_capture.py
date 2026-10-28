import ctypes
import tkinter as tk
from typing import Callable, Optional, Tuple
from PIL import Image, ImageGrab, ImageChops

# Enable Windows DPI awareness for pixel-perfect coordinates
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class SnipOverlay:
    """
    Transparent fullscreen overlay allowing user to drag a rectangle
    and snip any section of the screen containing text or handwriting.
    """
    def __init__(self, root: tk.Tk, on_snip_completed: Callable[[Optional[Image.Image]], None]):
        self.parent = root
        self.on_snip_completed = on_snip_completed
        self.top: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.guide_text_id = None

    def start(self):
        # Hide parent window temporarily so it doesn't get snipped
        self.parent.withdraw()
        self.parent.after(200, self._create_overlay)

    def _create_overlay(self):
        self.top = tk.Toplevel(self.parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.35)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="cross")

        # Get full screen dimensions
        screen_width = self.top.winfo_screenwidth()
        screen_height = self.top.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.top,
            cursor="cross",
            bg="#0f172a",
            highlightthickness=0,
            width=screen_width,
            height=screen_height
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Instructions banner on overlay
        self.guide_text_id = self.canvas.create_text(
            screen_width // 2,
            50,
            text="✨ Drag a rectangle over screen text or handwriting to read aloud | Press [ESC] to cancel",
            fill="#38bdf8",
            font=("Segoe UI", 16, "bold")
        )

        # Event bindings
        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.top.bind("<Escape>", self._on_cancel)

    def _on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#38bdf8", width=3, fill="#0284c7", stipple="gray25"
        )

    def _on_move_press(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def _on_button_release(self, event):
        end_x, end_y = event.x, event.y
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # Close overlay and restore main window
        self._cleanup()

        # Minimum snip area check (e.g. at least 10x10 px)
        if (x2 - x1) >= 10 and (y2 - y1) >= 10:
            # Short delay to allow screen overlay to fully vanish
            self.parent.after(80, lambda: self._capture_bbox((x1, y1, x2, y2)))
        else:
            self.on_snip_completed(None)

    def _on_cancel(self, event=None):
        self._cleanup()
        self.on_snip_completed(None)

    def _cleanup(self):
        if self.top:
            self.top.destroy()
            self.top = None
        self.parent.deiconify()

    def _capture_bbox(self, bbox: Tuple[int, int, int, int]):
        try:
            image = ImageGrab.grab(bbox=bbox, all_screens=True)
            self.on_snip_completed(image)
        except Exception as e:
            print(f"Error capturing snip region: {e}")
            self.on_snip_completed(None)


def capture_fullscreen() -> Optional[Image.Image]:
    """Capture the full active screen."""
    try:
        return ImageGrab.grab(all_screens=True)
    except Exception as e:
        print(f"Error capturing full screen: {e}")
        return None


def capture_clipboard() -> Optional[Image.Image]:
    """Grab image from system clipboard if present."""
    try:
        content = ImageGrab.grabclipboard()
        if isinstance(content, Image.Image):
            return content
        return None
    except Exception as e:
        print(f"Error grabbing clipboard: {e}")
        return None


def has_image_changed(img1: Optional[Image.Image], img2: Optional[Image.Image], threshold: float = 0.05) -> bool:
    """Check if two screen captures differ significantly (for live monitor)."""
    if img1 is None or img2 is None:
        return True
    if img1.size != img2.size:
        return True
    try:
        diff = ImageChops.difference(img1.convert("RGB"), img2.convert("RGB"))
        stat = sum(diff.convert("L").histogram())
        total_pixels = img1.width * img1.height
        change_ratio = stat / (total_pixels * 255.0)
        return change_ratio > threshold
    except Exception:
        return True

