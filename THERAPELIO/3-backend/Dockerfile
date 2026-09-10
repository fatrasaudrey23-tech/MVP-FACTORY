# Utilise une version légère et stable de Python
# (3.12 : le SDK Anthropic 1.x, utilisé pour l'IA conversationnelle, exige Python >= 3.10)
FROM python:3.12-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier requirements.txt et installe les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste de ton code backend dans le conteneur
COPY . .

# Port fourni par l'hébergeur (Clever Cloud impose $PORT) ; 8001 par défaut en local
ENV PORT=8001
EXPOSE $PORT

# Commande pour lancer l'application avec Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port $PORT