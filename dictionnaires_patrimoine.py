# dictionnaires_patrimoine.py
import re
from typing import Dict, List, Tuple, Pattern

# Catalogue des lieux
LIEUX_HISTORIQUES: Dict[str, Tuple[str, List[str]]] = {
    "ورقلة": ("Oasis", ["الورقلة", "ورقهلة"]),
    "غرداية": ("Ville", ["غردايت", "الغرداية"]),
    "بسكرة": ("Ville", ["بسكرة"]),
    "تمنراست": ("Ville", ["تمنراست"]),
    "إليزي": ("Ville", ["إليزي", "الإليزي"]),
    "تقرت": ("Oasis", ["تقرت"]),
    "المنيعة": ("Oasis", ["المنيعة"]),
    "زاوية كنتة": ("Zaouïa", ["زاوية كنتة"]),
    "عين صالح": ("Oasis", ["عين صالح"]),
    "وادي ميا": ("Vallée", ["وادي ميا", "وادي مياء"]),
    "تازركت": ("Ksar", ["تازركت"])
}

# Catalogue des personnages
PERSONNAGES_HISTORIQUES: Dict[str, Tuple[str, List[str]]] = {
    "الشيخ سيدي محمد بن عبد الرحمان": ("Savant", []),
    "أبي العباس أحمد": ("Auteur", ["أبو العباس أحمد"]),
    "سيدي عبد القادر الجيلاني": ("Figure religieuse", []),
    "ابن خلدون": ("Historien", []),
    "الشيخ بيضاوي": ("Savant", []),
    "التميمي": ("Tribu/Savant", [])
}

# Structures syntaxiques
STRUCTURES_NOMS: List[Pattern] = [
    re.compile(r"عبد\s+\w+\s+بن\s+\w+"),
    re.compile(r"أبو\s+\w+\s+\w+"),
    re.compile(r"بن\s+\w+\s+\w+"),
    re.compile(r"الشيخ\s+\w+")
]

ERREURS_OCR: List[Pattern] = [re.compile(r"الل[هة]"), re.compile(r"سلسم"), re.compile(r"علي[هة]"), re.compile(r"إل[يى]")]
CORRECTIONS_OCR: List[str] = ["الله", "سلم", "عليه", "إلى"]

MARQUEURS_TEMPORELS: List[str] = ["سنة", "عام", "في شهر", "أواخر", "أوائل"]

# --- LA NOUVELLE REGEX CHIRURGICALE (V2.1) ---
# Elle englobe "هجري" et "ميلادي" au complet, et rejette le "م" isolé grâce au Lookahead négatif
PATTERN_TEMPOREL: Pattern = re.compile(
    r'(?:(?:' + '|'.join(MARQUEURS_TEMPORELS) + r')\s+)?'
    r'\d{3,4}\s*'
    r'(?:'
    r'هـ|'
    r'هجرية?|'
    r'ميلاد[يى]?|'
    r'م(?![\u0600-\u06FF])' 
    r')?'
)

ARABIC_WORD_BOUNDARY_LEFT = r"(?<![\u0600-\u06FF])"
ARABIC_WORD_BOUNDARY_RIGHT = r"(?![\u0600-\u06FF])"

# Marqueur de version pour vérifier que le bon fichier est chargé
VERSION_DICT = "V2.1_CHIRURGICAL"