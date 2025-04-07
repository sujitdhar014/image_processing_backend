from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import shutil, csv, os
from uuid import uuid4
from celery import Celery
from PIL import Image
import requests
from io import BytesIO

# #>>>>>......... Configuration  >>>>>.........

DATABASE_URL = "sqlite:///./test.db"
UPLOAD_DIR = "input_csv"
OUTPUT_DIR = "output_csv"
IMAGE_DIR = "output_images"
REDIS_BROKER = "redis://localhost:6379/0"

# #>>>>>......... Setup #>>>>>.........
app = FastAPI()
engine = create_engine(DATABASE_URL)
Session_Local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
celery = Celery(__name__, broker=REDIS_BROKER)

# #>>>>>......... Database Models #>>>>>.........
class Request(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum('pending', 'processing', 'completed', 'failed', name='status_enum'))
    output_csv_url = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    products = relationship("Product", back_populates="request")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id"))
    product_name = Column(String)
    input_urls = Column(Text)
    output_urls = Column(Text)
    request = relationship("Request", back_populates="products")

Base.metadata.create_all(bind=engine)

# #>>>>>......... Utility Functions #>>>>>.........
def compress_image_from_url(url, save_path):
    try:
        print(f"Downloading image: {url}")
        response = requests.get(url, timeout=10)
        img = Image.open(BytesIO(response.content))
        img = img.convert("RGB")
        img.save(save_path, format='JPEG', quality=50)
        print(f"Saved image to: {save_path}")
        return True
    except Exception as e:
        print(f"Image error: {e}")
        return False

def write_output_csv(request_id, rows):
    path = f"{OUTPUT_DIR}/{request_id}.csv"
    with open(path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Serial Number", "Product Name:", "Input Image Urls:", "Output Image Urls"])
        for row in rows:
            writer.writerow(row)
    return path

def send_webhook(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Webhook sent: {response.status_code}")
    except Exception as e:
        print(f"Webhook failed: {e}")

# #>>>>>......... Celery Worker Task #>>>>>.........
@celery.task
def process_csv_task(request_id, file_path):
    db = Session_Local()
    req = None
    try:
        req = db.query(Request).get(request_id)
        req.status = 'processing'
        db.commit()

        with open(file_path, newline='') as f:
            reader = csv.reader(f)
            next(reader)
            output_rows = []

            for idx, row in enumerate(reader, start=1):
                if len(row) < 3:
                    continue
                _, name, input_urls = row
                input_list = [url.strip() for url in input_urls.split(',')]
                output_list = []

                for i, url in enumerate(input_list):
                    img_path = f"{IMAGE_DIR}/{request_id}_{idx}_{i}.jpg"
                    success = compress_image_from_url(url, img_path)
                    output_list.append(img_path if success else "FAILED")

                product = Product(
                    request_id=request_id,
                    product_name=name,
                    input_urls=','.join(input_list),
                    output_urls=','.join(output_list)
                )
                db.add(product)
                output_rows.append([idx, name, ','.join(input_list), ','.join(output_list)])

            csv_path = write_output_csv(request_id, output_rows)
            req.status = 'completed'
            req.output_csv_url = csv_path
            db.commit()

            if req.webhook_url:
                send_webhook(req.webhook_url, {
                    "status": "completed",
                    "request_id": req.id,
                    "output_csv_url": req.output_csv_url
                })

    except Exception as e:
        print(f"Task Error: {e}")
        if req:
            req.status = 'failed'
            db.commit()
            if req.webhook_url:
                send_webhook(req.webhook_url, {
                    "status": "failed",
                    "request_id": req.id,
                    "error": str(e)
                })
    finally:
        db.close()

# #>>>>>......... API Endpoints #>>>>>.........
@app.post("/upload/")
def upload_csv(
    file: UploadFile = File(...),
    webhook_url: str = Form(None)
):
    db = Session_Local()

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

    request_id = str(uuid4())
    file_path = f"{UPLOAD_DIR}/{request_id}.csv"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_req = Request(status='pending', webhook_url=webhook_url)
    db.add(new_req)
    db.commit()
    db.refresh(new_req)

    process_csv_task.delay(new_req.id, file_path)

    db.close()
    return {"request_id": new_req.id}

@app.get("/status/{request_id}")
def get_status(request_id: int):
    db = Session_Local()
    req = db.query(Request).get(request_id)
    if not req:
        return JSONResponse(status_code=404, content={"error": "Request not found..."})
    return {"status": req.status, "output_csv_url....": req.output_csv_url}
