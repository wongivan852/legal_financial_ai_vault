"""
Hong Kong Legal Document XML Parser
Parses Hong Kong e-Legislation XML files (legislation chapters and instruments)
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

class HKLegalXMLParser:
    """Parser for Hong Kong e-Legislation XML documents"""

    # XML namespaces used in HK legal documents
    NAMESPACES = {
        'law': 'http://www.xml.gov.hk/schemas/hklm/1.0',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
        'xhtml': 'http://www.w3.org/1999/xhtml'
    }

    def __init__(self):
        self.namespaces = self.NAMESPACES

    def parse_document(self, xml_file_path: str) -> Dict:
        """
        Parse a Hong Kong legal XML document

        Args:
            xml_file_path: Path to the XML file

        Returns:
            Dict containing parsed document data
        """
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            # Extract metadata
            metadata = self._extract_metadata(root)

            # Extract document content
            content = self._extract_content(root)

            # Extract structure (chapters, sections, etc.)
            structure = self._extract_structure(root)

            return {
                'metadata': metadata,
                'content': content,
                'structure': structure,
                'source_file': xml_file_path,
                'parsed_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error parsing XML file {xml_file_path}: {e}")
            raise

    def _extract_metadata(self, root: ET.Element) -> Dict:
        """Extract metadata from the document"""

        meta = root.find('law:meta', self.namespaces)
        if meta is None:
            return {}

        metadata = {}

        # Document name and type
        doc_name = meta.find('law:docName', self.namespaces)
        if doc_name is not None:
            metadata['doc_name'] = doc_name.text

        doc_type = meta.find('law:docType', self.namespaces)
        if doc_type is not None:
            metadata['doc_type'] = doc_type.text

        doc_number = meta.find('law:docNumber', self.namespaces)
        if doc_number is not None:
            metadata['doc_number'] = doc_number.text

        doc_status = meta.find('law:docStatus', self.namespaces)
        if doc_status is not None:
            metadata['doc_status'] = doc_status.text

        # Dublin Core metadata
        identifier = meta.find('dc:identifier', self.namespaces)
        if identifier is not None:
            metadata['identifier'] = identifier.text

        date = meta.find('dc:date', self.namespaces)
        if date is not None:
            metadata['date'] = date.text

        subject = meta.find('dc:subject', self.namespaces)
        if subject is not None:
            metadata['subject'] = subject.text

        language = meta.find('dc:language', self.namespaces)
        if language is not None:
            metadata['language'] = language.text

        publisher = meta.find('dc:publisher', self.namespaces)
        if publisher is not None:
            metadata['publisher'] = publisher.text

        rights = meta.find('dc:rights', self.namespaces)
        if rights is not None:
            metadata['rights'] = rights.text

        return metadata

    def _extract_content(self, root: ET.Element) -> Dict:
        """Extract text content from the document"""

        main = root.find('law:main', self.namespaces)
        if main is None:
            return {'text': '', 'sections': []}

        # Extract long title
        long_title = main.find('.//law:longTitle', self.namespaces)
        title_text = self._extract_text(long_title) if long_title is not None else ''

        # Extract preamble if exists
        preamble = main.find('.//law:preamble', self.namespaces)
        preamble_text = self._extract_text(preamble) if preamble is not None else ''

        # Extract all content sections
        sections = []
        for section in main.findall('.//law:section', self.namespaces):
            section_data = self._extract_section(section)
            if section_data:
                sections.append(section_data)

        # Extract chapters
        chapters = []
        for chapter in main.findall('.//law:chapter', self.namespaces):
            chapter_data = self._extract_chapter(chapter)
            if chapter_data:
                chapters.append(chapter_data)

        # Get full text content
        full_text = self._extract_text(main)

        return {
            'title': title_text,
            'preamble': preamble_text,
            'sections': sections,
            'chapters': chapters,
            'full_text': full_text,
            'word_count': len(full_text.split())
        }

    def _extract_section(self, section: ET.Element) -> Dict:
        """Extract a section element"""

        section_id = section.get('id', '')
        section_num = section.find('.//law:num', self.namespaces)
        section_num_text = section_num.text if section_num is not None else ''

        heading = section.find('.//law:heading', self.namespaces)
        heading_text = self._extract_text(heading) if heading is not None else ''

        content = self._extract_text(section)

        # Extract subsections
        subsections = []
        for subsection in section.findall('.//law:subsection', self.namespaces):
            subsection_data = {
                'id': subsection.get('id', ''),
                'content': self._extract_text(subsection)
            }
            subsections.append(subsection_data)

        return {
            'id': section_id,
            'number': section_num_text,
            'heading': heading_text,
            'content': content,
            'subsections': subsections
        }

    def _extract_chapter(self, chapter: ET.Element) -> Dict:
        """Extract a chapter element"""

        chapter_id = chapter.get('id', '')

        heading = chapter.find('.//law:heading', self.namespaces)
        heading_text = self._extract_text(heading) if heading is not None else ''

        content = self._extract_text(chapter)

        # Extract sections within chapter
        sections = []
        for section in chapter.findall('.//law:section', self.namespaces):
            section_data = self._extract_section(section)
            if section_data:
                sections.append(section_data)

        return {
            'id': chapter_id,
            'heading': heading_text,
            'content': content,
            'sections': sections
        }

    def _extract_structure(self, root: ET.Element) -> List[Dict]:
        """Extract document structure (TOC)"""

        structure = []
        main = root.find('law:main', self.namespaces)
        if main is None:
            return structure

        # Look for table of contents
        toc_table = main.find('.//xhtml:table', self.namespaces)
        if toc_table is not None:
            for row in toc_table.findall('.//xhtml:tr', self.namespaces):
                cells = row.findall('.//xhtml:td', self.namespaces)
                if cells:
                    entry = {
                        'level': len(cells),
                        'text': ' '.join([self._extract_text(cell) for cell in cells])
                    }
                    structure.append(entry)

        return structure

    def _extract_text(self, element: Optional[ET.Element]) -> str:
        """
        Extract all text content from an element and its children
        Removes XML tags but preserves text structure
        """
        if element is None:
            return ''

        # Get all text including nested elements
        text_parts = []

        # Get element's own text
        if element.text:
            text_parts.append(element.text.strip())

        # Get text from all child elements recursively
        for child in element.iter():
            if child.text:
                text_parts.append(child.text.strip())
            if child.tail:
                text_parts.append(child.tail.strip())

        # Join and clean up
        full_text = ' '.join(text_parts)
        # Remove multiple spaces
        full_text = re.sub(r'\s+', ' ', full_text)

        return full_text.strip()

    def parse_batch(self, xml_files: List[str]) -> List[Dict]:
        """
        Parse multiple XML files

        Args:
            xml_files: List of paths to XML files

        Returns:
            List of parsed document dictionaries
        """
        results = []

        for xml_file in xml_files:
            try:
                parsed = self.parse_document(xml_file)
                results.append(parsed)
                logger.info(f"Successfully parsed: {xml_file}")
            except Exception as e:
                logger.error(f"Failed to parse {xml_file}: {e}")
                results.append({
                    'source_file': xml_file,
                    'error': str(e),
                    'parsed_at': datetime.utcnow().isoformat()
                })

        return results
