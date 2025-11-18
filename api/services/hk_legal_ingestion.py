"""
Hong Kong Legal Data Ingestion Service
Processes XML files and imports into database and vector store
"""

import os
import logging
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from parsers.hk_legal_xml_parser import HKLegalXMLParser
from models.hk_legal_document import HKLegalDocument, HKLegalSection
from services.vector_store import VectorStoreService
from services.embedding import EmbeddingService
from database import SessionLocal

logger = logging.getLogger(__name__)


class HKLegalIngestionService:
    """Service for ingesting Hong Kong legal documents"""

    def __init__(self):
        self.parser = HKLegalXMLParser()
        self.vector_store = VectorStoreService()
        self.embedding_service = EmbeddingService()
        self.collection_name = "hk_legislation"

    async def ingest_directory(self, directory_path: str) -> Dict:
        """
        Ingest all XML files from a directory

        Args:
            directory_path: Path to directory containing XML files

        Returns:
            Dict with ingestion statistics
        """
        logger.info(f"Starting ingestion from directory: {directory_path}")

        # Find all XML files
        xml_files = list(Path(directory_path).rglob("*.xml"))
        logger.info(f"Found {len(xml_files)} XML files")

        stats = {
            'total_files': len(xml_files),
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'documents_created': 0,
            'sections_created': 0,
            'vectors_created': 0,
            'errors': []
        }

        db = SessionLocal()
        try:
            for xml_file in xml_files:
                try:
                    result = await self.ingest_file(str(xml_file), db)

                    if result['status'] == 'success':
                        stats['processed'] += 1
                        stats['documents_created'] += result.get('documents', 0)
                        stats['sections_created'] += result.get('sections', 0)
                        stats['vectors_created'] += result.get('vectors', 0)
                    elif result['status'] == 'skipped':
                        stats['skipped'] += 1
                    else:
                        stats['failed'] += 1
                        stats['errors'].append({
                            'file': str(xml_file),
                            'error': result.get('error')
                        })

                except Exception as e:
                    logger.error(f"Error processing {xml_file}: {e}")
                    stats['failed'] += 1
                    stats['errors'].append({
                        'file': str(xml_file),
                        'error': str(e)
                    })

                # Commit every 10 files
                if stats['processed'] % 10 == 0:
                    db.commit()
                    logger.info(f"Progress: {stats['processed']}/{len(xml_files)} files processed")

            # Final commit
            db.commit()

        finally:
            db.close()

        logger.info(f"Ingestion complete: {stats}")
        return stats

    async def ingest_file(self, xml_file_path: str, db: Session) -> Dict:
        """
        Ingest a single XML file

        Args:
            xml_file_path: Path to XML file
            db: Database session

        Returns:
            Dict with processing result
        """
        logger.info(f"Processing file: {xml_file_path}")

        try:
            # Parse XML
            parsed_data = self.parser.parse_document(xml_file_path)

            metadata = parsed_data['metadata']
            content = parsed_data['content']
            structure = parsed_data['structure']

            # Check if already imported
            existing = db.query(HKLegalDocument).filter(
                HKLegalDocument.identifier == metadata.get('identifier')
            ).first()

            if existing:
                logger.info(f"Document already exists: {metadata.get('identifier')}")
                return {'status': 'skipped', 'reason': 'already_exists'}

            # Create document record
            doc = HKLegalDocument(
                doc_number=metadata.get('doc_number', ''),
                doc_name=metadata.get('doc_name', ''),
                doc_type=metadata.get('doc_type', ''),
                doc_status=metadata.get('doc_status', ''),
                identifier=metadata.get('identifier', ''),
                language=metadata.get('language', 'en'),
                subject=metadata.get('subject', ''),
                publisher=metadata.get('publisher', ''),
                rights=metadata.get('rights', ''),
                title=content.get('title', ''),
                preamble=content.get('preamble', ''),
                full_text=content.get('full_text', ''),
                word_count=content.get('word_count', 0),
                structure=structure,
                sections=content.get('sections', []),
                chapters=content.get('chapters', []),
                source_file=xml_file_path
            )

            # Parse effective date
            if metadata.get('date'):
                try:
                    doc.effective_date = datetime.strptime(metadata['date'], '%Y-%m-%d')
                except:
                    logger.warning(f"Could not parse date: {metadata['date']}")

            db.add(doc)
            db.flush()  # Get the ID

            # Create section records
            sections_created = 0
            for section_data in content.get('sections', []):
                section = HKLegalSection(
                    document_id=doc.id,
                    doc_number=doc.doc_number,
                    section_id=section_data.get('id', ''),
                    section_number=section_data.get('number', ''),
                    section_heading=section_data.get('heading', ''),
                    content=section_data.get('content', ''),
                    word_count=len(section_data.get('content', '').split()),
                    subsections=section_data.get('subsections', [])
                )
                db.add(section)
                sections_created += 1

            # Vectorize document
            vectors_created = await self._vectorize_document(doc, db)

            # Mark as processed
            doc.processed = True
            doc.vectorized = vectors_created > 0

            logger.info(f"Successfully imported: {doc.doc_number} ({doc.language})")

            return {
                'status': 'success',
                'document_id': doc.id,
                'documents': 1,
                'sections': sections_created,
                'vectors': vectors_created
            }

        except Exception as e:
            logger.error(f"Error ingesting file {xml_file_path}: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _vectorize_document(self, doc: HKLegalDocument, db: Session) -> int:
        """
        Create vector embeddings for document

        Args:
            doc: HKLegalDocument instance
            db: Database session

        Returns:
            Number of vectors created
        """
        try:
            # Initialize collection if it doesn't exist
            await self.vector_store.create_collection(
                collection_name=self.collection_name,
                dimension=1024  # bge-large-en-v1.5 dimension
            )

            # Chunk document if too long
            chunks = self._chunk_text(doc.full_text, max_chunk_size=500)

            vector_ids = []

            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = await self.embedding_service.embed(chunk)

                # Store in vector database
                point_id = f"{doc.id}_chunk_{i}"

                await self.vector_store.upsert_point(
                    collection_name=self.collection_name,
                    point_id=point_id,
                    vector=embedding,
                    payload={
                        'document_id': doc.id,
                        'doc_number': doc.doc_number,
                        'doc_name': doc.doc_name,
                        'doc_type': doc.doc_type,
                        'language': doc.language,
                        'title': doc.title,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'text': chunk[:500],  # Store first 500 chars
                        'effective_date': doc.effective_date.isoformat() if doc.effective_date else None
                    }
                )

                vector_ids.append(point_id)

            # Update document with vector IDs
            doc.vector_collection = self.collection_name
            doc.vector_ids = vector_ids

            logger.info(f"Created {len(vector_ids)} vectors for document {doc.doc_number}")
            return len(vector_ids)

        except Exception as e:
            logger.error(f"Error vectorizing document {doc.id}: {e}")
            return 0

    def _chunk_text(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """
        Split text into chunks by words

        Args:
            text: Text to chunk
            max_chunk_size: Maximum words per chunk

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), max_chunk_size):
            chunk = ' '.join(words[i:i + max_chunk_size])
            chunks.append(chunk)

        return chunks if chunks else [text]

    async def search_documents(
        self,
        query: str,
        language: str = 'en',
        limit: int = 10
    ) -> List[Dict]:
        """
        Search HK legal documents using vector similarity

        Args:
            query: Search query
            language: Document language filter
            limit: Maximum results

        Returns:
            List of matching documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed(query)

            # Search vector store
            results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                filter={
                    'must': [
                        {'key': 'language', 'match': {'value': language}}
                    ]
                }
            )

            return results

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
