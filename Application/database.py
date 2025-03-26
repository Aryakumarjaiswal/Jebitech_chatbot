from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt
from sqlalchemy import (
    Column, String, Integer, Enum, ForeignKey, Text, TIMESTAMP, func, CHAR
)
import uuid
from sqlalchemy.dialects.mysql import CHAR
from dotenv import load_dotenv
import os


load_dotenv()




DB_PASSWORD= os.getenv("our_password")  #quote_plus("#1Krishna")
USERNAME=os.getenv("our_user")
HOST=os.getenv("our_host")
PORT=int(os.getenv("our_port"))
DB=os.getenv("our_database")

DATABASE_URL = f"mysql+pymysql://{USERNAME}:{DB_PASSWORD}@{HOST}:{PORT}/{DB}"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Session_Table(Base):
    __tablename__ = "Session_table"

    session_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(50))
    user_type = Column(String(50), nullable=False, default="user")
    status = Column(Enum("active", "closed", "transferred"), nullable=False, default="active")
    started_at = Column(TIMESTAMP, server_default=func.now(), nullable=True)
    ended_at = Column(TIMESTAMP, nullable=True)
    Duration = Column(Integer, nullable=True)  # Changed from String to Integer
    chats = relationship("Chat", back_populates="session")
    chat_transfers = relationship("ChatTransfer", back_populates="session")

class Chat(Base):
    __tablename__ = "Chat_table"

    chat_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(CHAR(36), ForeignKey("Session_table.session_id"))
    sender = Column(Enum("user", "bot", "agent"), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(TIMESTAMP, server_default=func.now(), nullable=True)
    status = Column(Enum("unread", "read"), default="read")
    session = relationship("Session_Table", back_populates="chats")

class ChatTransfer(Base):
    __tablename__ = "chat_transfer_table"

    transfer_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    session_id = Column(CHAR(36), ForeignKey("Session_table.session_id"))
    transferred_by = Column(String(50))
    transfer_reason = Column(Text, nullable=True)
    transferred_at = Column(TIMESTAMP, server_default=func.now(), nullable=True)
    agent_id = Column(CHAR(36), default=lambda: str(uuid.uuid4()), index=True)  # Fixed primary_key issue
    session = relationship("Session_Table", back_populates="chat_transfers")

# Create Tables
print("Tables to be created:")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
