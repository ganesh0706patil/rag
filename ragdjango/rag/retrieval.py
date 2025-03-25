import numpy as np
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from django.conf import settings

# Load sentence transformer model
encoder_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Connect to MongoDB
client = MongoClient(settings.MONGO_URI)
db = client["rag_database"]  # Change this to your actual DB name
documents_collection = db["documents"]

def retrieve_answer(query, user):
    """Retrieves the most relevant passage from user's uploaded documents."""
    
    # Get documents uploaded by the current user
    user_docs = list(documents_collection.find({"user_id": user.id}))

    if not user_docs:
        return "No documents found. Please upload some documents."

    # Extract text from the documents
    text_chunks = [doc["text"] for doc in user_docs]

    # Encode query and document chunks
    query_embedding = encoder_model.encode([query])[0]
    doc_embeddings = encoder_model.encode(text_chunks)

    # Compute cosine similarity
    similarities = np.dot(doc_embeddings, query_embedding) / (
        np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
    )

    # Find the most relevant document
    best_idx = np.argmax(similarities)
    return text_chunks[best_idx] if similarities[best_idx] > 0.5 else "No relevant information found."
