"""
encrypted_fields.py
-------------------
Handles encryption/decryption (Fernet) and password hashing (bcrypt).

- Fernet symmetric encryption → used for: alerts.location, reports.content
- bcrypt one-way hashing      → used for: users.password
"""

import os
import bcrypt
from cryptography.fernet import Fernet

# Path to the persistent master key file
KEY_PATH = os.path.join(os.path.dirname(__file__), "../../data/database/master.key")


# =====================================================================
# MASTER KEY  (Fernet)
# =====================================================================

def _load_or_create_key() -> bytes:
    """
    Loads the Fernet master key from disk.
    Generates and saves a new key if the file does not exist.
    """
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            key = f.read()
        print("[encrypted_fields.py] Master key loaded.")
    else:
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        print("[encrypted_fields.py] New master key generated and saved.")
    return key


_FERNET = Fernet(_load_or_create_key())


# =====================================================================
# FERNET ENCRYPT / DECRYPT
# =====================================================================

def encrypt(value: str) -> str:
    """
    Encrypts a plaintext string using Fernet symmetric encryption.

    Args:
        value: The plaintext string to encrypt.

    Returns:
        URL-safe base64-encoded encrypted token as a string.
        Returns None if value is None.

    Example:
        encrypt("Cairo, Egypt") -> "gAAAAAB..."
    """
    if value is None:
        return None
    return _FERNET.encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """
    Decrypts a Fernet-encrypted token back to plaintext.

    Args:
        token: The encrypted token string.

    Returns:
        Original plaintext string.
        Returns None if token is None.

    Example:
        decrypt("gAAAAAB...") -> "Cairo, Egypt"
    """
    if token is None:
        return None
    return _FERNET.decrypt(token.encode()).decode()


# =====================================================================
# BCRYPT PASSWORD HASHING
# =====================================================================

def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt (one-way, cannot be reversed).

    Args:
        password: The plaintext password string.

    Returns:
        The bcrypt hash string to store in the database.

    Example:
        hash_password("securePass123") -> "$2b$12$..."
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.

    Args:
        password: The plaintext password to check.
        hashed:   The stored bcrypt hash from the database.

    Returns:
        True if the password matches, False otherwise.

    Example:
        check_password("securePass123", stored_hash) -> True
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())


# =====================================================================
# SELF-TEST
# =====================================================================
if __name__ == "__main__":
    # Test Fernet
    original  = "Cairo Military Zone - Sector 7"
    token     = encrypt(original)
    recovered = decrypt(token)
    print(f"Fernet — Original : {original}")
    print(f"Fernet — Encrypted: {token}")
    print(f"Fernet — Decrypted: {recovered}")
    print(f"Fernet — Match    : {original == recovered}")
    print()

    # Test bcrypt
    pw      = "securePass123"
    hashed  = hash_password(pw)
    matched = check_password(pw, hashed)
    print(f"bcrypt — Password : {pw}")
    print(f"bcrypt — Hash     : {hashed}")
    print(f"bcrypt — Match    : {matched}")
