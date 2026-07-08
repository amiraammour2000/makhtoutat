# vision_engine.py
import cv2
import numpy as np
import logging
import warnings

# On cache les warnings inutiles de PaddleOCR 3.x qui cherchent torchvision
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
            # API PaddleOCR v3 : L'argument show_log a été supprimé.
            # use_angle_cls est géré automatiquement dans la v3.
            self._ocr = PaddleOCR(lang='ar')
        return self._ocr

    def _bytes_to_image(self, image_bytes: bytes) -> np.ndarray:
        """Convertit les bytes de l'image (RAM) en array NumPy."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Impossible de décoder l'image. Le fichier est corrompu.")
        return img

    def pretraiter_manuscrit(self, img: np.ndarray) -> np.ndarray:
        """Prétraitement chirurgical sur l'image en mémoire."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def extraire_texte(self, image_bytes: bytes, use_preprocessing: bool = True) -> str:
        """Pipeline complet 100% en mémoire vive."""
        logger.info("Début de l'extraction OCR depuis la mémoire (Bytes)...")
        
        # 1. Conversion Bytes -> Image
        img = self._bytes_to_image(image_bytes)
        
        # 2. Prétraitement
        img_to_feed = self.pretraiter_manuscrit(img) if use_preprocessing else img
        
        # 3. OCR (On n'ajoute plus cls=True, la v3 le gère seule)
        ocr_model = self._get_ocr_model()
        resultats = ocr_model.ocr(img_to_feed)
        
        # 4. Aggrégation (Compatible v2 et v3)
        texte_final = []
        if resultats and len(resultats) > 0 and resultats[0]:
            for ligne in resultats[0]:
                try:
                    # PaddleOCR v3 peut retourner un Dictionnaire ou un Tuple selon les modèles
                    if isinstance(ligne, dict):
                        text = ligne.get('rec_text', ligne.get('text', ''))
                        score = ligne.get('score', 1.0)
                    elif isinstance(ligne, (list, tuple)) and len(ligne) >= 2:
                        text = ligne[1][0] if isinstance(ligne[1], (list, tuple)) else str(ligne[1])
                        score = ligne[1][1] if isinstance(ligne[1], (list, tuple)) else 1.0
                    else:
                        continue
                    
                    if score > 0.5 and text.strip(): 
                        texte_final.append(text.strip())
                except Exception as e:
                    logger.warning(f"Impossible de lire une ligne OCR: {e}")
                    continue
                    
        return "\n".join(texte_final)