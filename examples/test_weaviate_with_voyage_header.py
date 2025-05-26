"""
Test script that passes VoyageAI API key through headers.
"""

import os
import asyncio
from dotenv import load_dotenv
import weaviate
from urllib.parse import urlparse

# Load existing environment variables
load_dotenv()

# Set the correct environment variables
os.environ['WEAVIATE_COLLECTION_NAME'] = 'Text_tables'

async def test_search():
    """Test the Weaviate search with VoyageAI API key in headers."""
    
    # Get the VoyageAI API key from environment
    voyage_api_key = os.getenv('VOYAGE_APIKEY') or os.getenv('VOYAGE_API_KEY') or os.getenv('VOYAGEAI_APIKEY')
    
    if not voyage_api_key:
        print("No VoyageAI API key found in environment variables!")
        print("Checked: VOYAGE_APIKEY, VOYAGE_API_KEY, VOYAGEAI_APIKEY")
        return
    
    # Get Weaviate connection details
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    
    print(f"Connecting to Weaviate at: {weaviate_url}")
    print(f"Using VoyageAI API key: {voyage_api_key[:10]}...")
    
    # Parse the URL to determine if it's Weaviate Cloud
    parsed_url = urlparse(weaviate_url)
    is_weaviate_cloud = '.weaviate.cloud' in parsed_url.hostname or '.weaviate.network' in parsed_url.hostname
    
    if is_weaviate_cloud:
        # For Weaviate Cloud, use the helper function with headers
        async_client = weaviate.use_async_with_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=weaviate.auth.Auth.api_key(weaviate_api_key),
            headers={
                'X-VoyageAI-Api-Key': voyage_api_key  # Pass VoyageAI key in headers
            }
        )
    else:
        # For custom instances
        http_host = parsed_url.hostname
        http_port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 8080)
        http_secure = parsed_url.scheme == 'https'
        grpc_port = 50051
        grpc_secure = http_secure
        
        async_client = weaviate.use_async_with_custom(
            http_host=http_host,
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=http_host,
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
            auth_credentials=weaviate.auth.Auth.api_key(weaviate_api_key) if weaviate_api_key else None,
            headers={
                'X-VoyageAI-Api-Key': voyage_api_key  # Pass VoyageAI key in headers
            }
        )
    
    async with async_client:
        try:
            # Import the search function
            from open_deep_research.utils import azureaisearch_search_async
            
            # Test queries
            search_queries = [
                "machine learning algorithms",
                "natural language processing",
                "vector databases"
            ]
            
            print(f"\nUsing Weaviate collection: {os.getenv('WEAVIATE_COLLECTION_NAME')}")
            print(f"Testing with queries: {search_queries}")
            print("-" * 50)
            
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