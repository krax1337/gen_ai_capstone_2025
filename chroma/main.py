import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
import logging
import sys
import time

class ChromaKnowledgeBase:
    def __init__(self, db_path: str = "chroma_data", collection_name: str = "it_knowledge_base"):
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s - %(asctime)s] %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=db_path, 
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding function
        self.sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.sentence_transformer_ef
        )

    def load_data_from_csv(self, csv_file_path: str):
        df = pd.read_csv(csv_file_path)

        if not all(col in df.columns for col in ['Question', 'Answer']):
            raise ValueError("CSV must contain 'Question' and 'Answer' columns")
        
        questions = df['Question'].tolist()
        answers = df['Answer'].tolist()

        self.logger.info(f"Successfully loaded {len(questions)} QA pairs from CSV")
        
        return questions, answers

    def seed_initial_data(self, csv_file_path: str):
        questions, answers = self.load_data_from_csv(csv_file_path)
        self.collection.add(
            documents=questions,
            metadatas=[{"answer": answer} for answer in answers],
            ids=[f"id{i}" for i in range(len(questions))]
        )

    def initialize_database(self, csv_file_path: str):
        if len(self.collection.get()['ids']) == 0:
            self.seed_initial_data(csv_file_path)
            self.logger.info("Database seeded with initial data!")
        else:
            self.logger.info("Using existing database")

    def search_knowledge(self, user_query: str, n_results: int = 3):
        self.logger.info(f"Searching for '{user_query}'")
        start_time = time.time()
        results = self.collection.query(
            query_texts=[user_query],
            n_results=n_results,
            include=["documents", "metadatas"]
        )
        self.logger.info(f"Search took {time.time() - start_time:.2f} seconds")
        self.logger.info(f"Result: '{results['metadatas'][0][0]['answer']}'")
        return results['metadatas'][0][0]['answer']

# Example usage
if __name__ == "__main__":
    CSV_KNOWLEDGE_BASE_PATH = "../hooli_helpdesk.csv"
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s - %(asctime)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    kb = ChromaKnowledgeBase()
    kb.initialize_database(CSV_KNOWLEDGE_BASE_PATH)
    result = kb.search_knowledge("How do I reset my password?")
    print(result)