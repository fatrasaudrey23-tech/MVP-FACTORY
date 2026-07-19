import os
import subprocess
import json

def verifier_qualite_backend(projet_nom):
    """Vérification non-destructive : alerte au lieu de supprimer."""
    chemin_main = os.path.join(projet_nom, "3-backend", "main.py")
    chemin_contrat = os.path.join(projet_nom, "api_contract.json")
    
    if not os.path.exists(chemin_main):
        print("❌ Fichier main.py introuvable.")
        return

    with open(chemin_main, "r", encoding="utf-8") as f:
        contenu = f.read()

    erreurs = []

    # 1. Vérification CORS
    if "CORSMiddleware" not in contenu:
        erreurs.append("CORS manquant")

    # 2. Vérification Contrat
    if os.path.exists(chemin_contrat):
        with open(chemin_contrat, "r", encoding="utf-8") as f:
            contrat = json.load(f)
            for route in contrat.get("routes", []):
                route_base = route.split("/{")[0]
                if route_base not in contenu:
                    erreurs.append(f"Route {route} manquante")

    if erreurs:
        print(f"⚠️ AVERTISSEMENT : Le backend généré présente des lacunes : {', '.join(erreurs)}")
        print("👉 Veuillez vérifier manuellement le fichier main.py.")
    else:
        print("✅ Backend validé avec succès.")

def orchestrateur():
    print("\n🏭 NEXUS FLOW - ORCHESTRATEUR STABILISÉ")
    
    dossiers = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")]
    for i, dossier in enumerate(dossiers, 1):
        print(f"[{i}] {dossier}")
    
    projet = input("\n👉 Projet ? : ")

    scripts = [
        "factory_po.py", "factory_architect.py", "factory_database.py",
        "factory_worker.py", "factory_backend.py", "factory_frontend.py"
    ]

    for script in scripts:
        if os.path.exists(script):
            print(f"--- Exécution : {script} ---")
            subprocess.run(["python3", script], input=f"{projet}\n", text=True)
            if script == "factory_backend.py":
                verifier_qualite_backend(projet)
        
    print("\n✅ PRODUCTION TERMINÉE. Aucun fichier n'a été supprimé.")

if __name__ == "__main__":
    orchestrateur()