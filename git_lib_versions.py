import importlib.metadata
packages = [
    "langchain-core",
    "langchain",
    "langchain-openai",
    "streamlit",
    "beautifulsoup4",
    "fastapi",
    "html5lib",
    "jinja2",
    "langchain",
    "langchain-astradb",
    "langchain_core",
    "langchain-google-genai",
    "langchain-groq",
    "lxml",
    "python-dotenv",
    "python-multipart",
    "selenium",
    "streamlit",
    "undetected-chromedriver",
    "uvicorn",
    "structlog",
    "langgraph",
    "ragas",
    "langchain-mcp-adapters",
    "mcp",
    "ddgs",
    "langchain-openai",
]
for pkg in packages:
    try:
        version = importlib.metadata.version(pkg)
        print(f"{pkg}=={version}")
    except importlib.metadata.PackageNotFoundError:
        print(f"{pkg} (not installed)")