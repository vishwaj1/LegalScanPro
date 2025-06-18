from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://legal-scan-pro-pyk5.vercel.app/", "http://localhost:3000"], # or restrict to ["http://localhost:3000"] if using Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

R2_ENDPOINT = "https://2528d8927d152e92961cc8c4ee90f43f.r2.cloudflarestorage.com/legal-scan-pro"
BUCKET = os.getenv("R2_BUCKET_NAME")

s3 = boto3.client(
"s3",
endpoint_url=R2_ENDPOINT,
aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
)

# s3 = boto3.client(
# "s3",
# endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT')}",
# aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
# aws_secret_access_key=os.getenv("MINIO_SECRET_KEY"),
# )

# BUCKET = os.getenv("MINIO_BUCKET", "legal-docs")

@app.on_event("startup")
def create_bucket_if_needed():
    try:
        s3.head_bucket(Bucket=BUCKET)
    except:
        s3.create_bucket(Bucket=BUCKET)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        s3.put_object(Bucket=BUCKET, Key=file.filename, Body=content)
        return {"message": "File uploaded successfully", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))