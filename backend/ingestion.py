from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
from dotenv import load_dotenv

load_dotenv()

def ingest_documents():
    print("Loading documents from data folder...")

    loader = DirectoryLoader(
        "data",                      # Changed from "docs"
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    docs = loader.load()
    print(f"Loaded {len(docs)} document(s)")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700, 
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="chroma_db_free"
    )

    print("✅ Vector Store Created Successfully in 'chroma_db_free'!")

if __name__ == "__main__":
    ingest_documents()