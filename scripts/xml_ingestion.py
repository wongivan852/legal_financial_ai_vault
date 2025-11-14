#!/usr/bin/env python3
"""
XML Dataset Ingestion Script
Processes legal/financial XML documents and imports them into the AI Vault.

This script:
1. Extracts XML files from zip archives
2. Parses XML structure and extracts legal content
3. Creates document records in database
4. Generates embeddings for RAG
5. Stores vectors in Qdrant

Usage:
    python xml_ingestion.py --zip-file /path/to/download.zip --user-email admin@example.com
    python xml_ingestion.py --xml-dir /path/to/xml_files/ --user-email admin@example.com
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
import logging
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from api.database import SessionLocal, engine
from api.models.user import User
from api.models.document import Document
from api.services.vector_store import VectorStoreService
from api.services.ollama_client import OllamaInferenceService
from api.security.encryption import EncryptionService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XMLDocumentParser:
    """Parser for legal/financial XML documents."""

    # Common XML namespaces for legal documents
    NAMESPACES = {
        'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
    }

    def __init__(self):
        self.supported_formats = ['.xml', '.akn', '.xhtml']

    def parse_xml_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse XML file and extract structured content.

        Args:
            file_path: Path to XML file

        Returns:
            Dict with extracted metadata and content
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Try different parsing strategies
            result = None

            # Strategy 1: Akoma Ntoso (legal document standard)
            if self._is_akoma_ntoso(root):
                result = self._parse_akoma_ntoso(root)

            # Strategy 2: Generic legal XML
            elif self._is_legal_xml(root):
                result = self._parse_legal_xml(root)

            # Strategy 3: Generic XML with text extraction
            else:
                result = self._parse_generic_xml(root)

            if result:
                result['file_name'] = file_path.name
                result['file_path'] = str(file_path)
                result['file_size'] = file_path.stat().st_size

            return result

        except ET.ParseError as e:
            logger.error(f"XML parsing error for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

    def _is_akoma_ntoso(self, root: ET.Element) -> bool:
        """Check if document is Akoma Ntoso format."""
        return 'akn' in root.tag.lower() or any(
            ns in root.tag for ns in self.NAMESPACES.values()
        )

    def _is_legal_xml(self, root: ET.Element) -> bool:
        """Check if document appears to be legal XML."""
        legal_tags = ['contract', 'agreement', 'statute', 'regulation', 'case', 'judgment']
        return any(tag in root.tag.lower() for tag in legal_tags)

    def _parse_akoma_ntoso(self, root: ET.Element) -> Dict[str, Any]:
        """Parse Akoma Ntoso legal document."""
        result = {
            'format': 'akoma_ntoso',
            'title': '',
            'content': '',
            'metadata': {},
            'sections': []
        }

        # Extract metadata
        meta = root.find('.//akn:meta', self.NAMESPACES)
        if meta is not None:
            result['metadata'] = self._extract_metadata(meta)

        # Extract title
        title_elem = root.find('.//akn:title', self.NAMESPACES)
        if title_elem is not None:
            result['title'] = title_elem.text or ''

        # Extract body content
        body = root.find('.//akn:body', self.NAMESPACES)
        if body is not None:
            result['content'] = self._extract_text(body)
            result['sections'] = self._extract_sections(body)

        return result

    def _parse_legal_xml(self, root: ET.Element) -> Dict[str, Any]:
        """Parse generic legal XML document."""
        result = {
            'format': 'legal_xml',
            'title': '',
            'content': '',
            'metadata': {},
            'sections': []
        }

        # Try to find title
        for title_tag in ['title', 'name', 'heading']:
            title_elem = root.find(f'.//{title_tag}')
            if title_elem is not None:
                result['title'] = title_elem.text or ''
                break

        # Extract all text content
        result['content'] = self._extract_text(root)

        # Try to extract sections
        for section_tag in ['section', 'article', 'clause', 'paragraph']:
            sections = root.findall(f'.//{section_tag}')
            if sections:
                result['sections'] = [
                    {
                        'type': section_tag,
                        'content': self._extract_text(sec),
                        'attributes': sec.attrib
                    }
                    for sec in sections
                ]
                break

        return result

    def _parse_generic_xml(self, root: ET.Element) -> Dict[str, Any]:
        """Parse generic XML and extract all text."""
        return {
            'format': 'generic_xml',
            'title': root.tag,
            'content': self._extract_text(root),
            'metadata': root.attrib,
            'sections': []
        }

    def _extract_metadata(self, meta_elem: ET.Element) -> Dict[str, str]:
        """Extract metadata from meta element."""
        metadata = {}
        for child in meta_elem:
            tag = child.tag.split('}')[-1]  # Remove namespace
            if child.text:
                metadata[tag] = child.text
            if child.attrib:
                metadata[f"{tag}_attrs"] = child.attrib
        return metadata

    def _extract_text(self, elem: ET.Element) -> str:
        """Recursively extract all text from element."""
        text_parts = []

        if elem.text:
            text_parts.append(elem.text.strip())

        for child in elem:
            text_parts.append(self._extract_text(child))
            if child.tail:
                text_parts.append(child.tail.strip())

        return ' '.join(filter(None, text_parts))

    def _extract_sections(self, body_elem: ET.Element) -> List[Dict[str, str]]:
        """Extract structured sections from body."""
        sections = []
        for section_tag in ['section', 'article', 'chapter', 'part']:
            section_elems = body_elem.findall(f'.//{section_tag}', self.NAMESPACES)
            if section_elems:
                for sec in section_elems:
                    sections.append({
                        'type': section_tag,
                        'heading': self._get_section_heading(sec),
                        'content': self._extract_text(sec)
                    })
        return sections

    def _get_section_heading(self, section_elem: ET.Element) -> str:
        """Get section heading/title."""
        for heading_tag in ['heading', 'title', 'num']:
            heading = section_elem.find(f'.//{heading_tag}', self.NAMESPACES)
            if heading is not None and heading.text:
                return heading.text
        return ''


class XMLDatasetIngestion:
    """Main ingestion orchestrator."""

    def __init__(
        self,
        db: Session,
        user_email: str,
        ollama_url: str = "http://localhost:11434",
        qdrant_url: str = "http://localhost:6333"
    ):
        self.db = db
        self.user = self._get_user(user_email)
        self.parser = XMLDocumentParser()
        self.encryption_service = EncryptionService()
        self.vector_store = VectorStoreService(qdrant_url)
        self.ollama_service = OllamaInferenceService(ollama_url)
        self.storage_base = Path("/data/documents")
        self.storage_base.mkdir(parents=True, exist_ok=True)

    def _get_user(self, email: str) -> User:
        """Get user by email."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError(f"User with email {email} not found")
        return user

    async def ingest_zip_file(self, zip_path: Path) -> Dict[str, Any]:
        """
        Extract and ingest all XML files from zip archive.

        Args:
            zip_path: Path to zip file

        Returns:
            Dict with ingestion statistics
        """
        logger.info(f"Extracting ZIP file: {zip_path}")

        # Extract to temporary directory
        extract_dir = zip_path.parent / f"extracted_{zip_path.stem}"
        extract_dir.mkdir(exist_ok=True)

        stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'documents_created': []
        }

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find all XML files
            xml_files = list(extract_dir.rglob('*.xml'))
            xml_files.extend(extract_dir.rglob('*.akn'))
            xml_files.extend(extract_dir.rglob('*.xhtml'))

            stats['total_files'] = len(xml_files)
            logger.info(f"Found {len(xml_files)} XML files")

            # Process each XML file
            for xml_file in xml_files:
                try:
                    doc_id = await self.ingest_xml_file(xml_file)
                    if doc_id:
                        stats['processed'] += 1
                        stats['documents_created'].append(doc_id)
                    else:
                        stats['skipped'] += 1
                except Exception as e:
                    logger.error(f"Failed to ingest {xml_file}: {e}")
                    stats['failed'] += 1

            return stats

        finally:
            # Cleanup extracted files
            import shutil
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

    async def ingest_xml_file(self, xml_path: Path) -> Optional[str]:
        """
        Ingest single XML file into the system.

        Args:
            xml_path: Path to XML file

        Returns:
            Document ID if successful, None otherwise
        """
        logger.info(f"Processing XML file: {xml_path}")

        # Parse XML
        parsed_data = self.parser.parse_xml_file(xml_path)
        if not parsed_data:
            logger.warning(f"Could not parse {xml_path}")
            return None

        # Create document title
        title = parsed_data.get('title', '') or xml_path.stem
        content = parsed_data['content']

        if not content:
            logger.warning(f"No content extracted from {xml_path}")
            return None

        # Save original file
        storage_path = self.storage_base / self.user.id / xml_path.name
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy and encrypt
        import shutil
        temp_copy = storage_path.with_suffix('.tmp')
        shutil.copy2(xml_path, temp_copy)

        encrypted_path = storage_path.with_suffix(storage_path.suffix + '.enc')
        self.encryption_service.encrypt_file(temp_copy, encrypted_path)
        temp_copy.unlink()

        # Create document record
        document = Document(
            user_id=self.user.id,
            title=title,
            file_type='xml',
            file_name=xml_path.name,
            storage_path=str(encrypted_path),
            original_size=xml_path.stat().st_size,
            encrypted=True,
            processed=True,
            text_extracted=True,
            metadata=json.dumps({
                'format': parsed_data.get('format'),
                'xml_metadata': parsed_data.get('metadata', {}),
                'section_count': len(parsed_data.get('sections', []))
            })
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        logger.info(f"Created document: {document.id} - {title}")

        # Generate embeddings and store in Qdrant
        try:
            await self._vectorize_document(document, content, parsed_data.get('sections', []))
        except Exception as e:
            logger.error(f"Failed to vectorize document {document.id}: {e}")

        return document.id

    async def _vectorize_document(
        self,
        document: Document,
        full_content: str,
        sections: List[Dict[str, str]]
    ):
        """Generate embeddings and store in vector database."""
        logger.info(f"Vectorizing document: {document.id}")

        collection_name = "legal_documents"

        # Ensure collection exists
        try:
            self.vector_store.create_collection(
                collection_name=collection_name,
                vector_size=768,  # nomic-embed-text dimension
                distance="Cosine"
            )
        except:
            pass  # Collection may already exist

        # Chunk content for embedding
        chunks = self._chunk_content(full_content, sections)

        points = []
        for idx, chunk in enumerate(chunks):
            # Generate embedding
            embedding = await self.ollama_service.generate_embedding(chunk['text'])

            points.append({
                "id": f"{document.id}_{idx}",
                "vector": embedding,
                "payload": {
                    "document_id": document.id,
                    "chunk_index": idx,
                    "text": chunk['text'],
                    "type": chunk.get('type', 'content'),
                    "heading": chunk.get('heading', '')
                }
            })

        # Batch insert
        if points:
            self.vector_store.upsert_batch(collection_name, points)
            document.vectorized = True
            document.vector_collection = collection_name
            self.db.commit()

            logger.info(f"Stored {len(points)} vectors for document {document.id}")

    def _chunk_content(
        self,
        content: str,
        sections: List[Dict[str, str]],
        chunk_size: int = 1000
    ) -> List[Dict[str, str]]:
        """Chunk content for embedding."""
        chunks = []

        # If we have sections, use them
        if sections:
            for section in sections:
                section_text = section.get('content', '')
                if len(section_text) > chunk_size:
                    # Split large sections
                    for i in range(0, len(section_text), chunk_size):
                        chunks.append({
                            'text': section_text[i:i+chunk_size],
                            'type': section.get('type', 'section'),
                            'heading': section.get('heading', '')
                        })
                else:
                    chunks.append({
                        'text': section_text,
                        'type': section.get('type', 'section'),
                        'heading': section.get('heading', '')
                    })
        else:
            # No sections, chunk the full content
            for i in range(0, len(content), chunk_size):
                chunks.append({
                    'text': content[i:i+chunk_size],
                    'type': 'content',
                    'heading': ''
                })

        return chunks


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Ingest XML legal documents')
    parser.add_argument('--zip-file', type=str, help='Path to ZIP file containing XML documents')
    parser.add_argument('--xml-dir', type=str, help='Path to directory containing XML files')
    parser.add_argument('--user-email', type=str, required=True, help='Email of user to associate documents with')
    parser.add_argument('--ollama-url', type=str, default='http://localhost:11434', help='Ollama API URL')
    parser.add_argument('--qdrant-url', type=str, default='http://localhost:6333', help='Qdrant URL')

    args = parser.parse_args()

    if not args.zip_file and not args.xml_dir:
        parser.error('Either --zip-file or --xml-dir must be specified')

    # Create database session
    db = SessionLocal()

    try:
        ingestion = XMLDatasetIngestion(
            db=db,
            user_email=args.user_email,
            ollama_url=args.ollama_url,
            qdrant_url=args.qdrant_url
        )

        if args.zip_file:
            zip_path = Path(args.zip_file)
            if not zip_path.exists():
                logger.error(f"ZIP file not found: {zip_path}")
                return

            stats = await ingestion.ingest_zip_file(zip_path)
            logger.info(f"\nIngestion complete!")
            logger.info(f"Total files: {stats['total_files']}")
            logger.info(f"Processed: {stats['processed']}")
            logger.info(f"Failed: {stats['failed']}")
            logger.info(f"Skipped: {stats['skipped']}")

        elif args.xml_dir:
            xml_dir = Path(args.xml_dir)
            if not xml_dir.exists():
                logger.error(f"Directory not found: {xml_dir}")
                return

            xml_files = list(xml_dir.rglob('*.xml'))
            logger.info(f"Found {len(xml_files)} XML files")

            for xml_file in xml_files:
                await ingestion.ingest_xml_file(xml_file)

    finally:
        db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
