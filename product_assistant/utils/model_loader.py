import os
import sys
import json
from dotenv import load_dotenv
from product_assistant.utils.config_loader import load_config
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_groq import ChatGroq
from product_assistant.logger import GLOBAL_LOGGER as log
from product_assistant.exception.custom_exception import ProductAssistantException
import asyncio



# class ApiKeyManager:
#     def __init__(self):
#         self.api_keys = {
#             "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
#             "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
#             "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
#             "ASTRA_DB_API_ENDPOINT": os.getenv("ASTRA_DB_API_ENDPOINT"),
#             "ASTRA_DB_APPLICATION_TOKEN": os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
#             "ASTRA_DB_KEYSPACE": os.getenv("ASTRA_DB_KEYSPACE"),
#         }

#         # Just log loaded keys (don't print actual values)
#         for key, val in self.api_keys.items():
#             if val:
#                 log.info(f"{key} loaded from environment")
#             else:
#                 log.warning(f"{key} is missing from environment")

#     def get(self, key: str):
#         return self.api_keys.get(key)

# class ModelLoader:
#     """
#     Loads embedding models and LLMs based on config and environment.
#     """

#     def __init__(self):
#         self.api_key_mgr = ApiKeyManager()
#         self.config = load_config()
#         log.info("YAML config loaded", config_keys=list(self.config.keys()))

    

#     def load_embeddings(self):
#         """
#         Load and return embedding model from Openai Generative AI.
#         """
#         try:
#             model_name = self.config["embedding_model"]["model_name"]
#             log.info("Loading embedding model", model=model_name)

#             # Patch: Ensure an event loop exists for gRPC aio
#             try:
#                 asyncio.get_running_loop()
#             except RuntimeError:
#                 asyncio.set_event_loop(asyncio.new_event_loop())

#             return GoogleGenerativeAIEmbeddings(
#                 model=model_name,
#                 openai_api_key=self.api_key_mgr.get("OPENAI_API_KEY")  # type: ignore
#             )
#         except Exception as e:
#             log.error("Error loading embedding model", error=str(e))
#             raise ProductAssistantException("Failed to load embedding model", sys)


#     def load_llm(self):
#         """
#         Load and return the configured LLM model.
#         """
#         llm_block = self.config["llm"]
#         provider_key = os.getenv("LLM_PROVIDER", "openai")

#         if provider_key not in llm_block:
#             log.error("LLM provider not found in config", provider=provider_key)
#             raise ValueError(f"LLM provider '{provider_key}' not found in config")

#         llm_config = llm_block[provider_key]
#         provider = llm_config.get("provider")
#         model_name = llm_config.get("model_name")
#         temperature = llm_config.get("temperature", 0.2)
#         max_tokens = llm_config.get("max_output_tokens", 2048)

#         log.info("Loading LLM", provider=provider, model=model_name)

#         if provider == "google":
#             return ChatGoogleGenerativeAI(
#                 model=model_name,
#                 google_api_key=self.api_key_mgr.get("GOOGLE_API_KEY"),
#                 temperature=temperature,
#                 max_output_tokens=max_tokens
#             )

#         elif provider == "groq":
#             return ChatGroq(
#                 model=model_name,
#                 api_key=self.api_key_mgr.get("GROQ_API_KEY"), #type: ignore
#                 temperature=temperature,
#             )

#         elif provider == "openai":
#             return ChatOpenAI(
#                 model=model_name,
#                 api_key=self.api_key_mgr.get("OPENAI_API_KEY"),
#                 temperature=temperature
#             )

#         else:
#             log.error("Unsupported LLM provider", provider=provider)
#             raise ValueError(f"Unsupported LLM provider: {provider}")


# if __name__ == "__main__":
#     loader = ModelLoader()

#     # Test Embedding
#     embeddings = loader.load_embeddings()
#     print(f"Embedding Model Loaded: {embeddings}")
#     result = embeddings.embed_query("Hello, how are you?")
#     print(f"Embedding Result: {result}")

#     # Test LLM
#     llm = loader.load_llm()
#     print(f"LLM Loaded: {llm}")
#     result = llm.invoke("Hello, how are you?")
#     print(f"LLM Result: {result.content}")





class ApiKeyManager:
    def __init__(self):
        load_dotenv()  # make sure .env is loaded

        self.api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
            "ASTRA_DB_API_ENDPOINT": os.getenv("ASTRA_DB_API_ENDPOINT"),
            "ASTRA_DB_APPLICATION_TOKEN": os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            "ASTRA_DB_KEYSPACE": os.getenv("ASTRA_DB_KEYSPACE"),
        }

        # Log which keys exist (no secrets)
        for key, val in self.api_keys.items():
            if val:
                log.info("%s loaded from environment", key)
            else:
                log.warning("%s is missing from environment", key)

    def get(self, key: str):
        return self.api_keys.get(key)


class ModelLoader:
    """
    Loads embeddings + LLM based on config and environment.
    Embeddings: OpenAI (Groq does not support embeddings)
    LLM: OpenAI or Groq
    """

    def __init__(self):
        try:
            self.api_key_mgr = ApiKeyManager()
            self.config = load_config()
            log.info("YAML config loaded | config_keys=%s", list(self.config.keys()))
        except Exception as e:
            log.error("Error initializing ModelLoader | error=%s", str(e), exc_info=True)
            raise ProductAssistantException("Failed to initialize ModelLoader", sys)

    def load_embeddings(self):
        """
        Load and return embeddings model.
        NOTE: Groq doesn't provide embeddings, so we use OpenAI embeddings.
        """
        try:
            model_name = self.config.get("embedding_model", {}).get(
                "model_name", "text-embedding-3-small"
            )

            api_key = self.api_key_mgr.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is missing. Required for embeddings.")

            log.info("Loading embeddings | provider=openai | model=%s", model_name)

            # OpenAI embeddings
            embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
            )

            log.info("Embeddings loaded successfully | provider=openai | model=%s", model_name)
            return embeddings

        except Exception as e:
            log.error("Error loading embedding model | error=%s", str(e), exc_info=True)
            raise ProductAssistantException("Failed to load embedding model", sys)

    def load_llm(self):
        """
        Load and return the configured LLM model.
        Supported: openai, groq
        Choose using env: LLM_PROVIDER=openai|groq
        """
        try:
            llm_block = self.config.get("llm", {})
            provider_key = os.getenv("LLM_PROVIDER", "openai").lower()

            if provider_key not in llm_block:
                raise ValueError(f"LLM provider '{provider_key}' not found in config")

            llm_config = llm_block[provider_key]
            provider = llm_config.get("provider", provider_key)
            model_name = llm_config.get("model_name")
            temperature = llm_config.get("temperature", 0.2)
            max_tokens = llm_config.get("max_output_tokens", 2048)

            log.info("Loading LLM | provider=%s | model=%s", provider, model_name)

            if provider_key == "openai":
                api_key = self.api_key_mgr.get("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY is missing but LLM_PROVIDER=openai")

                llm = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            elif provider_key == "groq":
                api_key = self.api_key_mgr.get("GROQ_API_KEY")
                if not api_key:
                    raise ValueError("GROQ_API_KEY is missing but LLM_PROVIDER=groq")

                llm = ChatGroq(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                )

            else:
                raise ValueError(f"Unsupported LLM provider: {provider_key}")

            log.info("LLM loaded successfully | provider=%s | model=%s", provider_key, model_name)
            return llm

        except Exception as e:
            log.error("Error loading LLM | error=%s", str(e), exc_info=True)
            raise ProductAssistantException("Failed to load LLM", sys)


if __name__ == "__main__":
    loader = ModelLoader()

    # Test Embeddings (OpenAI)
    embeddings = loader.load_embeddings()
    print(f"Embeddings Loaded: {embeddings}")
    vec = embeddings.embed_query("Hello, how are you?")
    print(f"Embedding sample: {vec[:5]}")

    # Test LLM (OpenAI or Groq)
    llm = loader.load_llm()
    print(f"LLM Loaded: {llm}")
    res = llm.invoke("Hello, how are you?")
    print(f"LLM Result: {res.content}")
