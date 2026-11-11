# Configurer le Brother DS-940DW sur Synology DSM 7

[Guide en anglais](../synology.md) · [README du projet](../../README.md)

Allumez le scanner et insérez une feuille. Le récepteur sur le NAS enregistre les deux faces dans un PDF. Vous pouvez utiliser un partage SMB, une installation Paperless-ngx existante ou une nouvelle instance avec le récepteur.

## 1. Préparer le scanner et le NAS

1. Installez **Container Manager** depuis le **Centre de paquets**. Le pilote utilisé exige un NAS x86-64. La commande `uname -m` doit afficher `x86_64`.
2. Connectez le scanner à votre réseau local en mode Wi-Fi et réservez son adresse IPv4 sur le routeur. Le NAS doit pouvoir joindre le scanner sur le LAN. L’installation de référence utilisait TCP 54921 et UDP 161.
3. Dans **File Station**, créez le dossier `/volume1/docker/ds-940-paperless-scanner`. Copiez-y le contenu du dépôt, dont `Dockerfile`, `compose.yaml`, `ds940/` et `.env.example`.
4. Pour la première installation, créez `work` et `consume`, puis copiez le modèle vers `.env`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

Renseignez `SCANNER_IP`. Indiquez dans `SCAN_UID` et `SCAN_GID` les identifiants d’un utilisateur et d’un groupe autorisés à écrire dans les deux dossiers. Les commandes SSH `id -u` et `id -g` donnent ces identifiants. Conservez `.env` sur le NAS.

## 2. Utiliser un partage SMB ou une instance Paperless existante

Pour SMB, indiquez le chemin du dossier partagé sur le NAS dans `SCAN_OUTPUT_DIR`. Pour Paperless, ouvrez les volumes du conteneur dans Container Manager. Repérez le chemin **sur l’hôte** monté sur `/usr/src/paperless/consume` et utilisez-le dans `SCAN_OUTPUT_DIR`. Les deux conteneurs doivent pouvoir accéder à ce dossier. Si Paperless ne détecte pas les nouveaux fichiers sur le partage, définissez `PAPERLESS_CONSUMER_POLLING_INTERVAL=15` dans son environnement.

Dans Container Manager, choisissez **Projet → Créer**, sélectionnez le dossier source et importez `compose.yaml`. Construisez et démarrez le projet. Si l’assistant ne charge pas `.env`, lancez le récepteur par SSH.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## 3. Démarrer une nouvelle instance Paperless-ngx

Créez `export`. Vérifiez les droits d’écriture du compte configuré sur `work`, `consume` et `export`. Définissez deux valeurs aléatoires distinctes pour `POSTGRES_PASSWORD` et `PAPERLESS_SECRET_KEY` dans le fichier local `.env`. Vous pouvez générer chacune avec `openssl rand -hex 32`. Pour accéder à Paperless depuis un autre appareil, renseignez l’adresse LAN du NAS dans `PAPERLESS_BIND_IP`. Le port par défaut est 8010.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

Ouvrez Paperless à l’adresse configurée et créez le premier administrateur. Vous pouvez aussi exécuter les commandes de votre variante une seule fois en tant que `root` depuis le **Planificateur de tâches** de DSM, avec un script utilisateur. Gardez la ligne `cd` et retirez `sudo`.

## 4. Vérifier la première numérisation

1. Allumez le scanner et attendez `Ready for paper` dans le journal du conteneur `scanner`. Le fichier `work/auto-status.json` affiche alors `waiting_for_paper`.
2. Marquez le recto et le verso d’une feuille de test. Insérez-la recto vers le haut. Attendez qu’elle soit sortie avant d’en introduire une autre.
3. Ouvrez le PDF dans le partage ou dans Paperless et vérifiez les deux faces. Laissez à Paperless le temps d’importer le fichier et de terminer l’OCR. Éteignez le scanner après la série.

Le profil par défaut est `SCAN_PAPER_SIZE=a4`. Le mode `auto` détecte le format et `legal` utilise une zone fixe d’environ 355,6 mm de long. La capture complète d’un ticket long en mode Legal reste à vérifier sur l’appareil. Fermez le guide de sortie supérieur pour le papier plus long que l’A4. Après un changement de profil, relancez `docker compose up -d scanner` avec le même nom de projet et les mêmes fichiers `-f`.

## Dépannage

- Avec `scanner_offline`, vérifiez le Wi-Fi, l’adresse réservée et l’accès depuis le NAS.
- Avec `scanner_busy` ou `-NG 401`, fermez les autres logiciels de numérisation. Attendez la nouvelle tentative ou éteignez puis rallumez le Brother.
- Avec `paper_blocked`, ouvrez le capot supérieur, retirez doucement la feuille et refermez le capot.
- Si le document manque dans Paperless, vérifiez le chemin, les permissions et les journaux. Dans `work/spool`, `ready` indique un envoi en attente et `forwarded` un PDF écrit dans le dossier de destination. Archivez les anciens dossiers après avoir vérifié l’import et conservé les copies utiles.
