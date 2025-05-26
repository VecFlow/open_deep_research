import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_semantic_search_index():
    """Create an Azure AI Search index with semantic search and vector capabilities"""
    
    # Use the new endpoint with semantic search
    endpoint = "https://testing-vecflow-1.search.windows.net"
    # Try to get API key from specific env var for new service, fallback to general one
    api_key = os.getenv("AZURE_AI_SEARCH_API_KEY_SEMANTIC") or os.getenv("AZURE_AI_SEARCH_API_KEY")
    index_name = "open-deep-research-semantic"
    
    if not api_key:
        print("❌ Error: No API key found!")
        print("Please set one of these environment variables:")
        print("  - AZURE_AI_SEARCH_API_KEY_SEMANTIC (for the new semantic search service)")
        print("  - AZURE_AI_SEARCH_API_KEY")
        return
    
    # Check for Azure OpenAI configuration
    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    if not all([azure_openai_endpoint, azure_openai_key, azure_openai_deployment]):
        print("❌ Error: Azure OpenAI configuration missing!")
        print("Please set these environment variables in your .env file:")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        print("\nWithout Azure OpenAI, the vector search with text queries will not work.")
        return
    
    print(f"Creating semantic search index: {index_name}")
    print(f"Endpoint: {endpoint}")
    print(f"Azure OpenAI Endpoint: {azure_openai_endpoint}")
    print(f"Embedding Deployment: {azure_openai_deployment}")
    print("=" * 60)
    
    # Create index client
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key)
    )
    
    # Define the fields for the index
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            sortable=True,
            filterable=True,
            facetable=True
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
            sortable=True
        ),
        SearchableField(
            name="chunk",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True
        ),
        SearchableField(
            name="url",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
            sortable=True,
            filterable=True
        ),
        SimpleField(
            name="creationTime",
            type=SearchFieldDataType.DateTimeOffset,
            retrievable=True,
            sortable=True,
            filterable=True
        ),
        SimpleField(
            name="lastModifiedTime",
            type=SearchFieldDataType.DateTimeOffset,
            retrievable=True,
            sortable=True,
            filterable=True
        ),
        SearchField(
            name="vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="vector-profile"
        )
    ]
    
    # Configure vector search with a vectorizer
    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config",
                vectorizer_name="openai-vectorizer"
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config"
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="openai-vectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    deployment_name=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"),
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    model_name=os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
                )
            )
        ]
    )
    
    # Configure semantic search
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="fraunhofer-rag-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[
                        SemanticField(field_name="chunk")
                    ],
                    keywords_fields=[
                        SemanticField(field_name="url")
                    ]
                )
            )
        ]
    )
    
    # Create the search index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )
    
    # Create or update the index
    try:
        result = index_client.create_or_update_index(index)
        print(f"✓ Index '{result.name}' created/updated successfully!")
        print(f"  - Semantic search enabled with configuration: 'fraunhofer-rag-semantic-config'")
        print(f"  - Vector search enabled with profile: 'vector-profile'")
        print(f"  - Vectorizer: 'openai-vectorizer' (Azure OpenAI text-embedding-ada-002)")
        print(f"  - Fields: id, title, chunk, url, creationTime, lastModifiedTime, vector")
        
        # Update .env file to use the new index
        print("\n⚠️  IMPORTANT: Update your .env file with:")
        print(f"AZURE_AI_SEARCH_ENDPOINT={endpoint}")
        print(f"AZURE_AI_SEARCH_INDEX_NAME={index_name}")
        print("AZURE_AI_SEARCH_API_KEY=<api-key-for-testing-vecflow-1>")
        print("\nFor vector search, also ensure you have:")
        print("AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>")
        print("AZURE_OPENAI_API_KEY=<your-azure-openai-api-key>")
        print("AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<your-embedding-deployment-name>")
        print("\nNote: The vectorizer will automatically generate embeddings when you search.")
        
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_semantic_search_index() 