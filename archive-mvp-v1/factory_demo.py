import os
import glob

print("🎬 Démarrage de l'Intégrateur Frontend (Architecture Dynamique Native)...")

# 1. On liste les fichiers
fichiers_code = glob.glob("*_code_genere.py")

if not fichiers_code:
    print("📭 Aucun fichier de code généré trouvé.")
    exit()

print(f"📦 {len(fichiers_code)} modules détectés. Création du tableau de bord...")

# 2. Le script du Dashboard Infaillible (bien protégé par ses triples guillemets)
code_dashboard = """import streamlit as st
import glob
import importlib.util
import sys
import io
import inspect
from contextlib import redirect_stdout

st.set_page_config(page_title="Tableau de Bord MVP", layout="wide")

st.sidebar.title("🧩 Modules du Projet")
fichiers = sorted(glob.glob("*_code_genere.py"))

if not fichiers:
    st.info("Aucun module à afficher.")
else:
    noms_propres = {f: f.replace("_code_genere.py", "").replace("_", " ") for f in fichiers}
    choix_nom = st.sidebar.radio("Navigation :", list(noms_propres.values()))
    fichier_choisi = [f for f, nom in noms_propres.items() if nom == choix_nom][0]
    
    st.header(f"🚀 {choix_nom}")
    st.markdown("---")
    
    try:
        capture_terminal = io.StringIO()
        
        with redirect_stdout(capture_terminal):
            spec = importlib.util.spec_from_file_location("module_dynamique", fichier_choisi)
            module_dynamique = importlib.util.module_from_spec(spec)
            sys.modules["module_dynamique"] = module_dynamique
            spec.loader.exec_module(module_dynamique)
            
            # Le cerveau du Dashboard : exécution adaptative
            for func_name in ['main', 'app', 'run']:
                if hasattr(module_dynamique, func_name):
                    func = getattr(module_dynamique, func_name)
                    sig = inspect.signature(func)
                    
                    if len(sig.parameters) > 0:
                        try:
                            func(None)
                        except:
                            func([])
                    else:
                        func()
                    break
                    
        logs = capture_terminal.getvalue()
        if logs:
            st.subheader("🖥️ Résultat de l'exécution :")
            st.code(logs, language="bash")
            
    except Exception as e:
        st.error(f"⚠️ L'Agent a rencontré une erreur technique : {e}")
"""

# 3. Sauvegarde immédiate
nom_fichier_demo = "main_demo.py"
with open(nom_fichier_demo, "w", encoding="utf-8") as f:
    f.write(code_dashboard.strip())

print(f"\n🎉 [SUCCÈS] Le tableau de bord Web '{nom_fichier_demo}' a été généré instantanément !")
print("🚀 Lance-le avec : python3 -m streamlit run main_demo.py")