"""
OCR path for scanned PDFs and photographed/screenshotted statements.
Tesseract (open-source, no API, no per-page cost) + OpenCV preprocessing.
This path has meaningfully lower accuracy than the text-PDF path — always
surfaces lower confidence scores so more rows get routed to human review.
"""
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

from app.core.config import get_settings

settings = get_settings()
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


@dataclass
class OCRWord:
    page_number: int
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float  # Tesseract's own per-word confidence, 0-100


def _preprocess(image: np.ndarray) -> np.ndarray:
    """Deskew, denoise, and binarize — meaningfully improves Tesseract
    accuracy on real-world phone-photo statements vs. raw OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(binary > 0))
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    (h, w) = binary.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(binary, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC)
    return deskewed


def extract_words_from_pdf(pdf_path: str, dpi: int = 300) -> list[OCRWord]:
    words: list[OCRWord] = []
    pages = convert_from_path(pdf_path, dpi=dpi)
    for page_number, pil_image in enumerate(pages, start=1):
        image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        processed = _preprocess(image)
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)

        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            words.append(
                OCRWord(
                    page_number=page_number,
                    text=text,
                    x=data["left"][i],
                    y=data["top"][i],
                    width=data["width"][i],
                    height=data["height"][i],
                    confidence=float(data["conf"][i]),
                )
            )
    return words
