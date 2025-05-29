#!/bin/bash

set -e

echo "🚀 Début du déploiement..."

# Variables
PROJECT_DIR="/home/khalil/tunis-gp25"
BRANCH="main"

cd $PROJECT_DIR

# Vérifier que nous sommes dans un repo git
if [ ! -d ".git" ]; then
    echo "❌ Erreur: Ce n'est pas un repository git"
    exit 1
fi

echo "📥 Récupération des dernières modifications..."

# Sauvegarder le fichier .env s'il existe
if [ -f ".env" ]; then
    cp .env .env.backup
fi

# Annuler toutes les modifications locales
git fetch origin
git reset --hard origin/$BRANCH
git clean -fd

# Restaurer le fichier .env
if [ -f ".env.backup" ]; then
    mv .env.backup .env
fi

# Forcer le pull
git pull origin $BRANCH --force

echo "🛑 Arrêt des containers existants..."
docker-compose down || true

# Nettoyer les images inutilisées (garde les volumes)
docker system prune -f

echo "🔧 Construction et démarrage des containers..."
docker-compose build --no-cache
docker-compose up -d

echo "⏳ Attente du démarrage des services..."
sleep 20

# Attendre que PostgreSQL soit prêt
echo "🔍 Attente de PostgreSQL..."
until docker exec postgres_tunis_gp25 pg_isready -U ${POSTGRES_USER:-tunis_user} -d ${POSTGRES_DB:-tunis_gp25_db}; do
  echo "PostgreSQL n'est pas encore prêt - attente..."
  sleep 2
done

# Test de connectivité à la base de données
echo "🔍 Test de connexion à PostgreSQL..."
docker exec flask_tunis_gp25 python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('✅ Connexion PostgreSQL OK')
    conn.close()
except Exception as e:
    print(f'❌ Erreur PostgreSQL: {e}')
    exit(1)
"

# Vérifier que les containers sont en cours d'exécution
if docker-compose ps | grep -q "Up"; then
    echo "✅ Déploiement réussi!"
    echo "📊 Status des containers:"
    docker-compose ps
    echo ""
    echo "🌐 Application accessible sur:"
    echo "   - http://tunis-gp25.npctunisia.com"
    echo "   - http://www.tunis-gp25.npctunisia.com"
    echo ""
    echo "🗄️  PostgreSQL accessible sur:"
    echo "   - Host: $(hostname -I | awk '{print $1}')"
    echo "   - Port: 1598"
    echo "   - Database: ${POSTGRES_DB:-tunis_gp25_db}"
    echo "   - User: ${POSTGRES_USER:-tunis_user}"
else
    echo "❌ Erreur lors du déploiement"
    echo "📋 Logs des containers:"
    docker-compose logs
    exit 1
fi
