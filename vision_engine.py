# vision_engine.py
import cv2
import numpy as np
import logging
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger("VisionEngine")

class VisionEngine:
    def __init__(self):
        self._ocr = None

    def _get_ocr_model(self):
        if self._ocr is None:
            logger.info("Chargement de PaddleOCR v3 (Arabe)...")
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR()
        return self._ocr

    def _bytes_to_image(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Impossible de décoder l'image.")
        return img

    def pretraiter_manuscrit(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def extraire_texte(self, image_bytes: bytes, use_preprocessing: bool = True) -> str:
        logger.info("Début de l'extraction OCR...")
        img = self._bytes_to_image(image_bytes)
        img_to_feed = self.pretraiter_manuscrit(img) if use_preprocessing else img
        
        ocr_model = self._get_ocr_model()
        resultats = ocr_model.ocr(img_to_feed)
        
        texte_final = []
        if resultats and len(resultats) > 0 and resultats[0]:
            for ligne in resultats[0]:
                try:
                    text = ""
                    score = 0.0
                    
                    # Gestion intelligente du format (Dict vs Tuple)
                    if isinstance(ligne, dict):
                        text = ligne.get('rec_text', ligne.get('text', ''))
                        score = ligne.get('score', 1.0)
                    elif isinstance(ligne, (list, tuple)) and len(ligne) >= 2:
                        info = ligne[1]
                        if isinstance(info, dict):
                            text = info.get('rec_text', info.get('text', ''))
                            score = info.get('score', 1.0)
                        elif isinstance(info, (list, tuple)):
                            text = str(info[0]) if len(info) >= 1 else ""
                            score = info[1] if len(info) >= 2 else 1.0
                        elif isinstance(info, str):
                            text = info
                    
                    if score > 0.5 and text.strip(): 
                        texte_final.append(text.strip())
                except Exception as e:
                    logger.warning(f"Ignore ligne OCR: {e}")
                    continue
                    
        return "\n".join(texte_final)
