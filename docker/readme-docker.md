# ============================================================
# Docker Compose - Guide d'utilisation
# ============================================================

## Démarrer l'environnement Docker complet
Pour construire et démarrer tous les services en arrière-plan :
```bash
docker compose up -d --build
```

## Accès aux services web

### Via ports directs (localhost)
- **Rodelika Web** : http://localhost:8081
- **Berlicum Web** : http://localhost:8082
- **Lunar White Web** : http://localhost:8083
- **Traefik Dashboard** : http://localhost:8080

### Via noms de domaine (Traefik)
- **Rodelika Web** : http://rodelika.crous-78.uvsq.fr
- **Berlicum Web** : http://berlicum.crous-78.uvsq.fr
- **Lunar White Web** : http://lunarwhite.crous-78.uvsq.fr

> **Note** : Pour utiliser les noms de domaine, vous devez configurer votre fichier `/etc/hosts` (Linux/Mac) ou `C:\Windows\System32\drivers\etc\hosts` (Windows) :
> ```
> 127.0.0.1 rodelika.crous-78.uvsq.fr
> 127.0.0.1 berlicum.crous-78.uvsq.fr
> 127.0.0.1 lunarwhite.crous-78.uvsq.fr
> ```

## Lancer les services CLI uniquement

### CLI - Rodelika
```bash
docker compose run --rm rodelika-cli
```

### CLI - Berlicum
```bash
docker compose run --rm berlicum-cli
```

### CLI - Lubiana
```bash
docker compose run --rm lubiana-cli
```

## Commandes utiles

### Arrêter tous les services
```bash
docker compose down
```

### Arrêter et supprimer les volumes (⚠️ supprime les données)
```bash
docker compose down -v
```

### Voir les logs d'un service
```bash
docker compose logs -f <nom-du-service>
# Exemples :
docker compose logs -f rodelika-web
docker compose logs -f purple-dragon-db
```

### Voir les logs de tous les services
```bash
docker compose logs -f
```

### Redémarrer un service spécifique
```bash
docker compose restart <nom-du-service>
# Exemple :
docker compose restart berlicum-web
```

### Reconstruire un service spécifique
```bash
docker compose up -d --build <nom-du-service>
# Exemple :
docker compose up -d --build lunar-white
```

### Vérifier l'état des services
```bash
docker compose ps
```

### Accéder au shell d'un conteneur
```bash
docker compose exec <nom-du-service> /bin/bash
# Exemples :
docker compose exec rodelika-web /bin/bash
docker compose exec purple-dragon-db mysql -uroot -p
```

### Voir les statistiques d'utilisation des ressources
```bash
docker compose stats
```

## Architecture des services

### Services Web
- **rodelika-web** : Application Flask Rodelika (port 8081)
- **berlicum-web** : Application Flask Berlicum (port 8082)
- **lunar-white** : Application Flask Lunar White (port 8083)

### Services Infrastructure
- **traefik** : Reverse proxy pour le routing par nom de domaine (port 80 et 8080)
- **purple-dragon-db** : Base de données MySQL 8.3
- **pcscd** : Daemon PC/SC pour l'accès aux lecteurs de cartes à puce
- **rubrovitamin** : Programmation des cartes avec Arduino ISP

### Services CLI
- **rodelika-cli** : Interface en ligne de commande Rodelika
- **berlicum-cli** : Interface en ligne de commande Berlicum
- **lubiana-cli** : Interface en ligne de commande Lubiana

## Volumes persistants
- **purple_dragon_data** : Données de la base de données MySQL
- **pcscd_socket** : Socket Unix pour la communication avec le daemon PC/SC

## Réseaux
- **traefik_proxy** : Réseau pour les services web exposés via Traefik
- **db_net** : Réseau interne pour la communication avec la base de données

## Dépannage

### La base de données ne démarre pas
Vérifiez les logs :
```bash
docker compose logs purple-dragon-db
```

### Un service web ne répond pas
1. Vérifiez que la base de données est démarrée :
```bash
docker compose ps purple-dragon-db
```

2. Vérifiez les logs du service :
```bash
docker compose logs -f <nom-du-service>
```

3. Redémarrez le service :
```bash
docker compose restart <nom-du-service>
```

### Reconstruire tout l'environnement depuis zéro
```bash
docker compose down -v
docker compose up -d --build
```

## Notes importantes
- L'option `--rm` supprime automatiquement le conteneur après son exécution
- L'option `-d` lance les services en arrière-plan (mode detach)
- L'option `--build` reconstruit les images avant de lancer les services
- Les ports 8081-8083 permettent un accès direct aux services sans configuration DNS
- Le service `pcscd` nécessite des privilèges élevés pour accéder aux périphériques USB
- Les services CLI nécessitent `stdin_open` et `tty` pour l'interaction en ligne de commande