"""Vector Store Service for Pinecone Integration"""

import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import pinecone
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.utils.logger import get_logger
from src.database.models import KnowledgeUpdate
from src.database.connection import AsyncSessionLocal

logger = get_logger(__name__)


@dataclass
class VectorResult:
    """Vector search result"""
    id: str
    score: float
    content: str
    metadata: Dict
    source: str
    last_updated: Optional[datetime] = None


@dataclass
class SearchResult:
    """Combined search result with freshness info"""
    results: List[VectorResult]
    is_fresh: bool
    confidence: float
    needs_web_search: bool
    query_embedding: List[float]


class VectorStoreService:
    """Advanced vector store service with freshness detection"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.sentence_transformer = None
        self.index = None
        self._initialize_pinecone()
        self._initialize_embeddings()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone client and index"""
        try:
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            
            # Check if index exists, create if not
            if settings.PINECONE_INDEX_NAME not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
                pinecone.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.PINECONE_DIMENSION,
                    metric="cosine",
                    metadata_config={
                        "indexed": ["source", "content_type", "last_updated", "campus"]
                    }
                )
            
            self.index = pinecone.Index(settings.PINECONE_INDEX_NAME)
            logger.info("Pinecone initialization successful")
            
        except Exception as e:
            logger.error(f"Pinecone initialization failed: {e}")
            raise
    
    def _initialize_embeddings(self):
        """Initialize embedding models"""
        try:
            # Initialize sentence transformer for fast local embeddings
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding models initialized")
            
        except Exception as e:
            logger.error(f"Embedding model initialization failed: {e}")
            raise
    
    async def search(self, query: str, filters: Optional[Dict] = None, 
                    top_k: int = 5, include_metadata: bool = True) -> SearchResult:
        """Search vector store with freshness detection"""
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            
            # Prepare search filters
            search_filters = self._prepare_filters(filters)
            
            # Search Pinecone
            search_results = self.index.query(
                vector=query_embedding,
                filter=search_filters,
                top_k=top_k,
                include_metadata=include_metadata
            )
            
            # Process results
            vector_results = []
            total_score = 0
            
            for match in search_results.matches:
                metadata = match.metadata or {}
                
                # Parse last updated timestamp
                last_updated = None
                if 'last_updated' in metadata:
                    try:
                        last_updated = datetime.fromisoformat(metadata['last_updated'])
                    except (ValueError, TypeError):
                        pass
                
                result = VectorResult(
                    id=match.id,
                    score=match.score,
                    content=metadata.get('content', ''),
                    metadata=metadata,
                    source=metadata.get('source', 'unknown'),
                    last_updated=last_updated
                )
                
                vector_results.append(result)
                total_score += match.score
            
            # Calculate average confidence
            avg_confidence = total_score / len(vector_results) if vector_results else 0
            
            # Determine freshness
            is_fresh = self._check_freshness(vector_results)
            
            # Determine if web search is needed
            needs_web_search = (
                avg_confidence < settings.WEB_SEARCH_THRESHOLD_SCORE or
                not is_fresh or
                len(vector_results) == 0
            )
            
            logger.info(f"Vector search completed: {len(vector_results)} results, "
                       f"confidence: {avg_confidence:.3f}, fresh: {is_fresh}")
            
            return SearchResult(
                results=vector_results,
                is_fresh=is_fresh,
                confidence=avg_confidence,
                needs_web_search=needs_web_search,
                query_embedding=query_embedding
            )
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return SearchResult(
                results=[],
                is_fresh=False,
                confidence=0.0,
                needs_web_search=True,
                query_embedding=await self._get_embedding(query)
            )
    
    async def upsert_documents(self, documents: List[Dict]) -> bool:
        """Upsert documents to vector store"""
        try:
            vectors_to_upsert = []
            
            for doc in documents:
                # Generate embedding
                content = doc.get('content', '')
                embedding = await self._get_embedding(content)
                
                # Prepare metadata
                metadata = {
                    'content': content,
                    'source': doc.get('source', 'unknown'),
                    'content_type': doc.get('content_type', 'general'),
                    'last_updated': datetime.utcnow().isoformat(),
                    'campus': doc.get('campus', 'all'),
                    'department': doc.get('department', ''),
                    'course_code': doc.get('course_code', ''),
                    'academic_year': doc.get('academic_year', ''),
                    'language': doc.get('language', 'en')
                }
                
                vectors_to_upsert.append({
                    'id': doc.get('id', f"doc_{datetime.utcnow().timestamp()}"),
                    'values': embedding,
                    'metadata': metadata
                })
            
            # Upsert to Pinecone
            self.index.upsert(vectors=vectors_to_upsert)
            
            logger.info(f"Successfully upserted {len(vectors_to_upsert)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Document upsert failed: {e}")
            return False
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from vector store"""
        try:
            self.index.delete(ids=document_ids)
            logger.info(f"Successfully deleted {len(document_ids)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Document deletion failed: {e}")
            return False
    
    async def update_document(self, document_id: str, new_content: str, 
                            metadata: Optional[Dict] = None) -> bool:
        """Update a specific document"""
        try:
            # Generate new embedding
            embedding = await self._get_embedding(new_content)
            
            # Prepare updated metadata
            updated_metadata = metadata or {}
            updated_metadata.update({
                'content': new_content,
                'last_updated': datetime.utcnow().isoformat()
            })
            
            # Upsert the document
            self.index.upsert(vectors=[{
                'id': document_id,
                'values': embedding,
                'metadata': updated_metadata
            }])
            
            # Log the update
            await self._log_knowledge_update(
                content_id=document_id,
                new_content=new_content,
                source='manual_update',
                update_type='update'
            )
            
            logger.info(f"Successfully updated document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Document update failed: {e}")
            return False
    
    async def get_stats(self) -> Dict:
        """Get vector store statistics"""
        try:
            stats = self.index.describe_index_stats()
            
            return {
                'total_vectors': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'namespaces': stats.namespaces
            }
            
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {}
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI or local model"""
        try:
            # Use OpenAI for high-quality embeddings
            response = self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.warning(f"OpenAI embedding failed, using local model: {e}")
            
            # Fallback to local sentence transformer
            if self.sentence_transformer:
                return self.sentence_transformer.encode(text).tolist()
            
            raise Exception("No embedding model available")
    
    def _prepare_filters(self, filters: Optional[Dict]) -> Dict:
        """Prepare Pinecone filters"""
        if not filters:
            return {}
        
        pinecone_filters = {}
        
        # Map common filter fields
        field_mapping = {
            'source': 'source',
            'content_type': 'content_type',
            'campus': 'campus',
            'department': 'department',
            'course_code': 'course_code'
        }
        
        for key, value in filters.items():
            if key in field_mapping:
                pinecone_filters[field_mapping[key]] = value
        
        return pinecone_filters
    
    def _check_freshness(self, results: List[VectorResult]) -> bool:
        """Check if search results are fresh enough"""
        if not results:
            return False
        
        threshold_date = datetime.utcnow() - timedelta(days=settings.VECTOR_FRESHNESS_THRESHOLD_DAYS)
        
        # Check if majority of top results are fresh
        fresh_count = 0
        checked_count = min(3, len(results))  # Check top 3 results
        
        for result in results[:checked_count]:
            if result.last_updated and result.last_updated > threshold_date:
                fresh_count += 1
            elif not result.last_updated:
                # If no timestamp, assume old
                continue
        
        # Consider fresh if majority of top results are fresh
        return fresh_count >= (checked_count / 2)
    
    async def _log_knowledge_update(self, content_id: str, new_content: str, 
                                  source: str, update_type: str, 
                                  old_content: Optional[str] = None):
        """Log knowledge base updates"""
        try:
            async with AsyncSessionLocal() as session:
                update_log = KnowledgeUpdate(
                    source=source,
                    content_id=content_id,
                    update_type=update_type,
                    old_content=old_content,
                    new_content=new_content,
                    metadata={
                        'timestamp': datetime.utcnow().isoformat(),
                        'source': source
                    }
                )
                
                session.add(update_log)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log knowledge update: {e}")