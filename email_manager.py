import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gmail_service import get_gmail_service


def lire_emails(max_resultats=10, filtre='is:unread'):
    """Lire les emails de la boite archiatechx@gmail.com"""
    service = get_gmail_service()
    resultats = service.users().messages().list(
        userId='me',
        q=filtre,
        maxResults=max_resultats
    ).execute()

    messages = resultats.get('messages', [])
    emails = []

    for msg in messages:
        message = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()

        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        corps = _extraire_corps(message['payload'])

        emails.append({
            'id': msg['id'],
            'de': headers.get('From', ''),
            'sujet': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'corps': corps,
        })

    return emails


def envoyer_email(destinataire, sujet, corps, html=False):
    """Envoyer un email depuis archiatechx@gmail.com"""
    service = get_gmail_service()

    if html:
        message = MIMEMultipart('alternative')
        message['To'] = destinataire
        message['Subject'] = sujet
        message.attach(MIMEText(corps, 'html'))
    else:
        message = MIMEText(corps)
        message['To'] = destinataire
        message['Subject'] = sujet

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(f"Email envoyé à {destinataire} — Sujet : {sujet}")


def chercher_emails(requete, max_resultats=10):
    """Chercher des emails avec une requête Gmail (ex: 'from:client@email.com')"""
    return lire_emails(max_resultats=max_resultats, filtre=requete)


def marquer_lu(message_id):
    """Marquer un email comme lu"""
    service = get_gmail_service()
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()


def _decode_base64(data):
    # Gmail omits base64url padding — normalize before decoding
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def _extraire_corps(payload):
    if payload.get('body', {}).get('data'):
        return _decode_base64(payload['body']['data']).decode('utf-8', errors='ignore')

    # Recurse into MIME tree (handles multipart/mixed → multipart/alternative → text/plain)
    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
            return _decode_base64(part['body']['data']).decode('utf-8', errors='ignore')
        result = _extraire_corps(part)
        if result:
            return result

    return ''


if __name__ == '__main__':
    print("=== Emails non lus ===")
    emails = lire_emails(max_resultats=5)
    for e in emails:
        print(f"\nDe : {e['de']}")
        print(f"Sujet : {e['sujet']}")
        print(f"Date : {e['date']}")
        print(f"Corps : {e['corps'][:200]}...")
