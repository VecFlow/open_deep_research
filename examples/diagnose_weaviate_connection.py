"""
Diagnostic script to check Weaviate connectivity and health.
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import weaviate
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

async def check_weaviate_health():
    """Check various aspects of Weaviate connectivity."""
    
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    
    if not weaviate_url:
        print("❌ WEAVIATE_URL environment variable not set!")
        return
    
    print(f"🔍 Checking Weaviate instance at: {weaviate_url}")
    print("-" * 50)
    
    # 1. Check HTTP/REST API connectivity
    print("\n1. Checking REST API connectivity...")
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {weaviate_api_key}"} if weaviate_api_key else {}
            
            # Check health endpoint
            health_url = f"{weaviate_url}/v1/.well-known/ready"
            async with session.get(health_url, headers=headers) as response:
                if response.status == 200:
                    print(f"✅ REST API is healthy (status: {response.status})")
                else:
                    print(f"❌ REST API returned status: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text}")
                    
            # Check schema endpoint
            schema_url = f"{weaviate_url}/v1/schema"
            async with session.get(schema_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Schema endpoint accessible")
                    print(f"   Found {len(data.get('classes', []))} classes")
                    for cls in data.get('classes', []):
                        print(f"   - {cls['class']}")
                else:
                    print(f"❌ Schema endpoint returned status: {response.status}")
                    
    except Exception as e:
        print(f"❌ REST API connection failed: {str(e)}")
    
    # 2. Check gRPC connectivity
    print("\n2. Checking gRPC connectivity...")
    try:
        parsed_url = urlparse(weaviate_url)
        is_weaviate_cloud = '.weaviate.cloud' in parsed_url.hostname or '.weaviate.network' in parsed_url.hostname
        
        if is_weaviate_cloud:
            async_client = weaviate.use_async_with_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.Auth.api_key(weaviate_api_key)
            )
        else:
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
                auth_credentials=weaviate.auth.Auth.api_key(weaviate_api_key) if weaviate_api_key else None
            )
        
        async with async_client:
            # Try to list collections
            collections = await async_client.collections.list_all()
            print(f"✅ gRPC connection successful")
            print(f"   Connected to {len(collections)} collections")
            
    except Exception as e:
        print(f"❌ gRPC connection failed: {str(e)}")
        if "no healthy upstream" in str(e):
            print("   This suggests the gRPC service is down or unreachable")
        elif "reset reason: connection termination" in str(e):
            print("   The connection was terminated - the instance might be restarting")
    
    # 3. Check with minimal connection (no gRPC)
    print("\n3. Trying REST-only connection...")
    try:
        # Create a simple client with only REST (no gRPC)
        from weaviate import Client
        simple_client = Client(
            url=weaviate_url,
            auth_client_secret=weaviate.auth.Auth.api_key(weaviate_api_key) if weaviate_api_key else None
        )
        
        # Try to get schema
        schema = simple_client.schema.get()
        print(f"✅ REST-only connection successful")
        print(f"   Schema has {len(schema.get('classes', []))} classes")
        
    except Exception as e:
        print(f"❌ REST-only connection failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Diagnosis Summary:")
    print("If REST works but gRPC fails, the issue is with the gRPC port/service.")
    print("If both fail, the entire Weaviate instance might be down.")
    print("\nPossible solutions:")
    print("1. Wait a few minutes and try again (instance might be restarting)")
    print("2. Check if your Weaviate Cloud instance is active")
    print("3. Verify your API credentials are correct")
    print("4. Check if you've exceeded any rate limits")

if __name__ == "__main__":
    asyncio.run(check_weaviate_health()) 