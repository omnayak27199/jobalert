from __future__ import annotations

"""Extract text from PDF bytes — pdfplumber first, OCR for scanned/noisy PDFs."""

import logging
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from io import BytesIO

import pdfplumber

from app.services.content_quality import document_text_is_usable, text_quality_score

logger = logging.getLogger(__name__)

MIN_USABLE_TEXT = 40
MIN_QUALITY_RATIO = 0.55
MIN_WORD_RATIO = 0.12
OCR_MAX_PAGES = 3
OCR_DPI = 110
OCR_TIMEOUT_SECONDS = 45


def _tesseract_cmd() -> str:
    return shutil.which("tesseract") or "/usr/bin/tesseract"


def _text_quality(text: str) -> float:
    """0–1 score: high for normal English/Hindi PDF text, low for OCR garbage."""
    if not text:
        return 0.0
    sample = text[:8000]
    if len(sample) < 20:
        return 0.0

    alnum = sum(1 for c in sample if c.isalnum())
    spaces = sum(1 for c in sample if c.isspace())
    weird = sum(1 for c in sample if c in "^■□▪●▫◆◇★☆▲►◄▶◀♦♠♣♥`~|\\")
    words = re.findall(r"[A-Za-z]{3,}", sample)
    word_chars = sum(len(w) for w in words)

    base = (alnum + spaces) / len(sample)
    word_ratio = word_chars / len(sample)
    penalty = min(0.4, weird / max(len(sample), 1) * 8)

    # Many short tokens like "srnft^" indicate bad extraction
    short_tokens = len(re.findall(r"\b\w{1,2}\b", sample))
    short_penalty = min(0.25, short_tokens / max(len(sample.split()), 1) * 0.15)

    return max(0.0, min(1.0, base * 0.55 + word_ratio * 2.5 - penalty - short_penalty))


def is_text_usable(text: str) -> bool:
    return (
        len(text.strip()) >= MIN_USABLE_TEXT
        and document_text_is_usable(text)
    )


def _extract_with_pdfplumber(data: bytes, max_pages: int = 40) -> str:
    parts: list[str] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages[:max_pages]:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
    return "\n".join(parts).strip()


def _extract_with_ocr(data: bytes, max_pages: int = 12) -> str:
    """OCR fallback for image-only PDFs. Requires tesseract + poppler."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError:
        return ""

    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()

    try:
        images = convert_from_bytes(
            data,
            first_page=1,
            last_page=max_pages,
            dpi=OCR_DPI,
            fmt="jpeg",
            thread_count=2,
        )
    except Exception as exc:
        logger.debug("pdf2image failed: %s", exc)
        return ""

    langs = ("hin+eng", "eng")
    parts: list[str] = []
    for image in images:
        text = ""
        for lang in langs:
            try:
                text = pytesseract.image_to_string(image, lang=lang, config="--psm 6 -c preserve_interword_spaces=1")
                if text and text_quality_score(text) >= 0.35:
                    break
            except Exception as exc:
                logger.debug("OCR page failed (%s): %s", lang, exc)
        if text and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()


def _extract_with_ocr_timed(data: bytes, max_pages: int) -> str:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_extract_with_ocr, data, max_pages)
        try:
            return future.result(timeout=OCR_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            logger.warning("OCR timed out after %ss", OCR_TIMEOUT_SECONDS)
            return ""


def extract_pdf_text(data: bytes, *, max_pages: int = 40, allow_ocr: bool = True) -> str:
    """Return best-effort text from a PDF (Devanagari + Latin)."""
    plumber_text = _extract_with_pdfplumber(data, max_pages=max_pages)

    if is_text_usable(plumber_text):
        return plumber_text

    if not allow_ocr:
        return plumber_text

    # Font-mapped garbage on large PDFs: OCR is too slow — rely on filename/metadata fallback.
    if len(plumber_text) > 8000 and not document_text_is_usable(plumber_text):
        logger.info(
            "Skipping OCR for garbled PDF text (%d chars, quality %.2f)",
            len(plumber_text),
            text_quality_score(plumber_text),
        )
        return plumber_text

    ocr_text = _extract_with_ocr_timed(data, max_pages=min(OCR_MAX_PAGES, max_pages))
    if not ocr_text:
        return plumber_text

    plumber_q = text_quality_score(plumber_text)
    ocr_q = text_quality_score(ocr_text)

    if ocr_q > plumber_q + 0.05 or not document_text_is_usable(plumber_text):
        logger.info(
            "Using OCR text (quality %.2f vs pdfplumber %.2f, len %d vs %d)",
            ocr_q,
            plumber_q,
            len(ocr_text),
            len(plumber_text),
        )
        return ocr_text

    return plumber_text
