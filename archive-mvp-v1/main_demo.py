import streamlit as st
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