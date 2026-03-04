# Envoi de message depuis `message.txt` vers `numero.txt`

Script Python (librairie standard uniquement) pour envoyer un message vers une liste de numéros, en parallèle, via Internet.

## ⚠️ Limitation importante

Sans API opérateur, sans compte d'authentification et sans modem, l'envoi SMS direct **n'est pas universellement possible**.
Ce script utilise la méthode **SMTP -> passerelle SMS** (adresse `numero@domaine-passerelle`).

## Préparer les fichiers

- `message.txt`: le texte à envoyer
- `numero.txt`: un numéro par ligne (avec ou sans `+`, les caractères non numériques sont ignorés)

## Exécution

```bash
python3 send_sms.py \
  --gateway-domain sms.operateur.example \
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
