import streamlit as st
import json
import ECOMENU_14_code_genere as eco_brain

st.set_page_config(page_title="EcoMenu MVP", page_icon="🌱", layout="wide")

st.title("🌱 Démo EcoMenu Dynamique")
st.write("Ajustez vos variables dans le menu de gauche et laissez l'algorithme faire le reste !")

# --- 1. BARRE LATÉRALE : LES VARIABLES DYNAMIQUES ---
st.sidebar.header("⚙️ Vos Préférences")

# On crée des sliders et champs que l'utilisateur peut modifier
budget_dynamique = st.sidebar.slider("Budget maximum (€)", min_value=10.0, max_value=150.0, value=40.0, step=5.0)
jours_dynamiques = st.sidebar.slider("Nombre de jours", min_value=1, max_value=7, value=3)
calories_min_dynamiques = st.sidebar.number_input("Calories minimum / jour", min_value=500, max_value=3000, value=800)

# --- 2. LE BOUTON MAGIQUE ---
if st.button("🪄 Générer mon menu optimisé", type="primary"):
    with st.spinner("Le moteur mathématique réfléchit..."):
        
        # 3. ON CRÉE LE FICHIER DE PRÉFÉRENCES À LA VOLÉE
        preferences = {
            "num_days": jours_dynamiques,
            "meals_per_day": ["lunch", "dinner"],
            "allergies": [],
            "dietary_restrictions": [], 
            "max_budget": budget_dynamique, 
            "optimization_goal": "minimize_cost",
            "min_calories_per_day": calories_min_dynamiques, 
            "max_calories_per_day": 2500,
            "min_protein_per_day": 20,
            "max_same_recipe_freq_days": 1
        }
        
        # On écrit physiquement tes choix dans le fichier JSON avant de lancer le calcul
        with open("preferences.json", "w", encoding="utf-8") as f:
            json.dump(preferences, f, indent=4)
            
        # 4. ON LANCE L'ALGORITHME
        results = eco_brain.main("config.json", "preferences.json")
        
        # --- 5. AFFICHAGE DES RÉSULTATS ---
        if results["status"] in ["Optimal", "Feasible"]:
            st.success("Menu généré avec succès !")
            st.metric(label="💰 Coût total estimé", value=f"{results['objective_value']:.2f} €")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🍽️ Votre Menu")
                for meal in results["optimized_menu"]:
                    st.info(f"**Jour {meal['day']} - {meal['meal_type'].capitalize()}**\n\n{meal['recipe']['name']}")
                    
            with col2:
                st.subheader("🛒 Liste de courses")
                for item, details in results["shopping_list"].items():
                    st.write(f"✅ {item} : **{details['quantity']}** {details['unit']}")
                    
        else:
            st.error(f"Le budget est peut-être trop serré ! Impossible de trouver un menu. Statut : {results['status']}")