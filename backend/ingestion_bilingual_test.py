import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data"
PERSIST_DIRECTORY = "chroma_db_bilingual_refs_test"


def load_and_split_documents():
    """
    Each source file uses blank-line-separated entries (one plant or one
    disease per block, separated by "\n\n\n"). A size-based splitter
    (RecursiveCharacterTextSplitter) doesn't work well here: it both cuts
    long entries in half AND merges short neighboring entries together,
    since entry lengths vary widely across files (852-3219 chars). So
    instead we split directly on the real entry boundary and keep each
    entry as exactly one chunk, no matter its length. This guarantees a
    disease/plant's Description, Typical Symptoms, and Recommended Action
    never get separated, and two different plants never get merged.
    """
    print("Loading documents from data folder...")

    loader = DirectoryLoader(
        DATA_PATH,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    docs = loader.load()
    print(f"Loaded {len(docs)} document(s)")

    if len(docs) == 0:
        raise FileNotFoundError(f"No .txt files found in '{DATA_PATH}'. Add your documents there first.")

    chunks = []
    for doc in docs:
        entries = doc.page_content.split("\n\n\n")
        for entry in entries:
            entry = entry.strip()
            if entry:
                chunks.append(Document(page_content=entry, metadata=doc.metadata))

    print(f"Created {len(chunks)} chunks")
    return chunks


def ingest_documents():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    if os.path.exists(PERSIST_DIRECTORY):
        print(f"OK: Vector store already exists at '{PERSIST_DIRECTORY}'. Loading existing store.")
        vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"}
        )
        chunk_count = vectorstore._collection.count()
        print(f"Loaded existing store with {chunk_count} chunks")
        if chunk_count > 0:
            return vectorstore
        print("Existing store is empty. Rebuilding from source documents.")

    chunks = load_and_split_documents()

    print("Creating embeddings and building Chroma vector store...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY,
        collection_metadata={"hnsw:space": "cosine"}
    )
    print(f"OK: Vector store created successfully at '{PERSIST_DIRECTORY}' with {len(chunks)} chunks!")
    return vectorstore


if __name__ == "__main__":
    ingest_documents()