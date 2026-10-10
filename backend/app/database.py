from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./data/smartpill.sqlite3"

# Đảm bảo thư mục data tồn tại
os.makedirs("./data", exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Tạo các bảng
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    from .models import User, CareReceiver
    
    # Khởi tạo dữ liệu mẫu nếu chưa có
    if db.query(User).first() is None:
        u1 = User(username="caregiver1", password_hash="123456", role="caregiver")
        u2 = User(username="caregiver2", password_hash="123456", role="caregiver")
        db.add_all([u1, u2])
        db.commit()
        
        c1 = CareReceiver(name="Ông Nguyễn Văn A", age=70, caregiver_id=u1.id)
        c2 = CareReceiver(name="Bà Trần Thị B", age=65, caregiver_id=u2.id)
        db.add_all([c1, c2])
        db.commit()
    db.close()
