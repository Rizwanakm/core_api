from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, schemas
from auth import hash_password, verify_password, create_token, get_current_user
import os

app = FastAPI()

# Create uploads folder
os.makedirs("uploads", exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

# -------------------------------
# DB Dependency
# -------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------
# REGISTER
# -------------------------------
@app.post("/v1/auth/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = models.User(
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()

    return {"message": "User registered successfully"}

# -------------------------------
# LOGIN
# -------------------------------
@app.post("/v1/auth/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(models.User).filter(models.User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Wrong password")

    token = create_token({"user_id": db_user.id})

    return {"access_token": token}

# -------------------------------
# HOME
# -------------------------------
@app.get("/")
def home():
    return {"message": "API is running 🚀"}

# -------------------------------
# FEED (JWT)
# -------------------------------
@app.get("/v1/feed")
def get_feed(user_id: int = Depends(get_current_user)):
    return {
        "message": "This is your personalized feed",
        "user_id": user_id
    }

# -------------------------------
# UPLOAD CONTENT (JWT)
# -------------------------------
@app.post("/v1/content/upload/initiate")
def upload_content(
    title: str = Form(...),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_location = f"uploads/{file.filename}"

    with open(file_location, "wb") as f:
        f.write(file.file.read())

    new_content = models.Content(
        title=title,
        url=file_location,
        owner_id=user_id
    )

    db.add(new_content)
    db.commit()
    db.refresh(new_content)

    return {
        "message": "File uploaded",
        "content_id": new_content.id,
        "url": file_location
    }

# -------------------------------
# GET CONTENT (NO AUTH)
# -------------------------------
@app.get("/v1/content/{id}")
def get_content(id: int, db: Session = Depends(get_db)):
    content = db.query(models.Content).filter(models.Content.id == id).first()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    return {
        "id": content.id,
        "title": content.title,
        "url": content.url
    }

# -------------------------------
# DELETE CONTENT (JWT)
# -------------------------------
@app.delete("/v1/content/{id}")
def delete_content(
    id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = db.query(models.Content).filter(models.Content.id == id).first()

    if not content:
        raise HTTPException(status_code=404, detail="Not found")

    if content.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your content")

    db.delete(content)
    db.commit()

    return {"message": "Deleted successfully"}

# -------------------------------
# CHECK DB
# -------------------------------
@app.get("/check-db")
def check_db():
    return {"status": "connected"}
@app.get("/v1/wallet/balance")
def get_balance(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()

    if not wallet:
        wallet = models.Wallet(user_id=user_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    return {
        "user_id": user_id,
        "balance": wallet.balance
    }
@app.get("/v1/wallet/history")
def wallet_history(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):

    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    ).all()

    return transactions
@app.post("/v1/wallet/redeem")
def redeem(amount: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()

    if not wallet or wallet.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    wallet.balance -= amount

    txn = models.Transaction(
        user_id=user_id,
        amount=amount,
        type="debit",
        description="Redeem to bank/UPI"
    )

    db.add(txn)
    db.commit()

    return {"message": "Redeem successful"}
@app.post("/v1/content/{id}/view")
def view_content(id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):

    reward = 5

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()

    if not wallet:
        wallet = models.Wallet(user_id=user_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    wallet.balance += reward

    txn = models.Transaction(
        user_id=user_id,
        amount=reward,
        type="credit",
        description="Content view reward"
    )

    db.add(txn)
    db.commit()

    return {
        "message": "View recorded",
        "reward": reward
    }
@app.post("/v1/users/{id}/follow")
def follow_user(id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):

    if id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == user_id,
        models.Follow.following_id == id
    ).first()

    if existing:
        return {"message": "Already following"}

    follow = models.Follow(
        follower_id=user_id,
        following_id=id
    )

    db.add(follow)
    db.commit()

    return {"message": "Followed successfully"}
@app.get("/v1/search")
def search(q: str, db: Session = Depends(get_db)):

    users = db.query(models.User).filter(models.User.email.contains(q)).all()

    content = db.query(models.Content).filter(models.Content.title.contains(q)).all()

    return {
        "users": users,
        "content": content
    }