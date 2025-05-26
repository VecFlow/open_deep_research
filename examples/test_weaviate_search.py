"""
Example script to test Weaviate search functionality.

This script demonstrates how the azureaisearch_search_async function
now uses Weaviate for vector search instead of Azure AI Search.

Required environment variables:
- WEAVIATE_URL: The URL of your Weaviate instance
- WEAVIATE_API_KEY: Your Weaviate API key
- WEAVIATE_COLLECTION_NAME: (Optional) The name of your collection (defaults to "Documents")
"""

import asyncio
import os
from dotenv import load_dotenv
from open_deep_research.utils import azureaisearch_search_async

# Load environment variables
load_dotenv()

async def test_weaviate_search():
    """Test the Weaviate search functionality."""
    
    # Example search queries
    search_queries = [
        "machine learning algorithms",
        "natural language processing",
        "vector databases"
    ]
    
    print("Testing Weaviate search with the following queries:")
    for query in search_queries:
        print(f"  - {query}")
    print()
    
    try:
        # Perform the search
        results = await azureaisearch_search_async(
            search_queries=search_queries,
            max_results=3,
            topic="general",  # Note: This parameter is currently unused with Weaviate
            include_raw_content=True
        )
        
        # Display results
        for result_set in results:
            query = result_set.get("query", "Unknown")
            print(f"\nResults for query: '{query}'")
            print("-" * 50)
            
            if "error" in result_set:
                print(f"Error: {result_set['error']}")
                continue
                
            for i, result in enumerate(result_set.get("results", []), 1):
                print(f"\n{i}. {result.get('title', 'No title')}")
                print(f"   URL: {result.get('url', 'No URL')}")
                print(f"   Score: {result.get('score', 'No score')}")
                print(f"   Content: {result.get('content', 'No content')[:200]}...")
                
    except Exception as e:
        print(f"Error during search: {str(e)}")
        print("\nMake sure you have set the following environment variables:")
        print("  - WEAVIATE_URL")
        print("  - WEAVIATE_API_KEY")
        print("  - WEAVIATE_COLLECTION_NAME (optional)")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(test_weaviate_search()) 