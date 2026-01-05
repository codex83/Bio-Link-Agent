"""
Configuration constants for Bio-Link Agent

Centralized configuration for embedding models, LLM models, and other settings.
"""

# Embedding Model Configuration
# Options:
#   - "all-MiniLM-L6-v2" (default, fast, general-purpose, 384 dims)
#   - "dmis-lab/biobert-base-cased-v1.1" (biomedical domain-specific, 768 dims, slower)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ollama LLM Model Configuration
# Used for router decisions and answer generation
# Options:
#   - "qwen2.5:3b" (default, fast, small)
#   - "llama3:8b" (larger, better quality)
#   - "gemma3:12b" (if available)
OLLAMA_MODEL = "qwen2.5:3b"

# Neo4j Database Configuration
NEO4J_DATABASE = "neo4j"

# Vector Database Configuration
CHROMA_PERSIST_DIR = "./data/indexed_trials"

# API Rate Limiting
CLINICAL_TRIALS_RATE_LIMIT = 0.5  # seconds between requests
PUBMED_RATE_LIMIT = 0.1  # seconds between requests

# Default Limits
DEFAULT_MAX_PAPERS = 10
DEFAULT_MAX_TRIALS = 10
DEFAULT_SEARCH_LIMIT = 5

# Graph Visualization
GRAPH_MAX_NODES = 100  # Limit nodes for visualization performance

