# Envoi de message depuis `message.txt` vers `numero.txt`

Script Python (librairie standard uniquement) pour envoyer un message vers une liste de numéros, en parallèle, via Internet.

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
  --smtp-sender noreply@example.com
```

Options utiles:

- `--workers 100` pour maximiser l'envoi parallèle
- `--smtp-user` / `--smtp-pass` si votre SMTP demande un login
- `--smtp-ssl` si vous utilisez SMTP SSL direct (port 465)

## Exemple de `numero.txt`

```text
33601020304
33711111111
```
