import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import logging
import sys
import time

CSV_KNOWLEDGE_BASE_PATH = "./hooli_helpdesk.csv"

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s - %(asctime)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

client = chromadb.PersistentClient(path="chroma_data", settings=chromadb.Settings(anonymized_telemetry=False))
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_or_create_collection(
    name="it_knowledge_base",
    embedding_function=sentence_transformer_ef
)

def load_data_from_csv(csv_file_path: str):
    df = pd.read_csv(csv_file_path)

    if not all(col in df.columns for col in ['Question', 'Answer']):
        raise ValueError("CSV must contain 'Question' and 'Answer' columns")
    
    questions = df['Question'].tolist()
    answers = df['Answer'].tolist()

    logger.info(f"Successfully loaded {len(questions)} QA pairs from CSV")
    
    return questions, answers

def seed_initial_data():
    questions, answers = load_data_from_csv(CSV_KNOWLEDGE_BASE_PATH)
    collection.add(
        documents=questions,
        metadatas=[{"answer": answer} for answer in answers],
        ids=[f"id{i}" for i in range(len(questions))]
    )

if len(collection.get()['ids']) == 0:
    seed_initial_data()
    logger.info("Database seeded with initial data!")
else:
    logger.info("Using existing database")

def search_knowledge(user_query: str, n_results: int = 3):
    results = collection.query(
        query_texts=[user_query],
        n_results=n_results,
        include=["documents", "metadatas"]
    )
    return results

def main():
    while True:
        user_input = input("\nDescribe your IT issue (type 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        
        start_time = time.time()
        results = search_knowledge(user_input)
        
        print(f"\nFound {len(results['documents'][0])} possible answers:")
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            print(f"- Question: {doc}")
            print(f"  Answer: {meta['answer']}")
            print("---")
        
        print(f"Search took {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()