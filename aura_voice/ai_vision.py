import io
from typing import Optional
from PIL import Image, ImageEnhance
from google import genai
from google.genai import types

HANDWRITING_PROMPTS = {
    "direct": """You are an expert Optical Handwriting and Screen Reader AI.
Your job is to read and transcribe all text and human handwriting in this image into clear, natural English for a text-to-speech engine.

Image Analysis Rules:
1. Human Handwriting: Look very closely at all handwritten words, cursive, stylus pen strokes, whiteboard notes, margins, and annotations. Decipher messy or cursive handwriting carefully based on linguistic context.
2. Printed Text: Transcribe all typed screen text, headings, buttons, or dialogs accurately.
3. Spoken Naturalness: Return only the exact transcribed words in readable order. Expand ambiguous handwritten abbreviations if needed for speech (e.g., "w/" to "with", "e.g." to "for example").
4. Output Format: Output ONLY the transcribed text. Do NOT include introductory words like "Here is the transcription" or markdown formatting codes that sound awkward when read aloud by TTS.
""",

    "explain": """You are an intelligent Voice Assistant tutor.
Look at the handwritten notes, calculations, or text shown in this image.
1. Transcribe the core ideas and handwriting accurately.
2. Then, explain the concept, problem, or message aloud in a warm, encouraging, conversational spoken tone as if speaking directly to the user.
3. Keep the spoken explanation concise, clear, and easy to understand when listened to.
4. Do NOT output conversational filler like "Sure!" or asterisks; output direct spoken sentences.
""",

    "summary": """You are an executive audio briefing assistant.
Look at the handwritten or printed notes in this image.
Extract the most critical key points and action items, and synthesize them into 2 to 4 crisp, spoken sentences that can be read aloud cleanly.
Output only the spoken sentences without bullet symbols or markdown asterisks.
""",

    "math": """You are a mathematical narrator for a speech assistant.
Look at the handwritten math formulas, equations, or scientific notes in this image.
Transcribe and verbalize them completely into phonetically spoken English words so that a voice synthesizer sounds completely natural.
For example:
- Transcribe "x^2 + 5 = 9" as "x squared plus five equals nine".
- Transcribe "H2O" as "H two O".
- Transcribe fractions like "1/2" as "one half".
- Transcribe square root symbols as "square root of ...".
Output ONLY the phonetically spoken text.
"""
}


class AIVisionEngine:
    def __init__(self, api_key: str = "", model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.client: Optional[genai.Client] = None
        if api_key:
            self._init_client()

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()
        self._init_client()

    def _init_client(self):
        try:
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = None
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            self.client = None

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Enhance image contrast and sharpness to make light pencil/pen
        handwriting strokes much easier for AI vision to decipher.
        """
        try:
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Boost contrast slightly for faint handwriting
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.25)
            
            # Sharpen edges of ink strokes
            sharpener = ImageEnhance.Sharpness(image)
            image = sharpener.enhance(1.3)
            
            return image
        except Exception:
            return image

    def recognize_screen_and_handwriting(self, image: Image.Image, mode: str = "direct") -> str:
        """
        Process the image and return the recognized text or voice narration.
        """
        if not self.api_key:
            return (
                "Gemini API key is required to read handwriting and screen text. "
                "Please click Settings or enter your API key to activate the assistant."
            )

        if not self.client:
            self._init_client()
            if not self.client:
                return "Failed to initialize Gemini Vision Client. Please check your API key."

        processed_img = self.preprocess_image(image)
        prompt = HANDWRITING_PROMPTS.get(mode, HANDWRITING_PROMPTS["direct"])

        try:
            # Generate content using Gemini multimodal vision
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[processed_img, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2,  # Low temperature for highest transcription accuracy
                    max_output_tokens=1024,
                )
            )

            text = response.text.strip() if response.text else ""
            if not text:
                return "No readable text or handwriting was detected in the selected area."
            
            # Clean up awkward markdown symbols that sound weird in TTS (e.g. **, ###, ---)
            cleaned = text.replace("**", "").replace("###", "").replace("##", "").replace("*", "")
            return cleaned.strip()

        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg or "400" in error_msg:
                return "Invalid Gemini API Key. Please verify your API key in Settings."
            elif "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                return "Rate limit reached. Please wait a moment before snipping again."
            return f"Recognition error: {error_msg}"

