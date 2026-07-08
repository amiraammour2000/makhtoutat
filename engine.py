# engine.py
import re
import hashlib
import logging
from typing import List, Dict, Any
import pyarabic.araby as araby
from lxml import etree

import dictionnaires_patrimoine as dp

# Configuration du logging professionnel
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PatrimoineNER")

# Regex chirurgicale pour supprimer UNIQUEMENT les diacritiques (Tashkeel)
# Cela préserve les Aléfs (أ إ آ) et les Yaa (ى ي) intacts !
TASHKEEL_REGEX = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]")

class MoteurExtraction:
    def __init__(self):
        self.intervals: List[tuple] = []

    def _chevauche(self, start: int, end: int) -> bool:
        return any(start < s_end and end > s_start for s_start, s_end in self.intervals)

    def _ajouter_interval(self, start: int, end: int):
        self.intervals.append((start, end))

    def nettoyer_texte_arabe(self, texte_brut: str) -> str:
        """Nettoyage chirurgical : Supprime les voyelles sans détruire les mots."""
        if not texte_brut:
            return ""
        
        # 1. Suppression stricte des Tashkeel (Notre propre regex au lieu de pyarabic)
        texte = TASHKEEL_REGEX.sub('', texte_brut)
        
        # 2. Normalisation des ligatures uniquement (لا -> ل ا)
        texte = araby.normalize_ligature(texte)
        
        # ATTENTION : On NE UTILISE PLUS normalize_hamza ni normalize_alef
        # Elles sont destructrices pour les noms propres et les textes modernes/classiques mixtes.
        
        # 3. Correction OCR basée sur le dictionnaire
        for pattern, correction in zip(dp.ERREURS_OCR, dp.CORRECTIONS_OCR):
            texte = pattern.sub(correction, texte)
            
        # 4. Nettoyage des caractères de ponctuation latins indésirables, 
        # on garde les espaces, les chiffres, et la ponctuation arabe
        texte = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s0-9.,؛:!؟\-\"\'«»()\n/]', '', texte)
        
        # 5. Normalisation des espaces
        texte = re.sub(r'\s+', ' ', texte).strip()
        return texte

    def extraire_entites(self, texte: str) -> List[Dict[str, Any]]:
        entites = []
        self.intervals = [] 

        # 1. Passes Dictionnaires
        for dico, type_entite in [(dp.LIEUX_HISTORIQUES, "Lieu"), (dp.PERSONNAGES_HISTORIQUES, "Personnalité")]:
            for nom, (sous_type, alias) in dico.items():
                cibles = [nom] + alias
                for cible in cibles:
                    pattern = re.compile(dp.ARABIC_WORD_BOUNDARY_LEFT + re.escape(cible) + dp.ARABIC_WORD_BOUNDARY_RIGHT)
                    for match in pattern.finditer(texte):
                        start, end = match.start(), match.end()
                        if not self._chevauche(start, end):
                            entites.append({"type": type_entite, "sous_type": sous_type, "entite": nom, "position": start, "confiance": 100})
                            self._ajouter_interval(start, end)

        # 2. Passe Structurelle
        for pattern in dp.STRUCTURES_NOMS:
            for match in pattern.finditer(texte):
                start, end = match.start(), match.end()
                if not self._chevauche(start, end):
                    entites.append({"type": "Personnalité", "sous_type": "Inconnu", "entite": match.group(), "position": start, "confiance": 85})
                    self._ajouter_interval(start, end)

        # 3. Passe Temporelle
        for match in dp.PATTERN_TEMPOREL.finditer(texte):
            start, end = match.start(), match.end()
            if not self._chevauche(start, end):
                entites.append({"type": "Date", "sous_type": "Chronologie", "entite": match.group().strip(), "position": start, "confiance": 90})
                self._ajouter_interval(start, end)

        for item in entites:
            start_ctx = max(0, item['position'] - 40)
            end_ctx = min(len(texte), item['position'] + len(item['entite']) + 40)
            item['contexte'] = texte[start_ctx:end_ctx]

        entites.sort(key=lambda x: x['position'])
        logger.info(f"Extraction terminée : {len(entites)} entités trouvées.")
        return entites

    @staticmethod
    def generer_hash_sha256(texte: str) -> str:
        return hashlib.sha256(texte.encode('utf-8')).hexdigest()

    @staticmethod
    def generer_tei_xml(texte: str, entites: List[Dict[str, Any]]) -> str:
        nsmap = {'tei': 'http://www.tei-c.org/ns/1.0'}
        TEI = "{%s}" % nsmap['tei']
        
        root = etree.Element(TEI + "TEI", nsmap=nsmap)
        tei_header = etree.SubElement(root, TEI + "teiHeader")
        file_desc = etree.SubElement(tei_header, TEI + "fileDesc")
        title_stmt = etree.SubElement(file_desc, TEI + "titleStmt")
        etree.SubElement(title_stmt, TEI + "title").text = "Manuscrit Indexé - TechCulture"
        
        text_node = etree.SubElement(root, TEI + "text")
        body = etree.SubElement(text_node, TEI + "body")
        
        tag_map = {"Personnalité": "persName", "Lieu": "placeName", "Date": "date"}
        last_node = body
        last_pos = 0

        for item in entites:
            start = item['position']
            end = start + len(item['entite'])
            txt_before = texte[last_pos:start]
            
            if last_node is body:
                last_node.text = (last_node.text or "") + txt_before
            else:
                last_node.tail = (last_node.tail or "") + txt_before

            elem = etree.SubElement(body, TEI + tag_map.get(item['type'], "rs"))
            elem.set("type", item.get('sous_type', 'unknown'))
            elem.set("cert", "high" if item['confiance'] == 100 else "medium")
            elem.text = item['entite']
            
            last_node = elem
            last_pos = end
            
        txt_after = texte[last_pos:]
        if last_node is body:
            last_node.text = (last_node.text or "") + txt_after
        else:
            last_node.tail = (last_node.tail or "") + txt_after

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode('utf-8')