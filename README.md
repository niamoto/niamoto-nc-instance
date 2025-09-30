# Instance Niamoto - Déploiement

Cette instance Niamoto est prête pour le déploiement sur Coolify.

**Note importante** : Cette instance utilise la branche `feat/pipeline-editor-unified` du repository Niamoto pour avoir accès aux dernières fonctionnalités de l'interface graphique.

## Prérequis

Avant de déployer, assurez-vous que :
1. Votre branche `feat/pipeline-editor-unified` est poussée sur GitHub
2. Le commit contenant les dernières modifications du GUI est présent sur cette branche

```bash
# Depuis le repository principal Niamoto
cd /Users/julienbarbe/Dev/Niamoto/Niamoto
git push origin feat/pipeline-editor-unified
```

## Déploiement sur Coolify

### 1. Créer un repository Git pour cette instance

```bash
cd /Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-og
git init
git add .
git commit -m "Initial commit - Niamoto instance with feat/pipeline-editor-unified"
```

### 2. Pusher vers un repository distant (GitHub/GitLab)

```bash
# Créez un repo sur GitHub (ex: niamoto-instance)
git remote add origin git@github.com:yourusername/niamoto-instance.git
git branch -M main
git push -u origin main
```

### 3. Déployer dans Coolify

1. Connectez-vous à Coolify
2. Créez un nouveau projet
3. Choisissez "Deploy from Git Repository"
4. Connectez votre repository `niamoto-instance`
5. Coolify détectera automatiquement le Dockerfile
6. Configuration :
   - **Port** : 8080
   - **Health Check Path** : `/api/config/project`
7. Déployez !

### 4. Accéder à votre application

- GUI : `https://votre-domaine.com`
- API : `https://votre-domaine.com/api/docs`
- Preview : `https://votre-domaine.com/preview/`

## Option alternative : Déploiement avec Docker Compose

Si vous préférez Docker Compose dans Coolify :

```yaml
version: '3.8'

services:
  niamoto:
    build: .
    ports:
      - "8080:8080"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/config/project"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Mise à jour de l'instance

Pour mettre à jour les données ou la configuration :

1. Modifiez les fichiers localement
2. Committez et pushez :
   ```bash
   git add .
   git commit -m "Update configuration"
   git push
   ```
3. Dans Coolify, cliquez sur "Redeploy"

## Variables d'environnement (optionnel)

Si besoin, configurez dans Coolify :
```
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

## Structure

```
.
├── config/          # Configuration YAML (import, transform, export)
├── db/              # Base de données SQLite
├── imports/         # Données sources
├── exports/         # Exports générés
│   └── web/         # Site statique
├── plugins/         # Plugins personnalisés
├── templates/       # Templates personnalisés
└── Dockerfile       # Configuration Docker
```