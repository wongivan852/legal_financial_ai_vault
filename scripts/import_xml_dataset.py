#!/usr/bin/env python3
"""
Simplified XML Dataset Import Script
Wrapper around xml_ingestion.py for easy use on macOS.

Usage:
    python import_xml_dataset.py --zip-file ~/Downloads/download.zip
    python import_xml_dataset.py --xml-dir ~/Documents/legal_docs/
"""

import sys
import os
from pathlib import Path
import argparse
import subprocess
import asyncio

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def check_prerequisites():
    """Check if all prerequisites are met."""
    print_header("Checking Prerequisites")

    all_ok = True

    # Check Python version
    if sys.version_info >= (3, 11):
        print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} installed")
    else:
        print_error(f"Python 3.11+ required (found {sys.version_info.major}.{sys.version_info.minor})")
        all_ok = False

    # Check if Ollama is running
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print_success("Ollama service is running")
        else:
            print_error("Ollama service not responding correctly")
            all_ok = False
    except Exception:
        print_error("Ollama service not running")
        print_info("Start Ollama: ollama serve")
        all_ok = False

    # Check if database is accessible
    db_url = os.getenv("DATABASE_URL", "postgresql://legal_ai:password@localhost:5432/legal_ai_vault")
    print_info(f"Database: {db_url.split('@')[1] if '@' in db_url else 'not configured'}")

    # Check if Qdrant is running
    try:
        import httpx
        response = httpx.get("http://localhost:6333/", timeout=2)
        if response.status_code == 200:
            print_success("Qdrant vector database is running")
        else:
            print_warning("Qdrant may not be running properly")
    except Exception:
        print_warning("Qdrant vector database not accessible")
        print_info("Start services: docker-compose -f docker-compose.ollama.yml up -d")

    return all_ok


async def import_dataset(zip_file=None, xml_dir=None, user_email="admin@example.com"):
    """Import XML dataset into the system."""

    # Add the project root to Python path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sys.path.insert(0, str(project_root))

    print_header("Importing XML Dataset")

    # Import the ingestion module
    try:
        from api.database import SessionLocal
        from scripts.xml_ingestion import XMLDatasetIngestion
    except ImportError as e:
        print_error(f"Failed to import required modules: {e}")
        print_info("Make sure you're in the project root and dependencies are installed")
        print_info("Install: pip install -r api/requirements.txt")
        return False

    # Validate input
    if zip_file:
        zip_path = Path(zip_file).expanduser()
        if not zip_path.exists():
            print_error(f"ZIP file not found: {zip_path}")
            return False
        print_info(f"ZIP file: {zip_path}")
        print_info(f"Size: {zip_path.stat().st_size / 1024 / 1024:.2f} MB")
    elif xml_dir:
        xml_path = Path(xml_dir).expanduser()
        if not xml_path.exists():
            print_error(f"Directory not found: {xml_path}")
            return False
        xml_count = len(list(xml_path.rglob('*.xml')))
        print_info(f"XML directory: {xml_path}")
        print_info(f"XML files found: {xml_count}")
    else:
        print_error("Either --zip-file or --xml-dir must be specified")
        return False

    # Create database session
    db = SessionLocal()

    try:
        # Create ingestion instance
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

        print_info(f"Ollama URL: {ollama_url}")
        print_info(f"Qdrant URL: {qdrant_url}")
        print_info(f"User: {user_email}")
        print()

        ingestion = XMLDatasetIngestion(
            db=db,
            user_email=user_email,
            ollama_url=ollama_url,
            qdrant_url=qdrant_url
        )

        # Ingest data
        if zip_file:
            print_info("Extracting and processing ZIP file...")
            stats = await ingestion.ingest_zip_file(zip_path)
        else:
            print_info("Processing XML files...")
            xml_files = list(xml_path.rglob('*.xml'))
            stats = {
                'total_files': len(xml_files),
                'processed': 0,
                'failed': 0,
                'skipped': 0,
                'documents_created': []
            }

            for i, xml_file in enumerate(xml_files, 1):
                print(f"\rProcessing file {i}/{len(xml_files)}...", end='', flush=True)
                try:
                    doc_id = await ingestion.ingest_xml_file(xml_file)
                    if doc_id:
                        stats['processed'] += 1
                        stats['documents_created'].append(doc_id)
                    else:
                        stats['skipped'] += 1
                except Exception as e:
                    print_error(f"\nFailed to process {xml_file}: {e}")
                    stats['failed'] += 1
            print()  # New line after progress

        # Print results
        print_header("Import Results")
        print(f"Total files:      {stats['total_files']}")
        print(f"{Colors.OKGREEN}Processed:        {stats['processed']}{Colors.ENDC}")
        if stats['failed'] > 0:
            print(f"{Colors.FAIL}Failed:           {stats['failed']}{Colors.ENDC}")
        if stats['skipped'] > 0:
            print(f"{Colors.WARNING}Skipped:          {stats['skipped']}{Colors.ENDC}")
        print()

        if stats['documents_created']:
            print_success(f"Created {len(stats['documents_created'])} documents")
            if len(stats['documents_created']) <= 10:
                print("\nDocument IDs:")
                for doc_id in stats['documents_created']:
                    print(f"  - {doc_id}")

        print_header("Next Steps")
        print("1. View documents via API:")
        print("   curl http://localhost:8000/api/documents")
        print()
        print("2. Analyze a contract:")
        print("   curl -X POST http://localhost:8000/api/agents/contract-review \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"document_id\": \"<doc_id>\"}'")
        print()
        print("3. Access Swagger docs:")
        print("   http://localhost:8000/docs")
        print()

        return True

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Import XML legal documents into Legal AI Vault',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Import from ZIP file:
    python import_xml_dataset.py --zip-file ~/Downloads/download.zip

  Import from directory:
    python import_xml_dataset.py --xml-dir ~/Documents/legal_docs/

  Specify user:
    python import_xml_dataset.py --zip-file ~/Downloads/download.zip --user-email user@example.com
        """
    )

    parser.add_argument(
        '--zip-file',
        type=str,
        help='Path to ZIP file containing XML documents (e.g., ~/Downloads/download.zip)'
    )
    parser.add_argument(
        '--xml-dir',
        type=str,
        help='Path to directory containing XML files'
    )
    parser.add_argument(
        '--user-email',
        type=str,
        default='admin@example.com',
        help='Email of user to associate documents with (default: admin@example.com)'
    )
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Skip prerequisite checks'
    )

    args = parser.parse_args()

    if not args.zip_file and not args.xml_dir:
        parser.error('Either --zip-file or --xml-dir must be specified')

    # Check prerequisites
    if not args.skip_checks:
        if not check_prerequisites():
            print_warning("\nSome prerequisites are not met.")
            response = input("Continue anyway? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted.")
                return

    # Run import
    success = asyncio.run(import_dataset(
        zip_file=args.zip_file,
        xml_dir=args.xml_dir,
        user_email=args.user_email
    ))

    if success:
        print_success("\nImport completed successfully!")
        sys.exit(0)
    else:
        print_error("\nImport failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
