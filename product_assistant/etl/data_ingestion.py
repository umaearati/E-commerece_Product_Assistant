import os
import math
import pandas as pd

from dotenv import load_dotenv
from typing import List

from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore

from product_assistant.utils.model_loader import ModelLoader
from product_assistant.utils.config_loader import load_config


class DataIngestion:

    def __init__(self):
        print("Initializing DataIngestion pipeline...")
        self.model_loader = ModelLoader()
        self._load_env_variables()
        self.csv_path = self._get_csv_path()
        self.product_data = self._load_csv()
        self.config = load_config()

    def _load_env_variables(self):
        load_dotenv()
        required_vars = ["OPENAI_API_KEY", "ASTRA_DB_API_ENDPOINT",
                         "ASTRA_DB_APPLICATION_TOKEN", "ASTRA_DB_KEYSPACE"]
        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {missing}")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.db_api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace = os.getenv("ASTRA_DB_KEYSPACE")

    def _get_csv_path(self):
        path = os.path.join(os.getcwd(), "data", "product_reviews.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV not found: {path}")
        return path

    def _load_csv(self):
        df = pd.read_csv(self.csv_path)
        if df.empty:
            raise ValueError("CSV is empty.")
        required = {"product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"}
        if not required.issubset(set(df.columns)):
            raise ValueError(f"CSV must have columns: {required}")
        return df

    def _clean(self, value):
        if pd.isna(value):
            return "N/A"
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return "N/A"
        return str(value).strip()

    def transform_data(self):
        documents = []
        seen_ids = set()

        for _, row in self.product_data.iterrows():
            product_id = self._clean(row["product_id"])
            if product_id in seen_ids:
                continue
            seen_ids.add(product_id)

            title = self._clean(row["product_title"])
            if not title or title in ("Unknown Title", "N/A"):
                continue

            price = self._clean(row["price"])
            rating = self._clean(row["rating"])
            total_reviews = self._clean(row["total_reviews"])
            top_reviews = self._clean(row["top_reviews"])

            parts = [
                f"Product: {title}",
                f"Price: {price}",
                f"Rating: {rating}",
                f"Total Reviews: {total_reviews}",
            ]
            if top_reviews and top_reviews not in ("N/A", "No reviews found", ""):
                parts.append(f"Reviews: {top_reviews}")

            doc = Document(
                page_content=" | ".join(parts),
                metadata={
                    "product_id": product_id,
                    "product_title": title,
                    "rating": rating,
                    "total_reviews": total_reviews,
                    "price": price,
                },
            )
            documents.append(doc)

        print(f"Transformed {len(documents)} valid documents.")
        return documents

    def store_in_vector_db(self, documents: List[Document]):
        if not documents:
            print("No valid documents to insert.")
            return None, []

        collection_name = self.config["astra_db"]["collection_name"]
        embeddings = self.model_loader.load_embeddings()

        # Clear old data first
        try:
            vstore = AstraDBVectorStore(
                embedding=embeddings,
                collection_name=collection_name,
                api_endpoint=self.db_api_endpoint,
                token=self.db_application_token,
                namespace=self.db_keyspace,
            )
            vstore.clear()
            print("🗑️ Cleared old collection data.")
        except Exception as e:
            print(f"⚠️ Could not clear collection: {e}")

        vstore = AstraDBVectorStore(
            embedding=embeddings,
            collection_name=collection_name,
            api_endpoint=self.db_api_endpoint,
            token=self.db_application_token,
            namespace=self.db_keyspace,
        )
        inserted_ids = vstore.add_documents(documents)
        print(f"Successfully inserted {len(inserted_ids)} documents into AstraDB.")
        return vstore, inserted_ids

    def run_pipeline(self):
        documents = self.transform_data()
        if not documents:
            print("No documents available for vector search.")
            return

        vstore, _ = self.store_in_vector_db(documents)
        if not vstore:
            return

        query = "Can you tell me the low budget iphone?"
        results = vstore.similarity_search(query)
        print(f"\nSample search results for query: '{query}'")
        for res in results:
            print(f"Content: {res.page_content}\nMetadata: {res.metadata}\n")


if __name__ == "__main__":
    ingestion = DataIngestion()
    ingestion.run_pipeline()

