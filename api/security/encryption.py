"""
Encryption Module - File and data encryption utilities
Uses Fernet (symmetric encryption) for document storage
"""

import base64
import hashlib
from pathlib import Path
from typing import Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import logging

from config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting files and strings"""

    def __init__(self):
        """Initialize encryption with key from settings"""
        # Derive a proper Fernet key from the encryption key in settings
        self.fernet = self._get_fernet_instance()

    def _get_fernet_instance(self) -> Fernet:
        """
        Create Fernet instance from settings encryption key

        The encryption key from settings is hashed to create a proper 32-byte key
        """
        # Use PBKDF2 to derive a proper key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'legal_ai_vault_salt',  # In production, use a unique salt per installation
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(
            kdf.derive(settings.ENCRYPTION_KEY.encode())
        )

        return Fernet(key)

    def encrypt_file(self, input_path: Union[str, Path], output_path: Union[str, Path]) -> bool:
        """
        Encrypt a file and save to output path

        Args:
            input_path: Path to file to encrypt
            output_path: Path where encrypted file will be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            # Read file content
            with open(input_path, 'rb') as f:
                file_data = f.read()

            # Encrypt data
            encrypted_data = self.fernet.encrypt(file_data)

            # Write encrypted data
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)

            logger.info(f"File encrypted successfully: {input_path} -> {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error encrypting file {input_path}: {e}")
            return False

    def decrypt_file(self, input_path: Union[str, Path], output_path: Union[str, Path]) -> bool:
        """
        Decrypt a file and save to output path

        Args:
            input_path: Path to encrypted file
            output_path: Path where decrypted file will be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            # Read encrypted file
            with open(input_path, 'rb') as f:
                encrypted_data = f.read()

            # Decrypt data
            decrypted_data = self.fernet.decrypt(encrypted_data)

            # Write decrypted data
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

            logger.info(f"File decrypted successfully: {input_path} -> {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error decrypting file {input_path}: {e}")
            return False

    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a string

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string

        Args:
            encrypted_text: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        decrypted_bytes = self.fernet.decrypt(encrypted_text.encode())
        return decrypted_bytes.decode()

    def read_encrypted_file(self, file_path: Union[str, Path]) -> bytes:
        """
        Read and decrypt a file directly to memory

        Args:
            file_path: Path to encrypted file

        Returns:
            Decrypted file content as bytes
        """
        file_path = Path(file_path)

        with open(file_path, 'rb') as f:
            encrypted_data = f.read()

        return self.fernet.decrypt(encrypted_data)

    def write_encrypted_file(self, file_path: Union[str, Path], data: bytes) -> bool:
        """
        Encrypt data and write to file

        Args:
            file_path: Path where encrypted file will be saved
            data: Data to encrypt and save

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(file_path)

            # Encrypt data
            encrypted_data = self.fernet.encrypt(data)

            # Write to file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)

            logger.info(f"Encrypted data written to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing encrypted file {file_path}: {e}")
            return False


def hash_string(text: str) -> str:
    """
    Create SHA-256 hash of a string (for audit logging)

    Args:
        text: String to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(text.encode()).hexdigest()


def hash_file(file_path: Union[str, Path]) -> str:
    """
    Create SHA-256 hash of a file

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


# Global encryption service instance
encryption_service = EncryptionService()
