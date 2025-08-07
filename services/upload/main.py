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

    system_prompt = SystemMessage(
        content=(
            "You are a legal assistant. Extract placeholders from a legal "
            "document and craft concise questions to gather the missing "
            "information. Respond only with valid JSON."
        )
    )

    user_prompt = HumanMessage(
        content=f"""
        Identify every location in the document below where user supplied information is
        required. Examples include bracketed text like [Company Name], blank lines of
        underscores, amounts with blanks, or signature blocks (e.g. \"Name:\").

        List the placeholders in the exact order they appear and produce a short plain
        English question for each. Use the placeholder exactly as it appears in the
        document. If the same placeholder appears multiple times, include each
        occurrence separately in the list.

        Respond **only** with JSON in the following structure:
        {{
        "fields": [
            {{"placeholder": "[Company Name]", "question": "What is the company name?"}},
            ...
        ]
        }}

        Document:
        {full_text}
        """
            )

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
        # Preserve the exact order of answers from frontend
        ordered_answers = sorted(request.answers, key=lambda x: x['index'])
        placeholder_answer_pairs = {}
        
        # Create mapping in the exact order received
        for answer_obj in ordered_answers:
            placeholder = answer_obj['placeholder']
            answer = answer_obj['answer'].replace('\n', ' ').replace('\r', '')
            index = answer_obj['index']
            
            # For duplicates, create unique keys based on order
            if placeholder in placeholder_answer_pairs:
                # Count how many times this placeholder has appeared so far
                count = sum(1 for a in ordered_answers[:index] if a['placeholder'] == placeholder) + 1
                unique_key = f"{placeholder}_{count}"
            else:
                unique_key = placeholder
            
            placeholder_answer_pairs[unique_key] = answer
            print(f"Processing field {index + 1}: {unique_key} = {answer}")
        
        print("Final placeholder-answer pairs:", placeholder_answer_pairs)

        first_block, second_block = {}, {}
        company = False
        investor = False
        for placeholder, answer in placeholder_answer_pairs.items():
            if placeholder == "[COMPANY]":
                company = True
            if placeholder == "INVESTOR:":
                company = False
                investor = True
            if company:
                first_block[placeholder] = answer
            if investor:
                second_block[placeholder] = answer
            if placeholder == "Email_2":
                investor = False
        print(first_block)
        print(second_block)

        temp_path = f"/tmp/{request.session_id}"
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="Session file not found")

        doc = Document(temp_path)

        def contains_safe(doc_path):
            doc = Document(doc_path)
            for para in doc.paragraphs:
                if "safe" in para.text.lower():
                    return True
            return False
        value = 0
        def replace_in_runs(runs, block):
            nonlocal value
            merged_text = ''.join(run.text for run in runs)
            replaced_text = merged_text
            keys_to_remove = []
            print(block,replaced_text)
            for placeholder, answer in block.items():
                if "_" in placeholder and placeholder.split("_")[-1].isdigit():
                    placeholder = "_".join(placeholder.split("_")[:-1])
                # Handle $[_____] type
                if placeholder.startswith("$["):
                    if value == answer:
                        continue
                    value = answer
                    replaced_text = replaced_text.replace(placeholder, f"${answer}")
                    #keys_to_remove.append(placeholder)
                elif placeholder.startswith("By:"):
                    replaced_text = replaced_text.replace(placeholder, f"{placeholder.split(':')[0]} - {answer}")
                    #keys_to_remove.append(placeholder)
                # Handle Name: ______ type
                elif placeholder in ["Name:", "Title:", "Email:", "Address:", "INVESTOR:"]:
                    replaced_text = replaced_text.replace(placeholder, f"{placeholder.split(':')[0]} - {answer}")
                    #keys_to_remove.append(placeholder)
                    
                else:
                    # Try exact match
                    if placeholder in replaced_text:
                        replaced_text = replaced_text.replace(placeholder, answer)
                        #keys_to_remove.append(placeholder)

            # for key in keys_to_remove:
            #    if key in placeholder_answer_pairs:
            #        del placeholder_answer_pairs[key]

            if replaced_text != merged_text:
                for run in runs:
                    run.text = ''
                if runs:
                    runs[0].text = replaced_text
        
        if contains_safe(temp_path):
            print("Contains safe")

            for paragraph in doc.paragraphs:
                replace_in_runs(paragraph.runs,placeholder_answer_pairs)
                if 'Section 2' in paragraph.text:
                    break
            
            company_place = '[COMPANY]'
            investor_place = 'INVESTOR:'
            company_started = False
            investor_started = False
            for para in doc.paragraphs:
                if company_place in para.text and not company_started:
                    print("Company started", para.text)
                    company_started = True
                if investor_place in para.text and not investor_started:
                    print("Investor started", para.text)
                    investor_started = True
                    company_started = False
                if company_started:
                    replace_in_runs(para.runs, first_block)
                if investor_started:
                    replace_in_runs(para.runs, second_block)
        else:
                print("No safe")
                for para in doc.paragraphs:
                    replace_in_runs(para.runs, placeholder_answer_pairs)
        
        

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
