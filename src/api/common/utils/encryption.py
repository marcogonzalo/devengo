import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Get encryption key from environment or generate one
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(
        f"Warning: ENCRYPTION_KEY not found in environment. Generated new key: {ENCRYPTION_KEY}")
    print("Please add this key to your .env file to ensure data consistency.")

# Initialize Fernet cipher
cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(
    ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data

    Args:
        data: The string data to encrypt

    Returns:
        Encrypted string
    """
    if not data:
        return ""
    return cipher.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data

    Args:
        encrypted_data: The encrypted string to decrypt

    Returns:
        Decrypted string
    """
    if not encrypted_data:
        return ""
    return cipher.decrypt(encrypted_data.encode()).decode()
