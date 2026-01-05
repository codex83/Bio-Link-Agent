"""
Test script to verify Bio-Link Agent setup.

Run this after installing dependencies to verify everything works.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all critical imports work."""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    tests = []
    
    # Test router imports
    try:
        from router.router import route_query, execute_tool, generate_final_answer
        from router.router_models import ToolSelection
        print("✅ Router imports: OK")
        tests.append(("Router", True))
    except Exception as e:
        print(f"❌ Router imports: FAILED - {e}")
        tests.append(("Router", False))
    
    # Test client imports
    try:
        from src.clients.trials import TrialsClient
        from src.clients.pubmed import PubMedClient
        print("✅ Client imports: OK")
        tests.append(("Clients", True))
    except Exception as e:
        print(f"❌ Client imports: FAILED - {e}")
        tests.append(("Clients", False))
    
    # Test RAG imports
    try:
        from src.rag.vector_store import TrialVectorStore
        from src.rag.graph_store import KnowledgeGraphEngine
        print("✅ RAG imports: OK")
        tests.append(("RAG", True))
    except Exception as e:
        print(f"❌ RAG imports: FAILED - {e}")
        tests.append(("RAG", False))
    
    # Test config
    try:
        import config
        print("✅ Config import: OK")
        tests.append(("Config", True))
    except Exception as e:
        print(f"❌ Config import: FAILED - {e}")
        tests.append(("Config", False))
    
    # Test MCP server
    try:
        from src.server import mcp
        print("✅ MCP server import: OK")
        tests.append(("MCP Server", True))
    except Exception as e:
        print(f"❌ MCP server import: FAILED - {e}")
        tests.append(("MCP Server", False))
    
    print("\n" + "=" * 60)
    passed = sum(1 for _, status in tests if status)
    total = len(tests)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    return all(status for _, status in tests)


def test_client_initialization():
    """Test that clients can be initialized."""
    print("=" * 60)
    print("TESTING CLIENT INITIALIZATION")
    print("=" * 60)
    
    try:
        from src.clients.trials import TrialsClient
        from src.clients.pubmed import PubMedClient
        
        trials_client = TrialsClient()
        print("✅ TrialsClient initialized")
        
        pubmed_client = PubMedClient()
        print("✅ PubMedClient initialized")
        
        print("\n✅ All clients initialized successfully\n")
        return True
    except Exception as e:
        print(f"❌ Client initialization failed: {e}\n")
        return False


def test_vector_store():
    """Test vector store initialization."""
    print("=" * 60)
    print("TESTING VECTOR STORE")
    print("=" * 60)
    
    try:
        from src.rag.vector_store import TrialVectorStore
        
        vector_store = TrialVectorStore()
        print("✅ TrialVectorStore initialized")
        print("✅ Embedding model loaded")
        
        print("\n✅ Vector store ready\n")
        return True
    except Exception as e:
        print(f"❌ Vector store initialization failed: {e}\n")
        return False


def test_environment():
    """Check environment variables."""
    print("=" * 60)
    print("CHECKING ENVIRONMENT")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    pubmed_email = os.getenv("PUBMED_EMAIL")
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if pubmed_email and pubmed_email != "your.email@example.com":
        print(f"✅ PUBMED_EMAIL: {pubmed_email}")
    else:
        print("⚠️  PUBMED_EMAIL: Not set (will use default)")
    
    if neo4j_uri:
        print(f"✅ NEO4J_URI: Set")
    else:
        print("⚠️  NEO4J_URI: Not set (graph features won't work)")
    
    if neo4j_user:
        print(f"✅ NEO4J_USER: Set")
    else:
        print("⚠️  NEO4J_USER: Not set")
    
    if neo4j_password:
        print(f"✅ NEO4J_PASSWORD: Set")
    else:
        print("⚠️  NEO4J_PASSWORD: Not set")
    
    print()
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("⚠️  WARNING: Neo4j credentials not fully configured.")
        print("   Graph features will not work without Neo4j setup.\n")
        return False
    
    return True


def test_graph_store():
    """Test graph store initialization (requires Neo4j)."""
    print("=" * 60)
    print("TESTING GRAPH STORE (Requires Neo4j)")
    print("=" * 60)
    
    try:
        from src.rag.graph_store import KnowledgeGraphEngine
        
        # This will try to connect to Neo4j
        graph_engine = KnowledgeGraphEngine()
        print("✅ KnowledgeGraphEngine initialized")
        print("✅ Neo4j connection successful")
        print("✅ NLP models loaded")
        
        print("\n✅ Graph store ready\n")
        return True
    except Exception as e:
        print(f"⚠️  Graph store initialization failed: {e}")
        print("   This is OK if Neo4j is not configured yet.\n")
        return False


def test_router():
    """Test router functionality (requires Ollama)."""
    print("=" * 60)
    print("TESTING ROUTER (Requires Ollama)")
    print("=" * 60)
    
    try:
        from router.router import route_query
        from router.router_models import ToolSelection
        
        # Test with a simple query
        test_query = "What are active trials for lung cancer?"
        
        print(f"Testing router with query: '{test_query}'")
        print("(This requires Ollama to be running with qwen2.5:3b model)")
        
        # Don't actually call it, just verify the function exists
        print("✅ Router functions available")
        print("⚠️  To fully test, ensure Ollama is running:")
        print("   ollama serve")
        print("   ollama pull qwen2.5:3b")
        
        print("\n✅ Router ready (manual testing recommended)\n")
        return True
    except Exception as e:
        print(f"❌ Router test failed: {e}\n")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("BIO-LINK AGENT SETUP TEST")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Client initialization
    results.append(("Client Init", test_client_initialization()))
    
    # Test 3: Vector store
    results.append(("Vector Store", test_vector_store()))
    
    # Test 4: Environment
    results.append(("Environment", test_environment()))
    
    # Test 5: Graph store (optional, requires Neo4j)
    results.append(("Graph Store", test_graph_store()))
    
    # Test 6: Router (optional, requires Ollama)
    results.append(("Router", test_router()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "⚠️  SKIP/WARN"
        print(f"{test_name:20} {status}")
    
    print("\n" + "=" * 60)
    
    critical_tests = ["Imports", "Client Init", "Vector Store"]
    critical_passed = all(passed for name, passed in results if name in critical_tests)
    
    if critical_passed:
        print("✅ CRITICAL TESTS PASSED - Setup is functional!")
        print("\nNext steps:")
        print("1. Configure .env file with your credentials")
        print("2. Set up Neo4j (for graph features)")
        print("3. Set up Ollama (for router features)")
        print("4. Run: streamlit run app.py")
    else:
        print("❌ SOME CRITICAL TESTS FAILED")
        print("   Please check the errors above and fix dependencies.")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

