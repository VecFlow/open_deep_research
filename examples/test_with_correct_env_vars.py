"""
Test script with correct environment variables for Weaviate.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load existing environment variables
load_dotenv()

# Set the correct environment variables
os.environ['WEAVIATE_COLLECTION_NAME'] = 'Text_tables'
# Copy the VoyageAI API key to the correct environment variable name
if 'VOYAGE_APIKEY' in os.environ:
    os.environ['VOYAGEAI_APIKEY'] = os.environ['VOYAGE_APIKEY']
elif 'VOYAGE_API_KEY' in os.environ:
    os.environ['VOYAGEAI_APIKEY'] = os.environ['VOYAGE_API_KEY']

# Now import and run the search function
from open_deep_research.utils import azureaisearch_search_async

async def test_search():
    """Test the Weaviate search with correct environment variables."""
    
    # Test queries
    search_queries = [
        "machine learning algorithms",
        "natural language processing",
        "vector databases"
    ]
    
    print(f"Using Weaviate collection: {os.getenv('WEAVIATE_COLLECTION_NAME')}")
    print(f"VoyageAI API key set: {'VOYAGEAI_APIKEY' in os.environ}")
    print(f"Testing with queries: {search_queries}")
    print("-" * 50)
    
    try:
        # Perform the search
        results = await azureaisearch_search_async(
            search_queries=search_queries,
            max_results=3,
            topic="general",
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
                
            results_list = result_set.get("results", [])
            if not results_list:
                print("No results found.")
                continue
                
            for i, result in enumerate(results_list, 1):
                print(f"\n{i}. Title: {result.get('title', 'No title')}")
                print(f"   URL: {result.get('url', 'No URL')}")
                print(f"   Score: {result.get('score', 'No score')}")
                
                content = result.get('content', 'No content')
                if content:
                    # Show first 200 characters of content
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   Content: {preview}")
                
    except Exception as e:
        print(f"Error during search: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search()) 