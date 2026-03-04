# Envoi de message depuis `message.txt` vers `numero.txt`

Script Python (librairie standard uniquement, avec `smtplib`) pour envoyer un message vers une liste de numéros, en parallèle, via Internet.

## ⚠️ Limitation importante

Sans API opérateur, sans compte d'authentification et sans modem, l'envoi SMS direct **n'est pas universellement possible**.
Ce script utilise la méthode **SMTP -> passerelle SMS** (adresse `numero@domaine-passerelle`).

## Gateway-domain "libre d'accès"

Par défaut, le script utilise `--gateway-domain free-access`, alias qui pointe vers `tmomail.net`.

Vous pouvez changer ce domaine libre d'accès via la variable d'environnement:

```bash
export FREE_SMS_GATEWAY_DOMAIN=tmomail.net
```

Ou forcer un domaine explicite:

```bash
--gateway-domain mon.domaine.sms
```

## Préparer les fichiers

- `message.txt`: le texte à envoyer
- `numero.txt`: un numéro par ligne (avec ou sans `+`, les caractères non numériques sont ignorés)

## Exécution

```bash
python3 send_sms.py \
  --gateway-domain free-access \
  --smtp-host localhost \
  --smtp-port 25 \
  --smtp-encryption none \
  --smtp-sender noreply@example.com
```

Options utiles:

- `--workers 100` pour maximiser l'envoi parallèle
- `--smtp-user` / `--smtp-pass` si votre SMTP demande un login
- `--smtp-encryption starttls` pour STARTTLS (recommandé, notamment pour Microsoft 365 / Office365)
- `--smtp-encryption ssl` pour SMTP SSL direct (port 465)
- `--smtp-encryption none` pour SMTP sans chiffrement (souvent local uniquement)
- `--smtp-ssl` reste disponible (compatibilité) et équivaut à `--smtp-encryption ssl`

## Configuration recommandée (Microsoft 365)

- Serveur SMTP: `smtp.office365.com`
- Port: `587`
- Chiffrement: `STARTTLS`
- Authentification: `Oui`
- Utilisateur: votre adresse email Microsoft 365
- Mot de passe: mot de passe du compte ou mot de passe d'application

Exemple générique:

```text
SMTP Host: smtp.office365.com
SMTP Port: 587
Encryption: STARTTLS
Authentication: true
Username: votre_email@domaine.com
Password: votre_mot_de_passe
```

Points importants:

- Le port 587 est recommandé par Microsoft pour l'envoi via SMTP authentifié.
- Le port 25 est souvent bloqué par les fournisseurs internet / environnements cloud.
- Pour la plupart des applications (Python, PHP, Node, imprimante, NAS), STARTTLS sur 587 est la bonne option.

### Cas Outlook / Office365 (erreur 530 5.7.57)

Si vous voyez `Client not authenticated to send mail`, activez
l'authentification SMTP et utilisez un expéditeur qui correspond au compte.

Exemple:

```bash
python3 send_sms.py \
  --gateway-domain msg.telus.com \
  --smtp-host smtp.office365.com \
  --smtp-port 587 \
  --smtp-encryption starttls \
  --smtp-sender moncompte@outlook.com \
  --smtp-user moncompte@outlook.com \
  --smtp-pass 'mot_de_passe_ou_app_password'
```

Note: si `--smtp-user` est omis mais que `--smtp-pass` est fourni, le script
réutilise automatiquement `--smtp-sender` comme utilisateur SMTP.

## Exemple de `numero.txt`

```text
33601020304
33711111111
```
