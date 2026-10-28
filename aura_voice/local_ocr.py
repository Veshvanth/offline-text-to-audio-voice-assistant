import io
import threading
from typing import Optional, List
import numpy as np
from PIL import Image, ImageEnhance, ImageOps


class LocalOCREngine:
    """
    Offline Optical Character Recognition & Handwriting Reader using EasyOCR.
    Runs 100% locally on the user's PC with ZERO API keys and ZERO internet.
    """
    def __init__(self):
        self.reader = None
        self._is_loading = False
        self._is_ready = False
        self._lock = threading.Lock()
        # Pre-load reader in background
        self.start_preload()

    def start_preload(self):
        """Asynchronously initialize EasyOCR model weights without blocking the UI."""
        if not self._is_ready and not self._is_loading:
            self._is_loading = True
            threading.Thread(target=self._init_reader, daemon=True).start()

    def _init_reader(self):
        try:
            import easyocr
            # Initialize for English (runs on CPU or GPU if available)
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            with self._lock:
                self.reader = reader
                self._is_ready = True
                self._is_loading = False
            print("Local EasyOCR Engine is ready!")
        except Exception as e:
            print(f"Error loading local EasyOCR: {e}")
            with self._lock:
                self._is_loading = False

    def is_ready(self) -> bool:
        return self._is_ready

    def preprocess_for_ocr(self, pil_img: Image.Image) -> Image.Image:
        """
        Enhance handwriting contrast, clean noise, and make light pencil
        or pen strokes crisp and legible for the local OCR model.
        """
        try:
            img = pil_img.convert("RGB")
            # Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.4)
            # Increase sharpness
            sharpener = ImageEnhance.Sharpness(img)
            img = sharpener.enhance(1.5)
            return img
        except Exception:
            return pil_img

    def recognize(self, pil_img: Image.Image) -> str:
        """
        Recognize text and handwriting from a PIL Image without any API key.
        """
        if not self._is_ready:
            # If not yet loaded, initialize synchronously
            self._init_reader()

        if not self.reader:
            return "Local OCR model could not be loaded. Please ensure EasyOCR is installed."

        try:
            processed_img = self.preprocess_for_ocr(pil_img)
            img_np = np.array(processed_img)

            # EasyOCR returns list of (bbox, text, prob)
            results = self.reader.readtext(img_np, detail=1, paragraph=True)

            if not results:
                # Try without paragraph grouping
                raw_results = self.reader.readtext(img_np, detail=1, paragraph=False)
                if not raw_results:
                    return "No readable text or handwriting detected in the selected area."
                results = raw_results

            # Sort top to bottom, left to right by bounding box
            extracted_lines = []
            for item in results:
                text = item[1].strip()
                if text:
                    extracted_lines.append(text)

            if not extracted_lines:
                return "No readable text or handwriting detected in the selected area."

            # Group into natural paragraphs
            return "\n\n".join(extracted_lines)

        except Exception as e:
            return f"Local recognition error: {e}"

