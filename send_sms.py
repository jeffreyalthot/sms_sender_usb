#!/usr/bin/env python3
"""Envoi en masse d'un message texte vers une passerelle SMTP->SMS.

Le script peut utiliser un domaine passerelle explicitement fourni
ou un préréglage "libre d'accès" (sans API HTTP), basé sur les
passerelles email-to-SMS d'opérateurs qui ne demandent pas de clé API.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


FREE_ACCESS_GATEWAY_DOMAIN = os.getenv("FREE_SMS_GATEWAY_DOMAIN", "tmomail.net")


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int
    sender: str
    username: str | None
    password: str | None
    encryption: str


def normalize_smtp_config(smtp_conf: SMTPConfig) -> SMTPConfig:
    """Applique des valeurs implicites utiles pour les SMTP publics.

    Cas courant: avec Outlook/Office365, l'utilisateur oublie --smtp-user
    mais fournit un sender + mot de passe. On réutilise alors l'expéditeur
    comme identifiant SMTP.
    """
    if smtp_conf.username or not smtp_conf.password:
        return smtp_conf

    if "@" not in smtp_conf.sender:
        return smtp_conf

    return SMTPConfig(
        host=smtp_conf.host,
        port=smtp_conf.port,
        sender=smtp_conf.sender,
        username=smtp_conf.sender,
        password=smtp_conf.password,
        encryption=smtp_conf.encryption,
    )


def normalize_encryption(encryption: str, smtp_ssl_flag: bool) -> str:
    """Normalise le type de chiffrement SMTP.

    Accepte none/starttls/ssl. Le drapeau historique --smtp-ssl force ssl.
    """
    if smtp_ssl_flag:
        return "ssl"

    normalized = encryption.strip().lower()
    if normalized not in {"none", "starttls", "ssl"}:
        raise ValueError("--smtp-encryption doit être: none, starttls ou ssl")
    return normalized


def read_message(path: Path) -> str:
    message = path.read_text(encoding="utf-8").strip()
    if not message:
        raise ValueError(f"Le fichier message est vide: {path}")
    return message


def read_numbers(path: Path) -> list[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    numbers: list[str] = []
    for line in lines:
        if not line:
            continue
        if line.startswith("+"):
            line = line[1:]
        normalized = "".join(ch for ch in line if ch.isdigit())
        if not normalized:
            continue
        numbers.append(normalized)

    if not numbers:
        raise ValueError(f"Aucun numéro valide trouvé dans {path}")
    return numbers


def build_email(sender: str, to_address: str, body: str, subject: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def resolve_gateway_domain(raw_gateway_domain: str) -> str:
    gateway_domain = raw_gateway_domain.strip().lower()
    if gateway_domain in {"libre", "free", "free-access"}:
        return FREE_ACCESS_GATEWAY_DOMAIN
    return gateway_domain


def send_one(
    smtp_conf: SMTPConfig,
    gateway_domain: str,
    number: str,
    body: str,
    subject: str,
    timeout_s: float,
) -> tuple[str, bool, str]:
    to_addr = f"{number}@{gateway_domain}"
    msg = build_email(smtp_conf.sender, to_addr, body, subject)

    try:
        if smtp_conf.encryption == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_conf.host, smtp_conf.port, timeout=timeout_s, context=context) as smtp:
                if smtp_conf.username:
                    smtp.login(smtp_conf.username, smtp_conf.password or "")
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_conf.host, smtp_conf.port, timeout=timeout_s) as smtp:
                smtp.ehlo()
                if smtp_conf.encryption == "starttls":
                    if not smtp.has_extn("starttls"):
                        raise smtplib.SMTPException(
                            "Le serveur SMTP ne supporte pas STARTTLS alors qu'il est requis"
                        )
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if smtp_conf.username:
                    smtp.login(smtp_conf.username, smtp_conf.password or "")
                smtp.send_message(msg)
        return number, True, "OK"
    except (smtplib.SMTPException, OSError, socket.error) as exc:
        hint = ""
        if isinstance(exc, smtplib.SMTPSenderRefused) and exc.smtp_code == 530:
            hint = (
                " | Astuce: activez l'auth SMTP (--smtp-user/--smtp-pass) "
                "et utilisez un expéditeur identique au compte SMTP."
            )
        return number, False, f"{exc}{hint}"


def send_bulk(
    smtp_conf: SMTPConfig,
    gateway_domain: str,
    numbers: Iterable[str],
    body: str,
    subject: str,
    workers: int,
    timeout_s: float,
) -> tuple[int, int]:
    ok = 0
    ko = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(send_one, smtp_conf, gateway_domain, number, body, subject, timeout_s)
            for number in numbers
        ]

        for future in concurrent.futures.as_completed(futures):
            number, success, info = future.result()
            if success:
                ok += 1
                print(f"[OK] {number}")
            else:
                ko += 1
                print(f"[ERREUR] {number}: {info}")

    return ok, ko


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Envoie le contenu de message.txt à chaque numéro de numero.txt via un domaine passerelle SMS."
        )
    )
    parser.add_argument("--message-file", default="message.txt", type=Path)
    parser.add_argument("--numbers-file", default="numero.txt", type=Path)
    parser.add_argument(
        "--gateway-domain",
        default="free-access",
        help=(
            "Domaine passerelle (ex: tmomail.net) ou alias 'libre'/'free-access' "
            f"(résout vers {FREE_ACCESS_GATEWAY_DOMAIN})."
        ),
    )
    parser.add_argument("--smtp-host", default=os.getenv("SMTP_HOST", "localhost"))
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv("SMTP_PORT", "25")))
    parser.add_argument("--smtp-sender", default=os.getenv("SMTP_SENDER", "noreply@localhost"))
    parser.add_argument("--smtp-user", default=os.getenv("SMTP_USER"))
    parser.add_argument("--smtp-pass", default=os.getenv("SMTP_PASS"))
    parser.add_argument(
        "--smtp-encryption",
        default=os.getenv("SMTP_ENCRYPTION", "starttls"),
        help="Type de chiffrement SMTP: none, starttls (défaut), ssl",
    )
    parser.add_argument(
        "--smtp-ssl",
        action="store_true",
        help="Compatibilité: équivaut à --smtp-encryption ssl",
    )
    parser.add_argument("--subject", default="SMS")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(100, (os.cpu_count() or 2) * 8),
        help="Nombre de threads en parallèle (défaut élevé pour minimiser la latence globale)",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout SMTP par envoi, en secondes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        encryption = normalize_encryption(args.smtp_encryption, args.smtp_ssl)
    except ValueError as exc:
        print(f"Erreur configuration SMTP: {exc}")
        return 2

    smtp_conf = normalize_smtp_config(
        SMTPConfig(
        host=args.smtp_host,
        port=args.smtp_port,
        sender=args.smtp_sender,
        username=args.smtp_user,
        password=args.smtp_pass,
        encryption=encryption,
        )
    )

    gateway_domain = resolve_gateway_domain(args.gateway_domain)
    message = read_message(args.message_file)
    numbers = read_numbers(args.numbers_file)

    print(
        f"Envoi vers {len(numbers)} numéros avec {args.workers} workers "
        f"(gateway: {gateway_domain})..."
    )
    ok, ko = send_bulk(
        smtp_conf=smtp_conf,
        gateway_domain=gateway_domain,
        numbers=numbers,
        body=message,
        subject=args.subject,
        workers=max(1, args.workers),
        timeout_s=max(1.0, args.timeout),
    )

    print(f"Terminé. Succès: {ok}, Erreurs: {ko}")
    return 0 if ko == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
