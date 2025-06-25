from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
from docxtpl import DocxTemplate
import os
import uuid
import tempfile
import re
# from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import boto3
import json
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://legal-scan-pro-pyk5.vercel.app",
        "http://localhost:3000",
        "https://www.legal-scan-pro-pyk5.vercel.app"  # (optional, for www)
    ],
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

    try:
        file_content = await file.read()
        s3.put_object(Bucket=BUCKET, Key=file.filename, Body=file_content)
        #return {"message": "File uploaded successfully", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files supported.")

    # Read the file content directly
    #file_content = await file.read()
    
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
    #parsed = {'fields': [{'placeholder': '[Company Name]', 'question': 'What is the company name?'}, {'placeholder': '[Investor Name]', 'question': "What is the investor's name?"}, {'placeholder': '$[_____________]', 'question': 'What is the purchase amount?'}, {'placeholder': '[Date of Safe]', 'question': 'What is the date of the SAFE?'}, {'placeholder': '[Company Name]', 'question': 'What is the company name?'}, {'placeholder': '[State of Incorporation]', 'question': 'What is the state of incorporation?'}, {'placeholder': '$[_____________]', 'question': 'What is the post-money valuation cap?'}, {'placeholder': '[Governing Law Jurisdiction]', 'question': 'What is the governing law jurisdiction?'}, {'placeholder': '[COMPANY]', 'question': 'What is the company name?'}, {'placeholder': '[name]', 'question': 'What is the name of the person signing on behalf of the company?'}, {'placeholder': '[title]', 'question': 'What is the title of the person signing on behalf of the company?'}, {'placeholder': 'Address', 'question': "What is the company's address?"}, {'placeholder': 'Email', 'question': "What is the company's email?"}, {'placeholder': 'INVESTOR:', 'question': 'Who is the investor?'}, {'placeholder': 'By:', 'question': 'Who is signing on behalf of the investor?'}, {'placeholder': 'Name:', 'question': 'What is the name of the person signing on behalf of the investor?'}, {'placeholder': 'Title:', 'question': 'What is the title of the person signing on behalf of the investor?'}, {'placeholder': 'Address:', 'question': "What is the investor's address?"}, {'placeholder': 'Email:', 'question': "What is the investor's email?"}]}

    try:
        
        # Parse the JSON response from the LLM
        parsed = json.loads(response.content)
        print("Parsed response:", parsed)  # Debug print
    except Exception as e:
        #  print("Raw response:", response.content)  # Debug print
        raise HTTPException(status_code=500, detail=f"LLM response could not be parsed: {e}")
    
    return {"questions": parsed, "session_id": os.path.basename(temp_path)}

class CompleteRequest(BaseModel):
    session_id: str
    answers: list  # List of objects with placeholder, answer, index


@app.post("/template-fill/complete")
async def complete_template_fill(request: CompleteRequest):
    try:
        placeholder_answer_pairs = {a['placeholder']: a['answer'].replace('\n', ' ').replace('\r', '') for a in request.answers}
        temp_path = f"/tmp/{request.session_id}"
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="Session file not found")

        doc = Document(temp_path)

        def replace_in_runs(runs):
            merged_text = ''.join(run.text for run in runs)
            replaced_text = merged_text
            for placeholder, answer in placeholder_answer_pairs.items():
                # Handle $[_____] type
                if placeholder.startswith("$"):
                    replaced_text = replaced_text.replace(placeholder, f"${answer}")
                # Handle Name: ______ type
                elif placeholder in ["By", "Name", "Title", "Email", "Address", "INVESTOR"]:
                    replaced_text = re.sub(fr"({placeholder}:\s*)([_\s]*)", fr"\1{answer.strip()}", replaced_text, flags=re.MULTILINE)
                else:
                    # Try exact match
                    if placeholder in replaced_text:
                        replaced_text = replaced_text.replace(placeholder, answer)
                    else:
                        # Try fallback to original key if placeholder has _2, _3, etc.
                        if "_" in placeholder and placeholder.split("_")[-1].isdigit():
                            fallback = "_".join(placeholder.split("_")[:-1])
                            if fallback in replaced_text:
                                replaced_text = replaced_text.replace(fallback, answer)

            if replaced_text != merged_text:
                for run in runs:
                    run.text = ''
                if runs:
                    runs[0].text = replaced_text

        for paragraph in doc.paragraphs:
            replace_in_runs(paragraph.runs)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_runs(paragraph.runs)

        filled_path = f"/tmp/{request.session_id}_filled.docx"
        doc.save(filled_path)

        key = f"filled_docs/{request.session_id}_filled.docx"
        with open(filled_path, "rb") as f:
            s3.put_object(
                Bucket=BUCKET,
                Key=key,
                Body=f,
                ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        base_url = os.getenv("R2_PUBLIC_BASE_URL")
        if not base_url:
            raise HTTPException(status_code=500, detail="R2_PUBLIC_BASE_URL not configured")
        public_url = f"{base_url}/{key}"

        return {
            "public_preview_url": public_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {e}")
