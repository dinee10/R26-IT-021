from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import os
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data"
PERSIST_DIRECTORY = "chroma_db_free"

def load_and_split_documents():
    print("Loading documents from data folder...")

    loader = DirectoryLoader(
        DATA_PATH,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    docs = loader.load()
    print(f"Loaded {len(docs)} document(s)")

    if len(docs) == 0:
        raise FileNotFoundError(f"No .txt files found in '{DATA_PATH}'. Add your documents there first.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")
    return chunks

def ingest_documents():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    
    if os.path.exists(PERSIST_DIRECTORY):
        print(f"✅ Vector store already exists at '{PERSIST_DIRECTORY}'. Loading existing store.")
        vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"}
        )
        print(f"Loaded existing store with {vectorstore._collection.count()} chunks")
        return vectorstore

    chunks = load_and_split_documents()

    print("Creating embeddings and building Chroma vector store...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY,
        collection_metadata={"hnsw:space": "cosine"}  
    )
    print(f"✅ Vector store created successfully at '{PERSIST_DIRECTORY}' with {len(chunks)} chunks!")
    return vectorstore

if __name__ == "__main__":
    ingest_documents()