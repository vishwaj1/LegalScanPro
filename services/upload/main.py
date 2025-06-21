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
    session_id = request.session_id
    answers = request.answers  # This is a list of objects

    temp_path = f"/tmp/{session_id}"
    if not os.path.exists(temp_path):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        doc = Document(temp_path)
        
        # Convert answers array to a dictionary for easier processing
        # Each answer object has: {placeholder, answer, index}
        converted_answers = {}
        for answer_obj in answers:
            placeholder = answer_obj["placeholder"]
            answer_value = answer_obj["answer"]
            index = answer_obj["index"]
            
            # Create unique key for duplicates based on order
            if placeholder in converted_answers:
                # Count how many times this placeholder has appeared so far
                count = sum(1 for a in answers[:index] if a["placeholder"] == placeholder) + 1
                unique_key = f"{placeholder}_{count}"
            else:
                unique_key = placeholder
            
            converted_answers[unique_key] = answer_value
            print(f"Processing field {index + 1}: {unique_key} = {answer_value}")

        def replace_placeholders(text):
            keys_to_remove = []
            for key, val in converted_answers.items():
                # Handle unique keys created by frontend (e.g., [Company Name]_2)
                original_placeholder = key.split('_')[0] if '_' in key and key.split('_')[-1].isdigit() else key
                
                if key.startswith("$") and key in text:
                    text = text.replace(key, f"${val}")
                    keys_to_remove.append(key)
                elif key in ["By", "Name", "Title", "Email", "Address"]:
                    text = text.replace(key, f"{key}: {val}")
                    keys_to_remove.append(key)
                elif key in text:
                    text = text.replace(key, val)
                    keys_to_remove.append(key)
                elif original_placeholder in text:
                    # Try matching with original placeholder (without suffix)
                    text = text.replace(original_placeholder, val)
                    keys_to_remove.append(key)
            
            # Remove used keys from converted_answers
            for key in keys_to_remove:
                if key in converted_answers:
                    del converted_answers[key]
            
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
