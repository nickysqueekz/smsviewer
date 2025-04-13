# 1.1.0 models.py

from sqlalchemy import Column, Integer, String, Text, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone_number = Column(String, unique=True)
    email = Column(String, nullable=True)

    messages = relationship("Message", back_populates="sender")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, unique=True)
    title = Column(String)

    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    message_id = Column(String, unique=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender_id = Column(Integer, ForeignKey("contacts.id"))
    timestamp = Column(BigInteger, nullable=False)
    type = Column(String)
    body = Column(Text)
    is_from_me = Column(Boolean)
    status = Column(String)
    read = Column(Boolean, default=True)
    date_sent = Column(BigInteger, nullable=True)
    date_received = Column(BigInteger, nullable=True)
    subject = Column(Text, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("Contact", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message")


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    content_type = Column(String)
    file_name = Column(String)
    file_path = Column(String)
    data_base64 = Column(Text)

    message = relationship("Message", back_populates="attachments")
