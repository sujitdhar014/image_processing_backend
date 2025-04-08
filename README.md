# 🖼️ Image Processor Backend

This is a backend system for asynchronous image compression. It accepts a CSV file containing product names and image URLs, compresses the images in the background, and provides an output CSV with updated image paths. The service supports status tracking and webhook callbacks.

---

## 📐 Architecture Overview

```
Client ➤ FastAPI ➤ SQLite DB
             ⬇
         Celery Worker ➤ Redis (broker)
             ⬇
        File System (input, output, reports)
             ⬇
        Webhook Callback (optional)
```
## 📝  Architecture Diagram
![architecture](https://github.com/user-attachments/assets/1b0c4c6f-a87b-4398-a2db-ce5752f7826f)


---

## 🚀 Features

- Upload CSV with product names & image URLs.
- Asynchronous image compression using Celery.
- Real-time status tracking via API.
- Webhook support for post-processing callbacks.
- Error handling and retry mechanism.

---

## 🛠️ Technologies Used

- Python 3
- FastAPI
- Celery
- SQLite
- Redis
- Pillow (image processing)

---

## 🏗️ Project Structure

```
.
├── main.py                 # FastAPI server
├── celery_worker.py        # Celery worker process
├── database.py             # DB setup and models
├── utils.py                # Image compression logic
├── requirements.txt
└── /storage
    ├── /input_csv
    ├── /output_images
    └── /output_csv

```

---

## 📦 Setup & Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-username/image-processor-backend.git
   cd image-processor-backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Redis**
   Ensure Redis is installed and running:
   ```bash
   redis-server
   ```

4. **Start FastAPI app**
   ```bash
   uvicorn main: app --reload
   ```

5. **Start Celery worker**
   ```bash
   celery -A celery_worker.app worker --loglevel=info
   ```

---

## 📤 API Endpoints

### `POST /upload/`

**Description:** Upload a CSV file and start async image processing.

**Form Fields**
- `file`: CSV file (with columns: `product_name`, `image_urls`)
- `webhook_url` (optional): URL to notify when processing is done.

**Response:**
```json
{
  "request_id": 1
}
```

---

### `GET /status/{request_id}`

**Description: ** Could you check the current processing status?

**Response:**
```json
{
  "status": "completed",
  "output_csv_url": "output_csv/1.csv"
}
```

---

## ⚙️ Worker Functionality

The Celery worker executes the `process_csv_task()` function which performs the following:

1. It loads the request from the database using `request_id`.
2. Parses the input CSV.
3. For each product:
   - Downloads image(s) from URL.
   - Compresses image using Pillow.
   - Saves it to `/output_images/`.
4. Writes a new CSV report to `/output_csv/`.
5. Updates request status in DB.
6. Triggers webhook if provided.

---

## 🔔 Webhook Example

If a `webhook_url` is provided during upload, the following JSON is POSTed to that endpoint after processing:

```json
{
  "request_id": 2,
  "status": "completed",
  "output_csv_url": "output_csv/2.csv"
}
```

---

## 🧪 Testing & Error Handling

- ✅ Skips malformed rows in the uploaded CSV.
- ❌ Invalid image URLs or unreachable resources are gracefully handled.
- 💥 On an unrecoverable error, a request is marked as `failed. '
- 🔁 No retries for now (can be added with Celery retry policies).

---

## 📈 Future Improvements

- Add support for cloud storage (e.g., S3).
- Include a comparison of image size in the report.
- User authentication and API rate limits.
- Dockerization for deployment.

---

## 🧩 Sample CSV Format

```csv
S. No, Product Name, Input URLs
4,imageone,https://picsum.photos/800/600.jpg  
3,imagetwo,https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png 
```

---



### 📬 Postman Collection
A Postman collection is available to test all endpoints.
Open in Postman → 

[![View in Postman](https://img.shields.io/badge/View%20in-Postman-orange?logo=postman)](https://www.postman.com/sujit014/workspace/testing-the-apis/request/33142565-e23a9506-a0e0-4055-95b4-a4479a8fb61d?action=share&creator=33142565&ctx=documentation)

##  Contact

Feel free to raise an issue or reach out if you have any questions or suggestions.

---

⭐ Don’t forget to star the repo if you found this helpful!



