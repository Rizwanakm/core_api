from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    url = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    # -------------------------------
# WALLET
# -------------------------------
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Integer, default=0)

# -------------------------------
# TRANSACTIONS (history)
# -------------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Integer)
    type = Column(String)  # "credit" or "debit"
    description = Column(String)

# -------------------------------
# FOLLOW SYSTEM
# -------------------------------
class Follow(Base):
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer)
    following_id = Column(Integer)