#!/usr/bin/env bash
# Script de lancement rapide pour Apple Music To Video

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Vérification de python3
if ! command -v python3 &> /dev/null; then
    echo "Erreur: Python 3 est requis pour exécuter cette application."
    exit 1
fi

# Exécution de l'application
python3 main.py "$@"
