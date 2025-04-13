# 1.1.1 parser.py

import os
import hashlib
from pathlib import Path
from lxml import etree
from sqlalchemy.orm import Session
from .models import Contact, Conversation, Message, Attachment
from .db import SessionLocal
import requests

MEDIA_DIR = Path("/app/media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_contact(db: Session, phone_number: str, name: str = None) -> Contact:
    contact = db.query(Contact).filter(Contact.phone_number == phone_number).first()
    if not contact:
        contact = Contact(phone_number=phone_number, name=name)
        db.add(contact)
        db.commit()
        db.refresh(contact)
    return contact


def get_or_create_conversation(db: Session, thread_id: int) -> Conversation:
    convo = db.query(Conversation).filter(Conversation.thread_id == thread_id).first()
    if not convo:
        convo = Conversation(thread_id=thread_id, title=f"Thread {thread_id}")
        db.add(convo)
        db.commit()
        db.refresh(convo)
    return convo


def generate_message_id(timestamp: str, address: str, body: str) -> str:
    composite = f"{timestamp}:{address}:{body}".encode("utf-8")
    return hashlib.sha256(composite).hexdigest()


def download_media(url: str, message_id: str) -> str:
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            ext = url.split('.')[-1].split('?')[0]  # crude extension grab
            fname = f"{message_id[:12]}_{hash(url)}.{ext}"
            file_path = MEDIA_DIR / fname
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return str(file_path)
    except Exception as e:
        print(f"Failed to download media: {url} -> {e}")
    return ""


def parse_sms(elem, db: Session):
    address = elem.attrib.get("address")
    thread_id = int(elem.attrib.get("thread_id", 0))
    body = elem.attrib.get("body", "")
    timestamp = elem.attrib.get("date", "0")
    contact_name = elem.attrib.get("contact_name", None)

    message_id = generate_message_id(timestamp, address, body)

    if db.query(Message).filter(Message.message_id == message_id).first():
        return  # Skip duplicates

    contact = get_or_create_contact(db, phone_number=address, name=contact_name)
    convo = get_or_create_conversation(db, thread_id=thread_id)

    message = Message(
        message_id=message_id,
        conversation_id=convo.id,
        sender_id=contact.id,
        timestamp=int(timestamp),
        type="sms",
        body=body,
        is_from_me=(elem.attrib.get("type") == "2"),
        status=elem.attrib.get("status"),
        read=(elem.attrib.get("read", "1") == "1"),
        date_sent=int(elem.attrib.get("date_sent", "0")),
        date_received=int(elem.attrib.get("date", "0")),
        subject=elem.attrib.get("subject", None)
    )

    db.add(message)
    db.commit()


def parse_mms(elem, db: Session):
    thread_id = int(elem.attrib.get("thread_id", 0))
    timestamp = elem.attrib.get("date", "0")
    message_id = generate_message_id(timestamp, "mms", elem.attrib.get("text", ""))

    if db.query(Message).filter(Message.message_id == message_id).first():
        return

    convo = get_or_create_conversation(db, thread_id=thread_id)

    message = Message(
        message_id=message_id,
        conversation_id=convo.id,
        sender_id=None,
        timestamp=int(timestamp),
        type="mms",
        body=elem.attrib.get("text", ""),
        is_from_me=(elem.attrib.get("msg_box") == "2"),
        read=True,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    for part in elem.findall("part"):
        url = part.attrib.get("data", "")
        content_type = part.attrib.get("ct", "")
        if url.startswith("http://") or url.startswith("https://"):
            file_path = download_media(url, message_id)
            attachment = Attachment(
                message_id=message.id,
                content_type=content_type,
                file_path=file_path,
                file_name=os.path.basename(file_path)
            )
            db.add(attachment)

    db.commit()


def parse_file(file_path: str, db: Session):
    context = etree.iterparse(file_path, events=("end",), tag=("sms", "mms"))
    for _, elem in context:
        try:
            if elem.tag == "sms":
                parse_sms(elem, db)
            elif elem.tag == "mms":
                parse_mms(elem, db)
        except Exception as e:
            print(f"Failed to parse {elem.tag}: {e}")
        finally:
            elem.clear()


def parse_directory_recursively(root_dir: str):
    db = SessionLocal()
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".xml"):
                full_path = os.path.join(dirpath, filename)
                print(f"Parsing {full_path}")
                parse_file(full_path, db)
    db.close()
