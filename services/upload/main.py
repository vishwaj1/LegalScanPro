from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
from docxtpl import DocxTemplate
import os
import uuid
import tempfile
# from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import boto3
import json
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://legal-scan-pro-pyk5.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq setup (commented)
# llm = ChatGroq(model="llama3-8b-8192",
#                 temperature=0,
#                 api_key= os.getenv("GROQ_API_KEY"))

# OpenAI setup
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

R2_ENDPOINT = os.getenv("R2_ENDPOINT")
#MINIO_ENDPOINT = "http://minio:9000"
BUCKET = os.getenv("R2_BUCKET_NAME")
# BUCKET = "legal-docs"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
)

# s3 = boto3.client(
#     "s3",
#     endpoint_url=MINIO_ENDPOINT,
#     aws_access_key_id="minio",
#     aws_secret_access_key="minio123",
# )

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

@app.post("/template-fill/start")
async def start_template_fill(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files supported.")

    # Read the file content directly
    file_content = await file.read()
    
    # Convert DOCX to text
    temp_path = f"/tmp/{uuid.uuid4()}.docx"
    with open(temp_path, "wb") as f:
        f.write(file_content)

    doc = Document(temp_path)
    full_text = "\n".join([p.text for p in doc.paragraphs])
    print(full_text)

    system_prompt = SystemMessage(content="You are a legal assistant that extracts placeholders from a document and generates user-friendly questions.")

    user_prompt = HumanMessage(content=f"""
        You are a smart document parser. Your task is to extract all the fields or placeholders from the document below where a user is expected to fill in custom information. These may include:

        - Bracketed text (e.g., [Company Name], [Date])
        - Underscore blanks (e.g., ____________)
        - Dollar or numeric blanks (e.g., $[________], [00.00])
        - Signature fields, names, titles, addresses, emails

        Return a JSON object of all such fields with a question asking about the field, in the order they appear. Only extract **places where user input is expected**, and do not include static text.
        Please stick to the format of the example output below.
        Example output:
        {{
                {{
                    "placeholder": "[Company Name]",
                    "question": "What is the company name?"
                }},
                ...
        }}
        Here is the document:
        {full_text}

    """)

    response = llm.invoke([system_prompt, user_prompt])

    try:
        # Parse the JSON response from the LLM
        parsed = json.loads(response.content)
        print("Parsed response:", parsed)  # Debug print
    except Exception as e:
        print("Raw response:", response.content)  # Debug print
        raise HTTPException(status_code=500, detail=f"LLM response could not be parsed: {e}")
    
    return {"questions": parsed, "session_id": os.path.basename(temp_path)}

class CompleteRequest(BaseModel):
    session_id: str
    answers: dict


@app.post("/template-fill/complete")
async def complete_template_fill(request: CompleteRequest):
    session_id = request.session_id
    answers = request.answers

    temp_path = f"/tmp/{session_id}"
    if not os.path.exists(temp_path):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        doc = Document(temp_path)
        converted_answers = answers

        def replace_placeholders(text):
            for key, val in converted_answers.items():
                if key.startswith("$") and key in text:
                    text = text.replace(key, f"${val}")
                elif key in ["By", "Name", "Title", "Email", "Address"]:
                    text = text.replace(key, f"{key}: {val}")
                elif key in text:
                    text = text.replace(key, val)
            return text

        for p in doc.paragraphs:
            full_text = "".join(run.text for run in p.runs)
            replaced_text = replace_placeholders(full_text)
            if replaced_text != full_text:
                p.clear()
                p.add_run(replaced_text)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text = "".join(paragraph.text for paragraph in cell.paragraphs)
                    replaced_text = replace_placeholders(full_text)
                    if replaced_text != full_text:
                        cell.text = replaced_text

        filled_path = temp_path.replace(".docx", "_filled.docx")
        doc.save(filled_path)

        # Upload to R2
        key = f"filled_docs/{session_id}"
        with open(filled_path, "rb") as f:
            s3.put_object(
                Bucket=BUCKET,
                Key=key,
                Body=f,
                ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        # Generate a public preview URL
        base_url = os.getenv("R2_PUBLIC_BASE_URL")  # e.g., https://your-cdn-domain.com/legal-scan-pro
        if not base_url:
            raise HTTPException(status_code=500, detail="R2_PUBLIC_BASE_URL not configured")
        public_url = f"{base_url}/{key}"

        return {
            "local_download_url": FileResponse(f"/tmp/{session_id}_filled.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "public_preview_url": public_url
        }

    except Exception as e:
        print(f"ERROR processing document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")
