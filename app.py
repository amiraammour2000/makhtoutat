# app.py
import sys
import subprocess

# --- CHIRURGICAL FIX FOR STREAMLIT CLOUD (Headless Server) ---
# PaddleOCR force l'installation d'OpenCV GUI, ce qui crashe le serveur sans écran.
# On le désinstalle silencieusement pour forcer l'utilisation de la version "headless".
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "opencv-python", "opencv-contrib-python"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
# -------------------------------------------------------------
import streamlit as st
import xml.dom.minidom
import os
from engine import MoteurExtraction
from vision_engine import VisionEngine

# Configuration UI Professionnelle
st.set_page_config(page_title="TechCulture AI Studio", page_icon="📜", layout="wide")
hide_st_style = """<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .block-container {padding-top: 2rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #1a1a1a;'>TechCulture AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Moteur d'Indexation Sémantique & OCR de Manuscrits Arabes</p>", unsafe_allow_html=True)
st.divider()

# Initialisation des moteurs
if "moteur_ner" not in st.session_state:
    st.session_state.moteur_ner = MoteurExtraction()
if "moteur_vision" not in st.session_state:
    st.session_state.moteur_vision = VisionEngine()

# Fonction d'affichage des résultats (Factorisée)
def afficher_resultats(texte_nettoye, entites, hash_doc, xml_output):
    st.success("✅ Pipeline d'analyse terminé avec succès !")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Entités trouvées", len(entites))
    col_m2.metric("Personnalités", sum(1 for e in entites if e['type'] == 'Personnalité'))
    col_m3.metric("Lieux", sum(1 for e in entites if e['type'] == 'Lieu'))
    col_m4.metric("Dates", sum(1 for e in entites if e['type'] == 'Date'))
    
    tab1, tab2, tab3 = st.tabs(["📝 Texte Nettoyé", "🔍 Entités Sémantiques", "🌳 Standard TEI-XML"])
    with tab1:
        st.text_area("Texte traité par le moteur :", texte_nettoye, height=250)
        st.caption(f"Hash SHA-256 : `{hash_doc}`")
    with tab2:
        if not entites: st.info("Aucune entité n'a été identifiée.")
        for ent in entites:
            couleur = {"Personnalité": "🟢", "Lieu": "🔵", "Date": "🟠"}.get(ent['type'], "⚪")
            st.markdown(f"{couleur} **{ent['entite']}** (`{ent['type']}` - {ent['sous_type']}) *Confiance: {ent['confiance']}%*")
            st.caption(f"Contexte : *...{ent['contexte']}...*")
    with tab3:
        xml_pretty = xml.dom.minidom.parseString(xml_output).toprettyxml(indent="  ")
        st.code(xml_pretty, language='xml')
        st.download_button("⬇️ Télécharger TEI-XML", xml_output, file_name="manuscrit_tei.xml", mime="application/xml")

# --- INTERFACE A DOUBLE VOIE ---
mode_choisi = st.tabs(["📝 Mode Texte (Saisie)", "📜 Mode Vision (Manuscrit Image)"])

# =====================================================================
# ONGLET 1 : MODE TEXTE
# =====================================================================
with mode_choisi[0]:
    st.markdown("### Saisie directe de texte arabe")
    
    # Vérification du chargement du dictionnaire (Optionnel mais utile pour le débug)
    try:
        import dictionnaires_patrimoine as dp
        st.caption(f"🔧 Version du dictionnaire chargée : **{dp.VERSION_DICT}**")
    except Exception as e:
        st.caption(f"⚠️ Erreur de chargement du dictionnaire : {e}")

    # Zone de saisie UNIQUE avec une clé explicite pour éviter l'erreur DuplicateWidgetID
    texte_brut = st.text_area(
        "Collez votre texte ici :", 
        height=300, 
        placeholder="بسم الله الرحمن الرحيم...",
        key="zone_saisie_texte_arabe" # <-- CECI RÈGLE LE PROBLÈME
    )
    
    if st.button("Analyser le texte", type="primary", use_container_width=True):
        if texte_brut.strip():
            with st.spinner("Nettoyage linguistique et extraction en cours..."):
                m = st.session_state.moteur_ner
                texte_nettoye = m.nettoyer_texte_arabe(texte_brut)
                entites = m.extraire_entites(texte_nettoye)
                hash_doc = m.generer_hash_sha256(texte_brut)
                xml_output = m.generer_tei_xml(texte_nettoye, entites)
                afficher_resultats(texte_nettoye, entites, hash_doc, xml_output)
        else:
            st.warning("Veuillez saisir du texte avant de lancer l'analyse.")

# =====================================================================
# ONGLET 2 : MODE VISION
# =====================================================================
with mode_choisi[1]:
    st.markdown("### Reconnaissance Optique de Manuscrits (OCR)")
    col_img1, col_img2 = st.columns([1, 2])
    with col_img1:
        fichier_uploade = st.file_uploader("Chargez l'image du manuscrit", type=["jpg", "jpeg", "png"], key="upload_image")
        pretraitement_actif = st.checkbox("Pré-traitement chirurgical OpenCV (Recommandé)", value=True)
    with col_img2:
        if fichier_uploade: 
            st.image(fichier_uploade, use_column_width=True, caption="Aperçu du document source")
    
    if st.button("Lancer l'OCR et l'Analyse", type="primary", use_container_width=True, disabled=not fichier_uploade):
        try:
            with st.spinner("🧠 Étape 1/2 : Vision par ordinateur (PaddleOCR)..."):
                # On lit directement les bytes depuis Streamlit. Plus de fichier temporaire !
                image_bytes = fichier_uploade.getvalue()
                texte_ocr_brut = st.session_state.moteur_vision.extraire_texte(image_bytes, use_preprocessing=pretraitement_actif)
                
            if not texte_ocr_brut.strip():
                st.error("Aucun texte extrait. Vérifiez la qualité de l'image.")
            else:
                with st.spinner("🔬 Étape 2/2 : Nettoyage NLP et Extraction (NER)..."):
                    m = st.session_state.moteur_ner
                    texte_nettoye = m.nettoyer_texte_arabe(texte_ocr_brut)
                    entites = m.extraire_entites(texte_nettoye)
                    hash_doc = m.generer_hash_sha256(texte_nettoye)
                    xml_output = m.generer_tei_xml(texte_nettoye, entites)
                    afficher_resultats(texte_nettoye, entites, hash_doc, xml_output)
                    
        except Exception as e:
            st.error(f"Erreur critique lors de l'OCR : {e}")
