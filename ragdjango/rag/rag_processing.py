import os
import faiss
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from transformers import DPRQuestionEncoder, DPRQuestionEncoderTokenizer, DPRContextEncoder, DPRContextEncoderTokenizer
from django.core.files.uploadedfile import InMemoryUploadedFile
import PyPDF2
import docx
import io

# Load FAISS and DPR models
encoder_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
question_encoder = DPRQuestionEncoder.from_pretrained("facebook/dpr-question_encoder-single-nq-base")
question_tokenizer = DPRQuestionEncoderTokenizer.from_pretrained("facebook/dpr-question_encoder-single-nq-base")
context_encoder = DPRContextEncoder.from_pretrained("facebook/dpr-ctx_encoder-single-nq-base")
context_tokenizer = DPRContextEncoderTokenizer.from_pretrained("facebook/dpr-ctx_encoder-single-nq-base")

# Initialize FAISS index
dimension = 768  # Matches the embedding size of sentence transformers
index = faiss.IndexFlatL2(dimension)
doc_store = []  # Stores extracted text

def extract_text_from_file(uploaded_file: InMemoryUploadedFile):
    """Extracts text from uploaded PDF, DOCX, or TXT files."""
    text = ""

    if uploaded_file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(uploaded_file)
        text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
    
    elif uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        text = " ".join([para.text for para in doc.paragraphs])
    
    elif uploaded_file.name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")

    return text

def process_uploaded_files(uploaded_files):
    """Processes multiple uploaded files and stores their embeddings in FAISS."""
    global doc_store, index

    extracted_texts = []
    for file in uploaded_files:
        extracted_text = extract_text_from_file(file)
        extracted_texts.append(extracted_text)

    # Chunk documents into smaller parts
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = [chunk for text in extracted_texts for chunk in splitter.split_text(text)]

    # Store chunks and compute embeddings
    embeddings = encoder_model.encode(chunks)
    index.add(np.array(embeddings, dtype=np.float32))
    doc_store.extend(chunks)

    return chunks  # Returning stored document chunks for session storage

def retrieve_answer(query, documents):
    """Retrieves the most relevant passage using FAISS + DPR for a given query."""
    if not documents:
        return "No documents available. Please upload files first."

    # Encode the query
    query_embedding = encoder_model.encode([query])[0]

    # Search in FAISS
    D, I = index.search(np.array([query_embedding], dtype=np.float32), k=3)  # Retrieve top 3 results
    retrieved_texts = [doc_store[i] for i in I[0] if i < len(doc_store)]

    return retrieved_texts[0] if retrieved_texts else "No relevant information found."
