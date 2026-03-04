#!/usr/bin/env python3
"""Envoi en masse d'un message texte vers une liste de numéros via une passerelle SMTP->SMS.

Contraintes:
- Sans API HTTP externe (utilise uniquement la librairie standard Python)
- Sans modem USB / dongle
- Envoi via Internet

Important: l'envoi réel nécessite une passerelle opérateur (ex: numero@domaine-passerelle)
ou un serveur SMTP autorisé à relayer les messages.
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


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int
    sender: str
    username: str | None
    password: str | None
    use_tls: bool


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
        if smtp_conf.use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_conf.host, smtp_conf.port, timeout=timeout_s, context=context) as smtp:
                if smtp_conf.username:
                    smtp.login(smtp_conf.username, smtp_conf.password or "")
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_conf.host, smtp_conf.port, timeout=timeout_s) as smtp:
                smtp.ehlo()
                if smtp.has_extn("starttls"):
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if smtp_conf.username:
                    smtp.login(smtp_conf.username, smtp_conf.password or "")
                smtp.send_message(msg)
        return number, True, "OK"
    except (smtplib.SMTPException, OSError, socket.error) as exc:
        return number, False, str(exc)


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
    parser.add_argument("--gateway-domain", required=True, help="Ex: sms.operateur.example")
    parser.add_argument("--smtp-host", default=os.getenv("SMTP_HOST", "localhost"))
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv("SMTP_PORT", "25")))
    parser.add_argument("--smtp-sender", default=os.getenv("SMTP_SENDER", "noreply@localhost"))
    parser.add_argument("--smtp-user", default=os.getenv("SMTP_USER"))
    parser.add_argument("--smtp-pass", default=os.getenv("SMTP_PASS"))
    parser.add_argument("--smtp-ssl", action="store_true", help="Utiliser SMTP_SSL directement")
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

    smtp_conf = SMTPConfig(
        host=args.smtp_host,
        port=args.smtp_port,
        sender=args.smtp_sender,
        username=args.smtp_user,
        password=args.smtp_pass,
        use_tls=args.smtp_ssl,
    )

    message = read_message(args.message_file)
    numbers = read_numbers(args.numbers_file)

    print(f"Envoi vers {len(numbers)} numéros avec {args.workers} workers...")
    ok, ko = send_bulk(
        smtp_conf=smtp_conf,
        gateway_domain=args.gateway_domain,
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
