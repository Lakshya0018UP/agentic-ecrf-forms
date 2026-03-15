import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from langchain_core.documents import Document

load_dotenv()

# Configuration
PROTOCOL_DIR = "data/protocol"
COLLECTION_NAME = "protocol_collection"
QDRANT_URL = "http://localhost:6333"

def index_text_content(text: str, source_id: str):
    """Indexes raw text (e.g. from API) into Qdrant."""
    print(f"Indexing text from source {source_id}...")
    
    # Wrap text in a LangChain Document
    doc = Document(page_content=text, metadata={"source": source_id})
    
    # 2. Split Text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    texts = text_splitter.split_documents([doc])
    
    # 3. Embed and Store using Ollama
    embedding = OllamaEmbeddings(model="nomic-embed-text")
    client = QdrantClient(url=QDRANT_URL)
    
    # Recreate collection for fresh start
    collections = client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        client.delete_collection(COLLECTION_NAME)
    
    QdrantVectorStore.from_documents(
        texts,
        embedding=embedding,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME
    )
    print("Ingestion from text complete!")

def run_ingestion():
    # 1. Load Files (PDF or DOCX)
    files = [f for f in os.listdir(PROTOCOL_DIR) if f.endswith(('.pdf', '.docx'))]
    if not files:
        print("No PDF or DOCX found in data/protocol/")
        return
    
    all_documents = []
    for file in files:
        file_path = os.path.join(PROTOCOL_DIR, file)
        print(f"Loading {file_path}...")
        if file.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        else:
            continue
        all_documents.extend(loader.load())
    
    # 2. Split Text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    texts = text_splitter.split_documents(all_documents)
    
    # 3. Embed and Store in Qdrant using Ollama (nomic-embed-text)
    embedding = OllamaEmbeddings(model="nomic-embed-text")
    
    print(f"Indexing {len(texts)} chunks into Qdrant using Ollama Embeddings...")
    
    # Manually handle collection recreation
    client = QdrantClient(url=QDRANT_URL)
    collections = client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        client.delete_collection(COLLECTION_NAME)
    
    QdrantVectorStore.from_documents(
        texts,
        embedding=embedding,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME
    )
    print("Ingestion Complete!")

if __name__ == "__main__":
    run_ingestion()
