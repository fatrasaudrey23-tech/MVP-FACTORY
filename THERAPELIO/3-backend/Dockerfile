# Utilise une version légère et stable de Python
FROM python:3.9-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier requirements.txt et installe les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste de ton code backend dans le conteneur
COPY . .

# Expose le port 8001 sur lequel ton API écoute
EXPOSE 8001

# Commande pour lancer l'application avec Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]