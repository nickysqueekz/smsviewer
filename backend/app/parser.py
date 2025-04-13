# 1.1.0 parser.py

import os
import hashlib
from lxml import etree
from sqlalchemy.orm import Session
from .models import Contact, Conversation, Message
from .db import SessionLocal

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

def parse_sms_backup(file_path: str):
    db = SessionLocal()
    context = etree.iterparse(file_path, events=("end",), tag=("sms",))

    for _, elem in context:
        try:
            address = elem.attrib.get("address")
            thread_id = int(elem.attrib.get("thread_id", 0))
            body = elem.attrib.get("body", "")
            timestamp = elem.attrib.get("date", "0")
            contact_name = elem.attrib.get("contact_name", None)

            message_id = generate_message_id(timestamp, address, body)

            if db.query(Message).filter(Message.message_id == message_id).first():
                continue  # Skip duplicates

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

        except Exception as e:
            print(f"Failed to process element: {e}")
        finally:
            elem.clear()

    db.close()
