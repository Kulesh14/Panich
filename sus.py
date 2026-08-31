import hashlib
from cryptography.fernet import Fernet
from config import ENC_KEY
from config import SALT

fernet = Fernet(ENC_KEY)

def get_id_hash(tg_id: int) -> str:
    salted = f"{tg_id}{SALT}"
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    return fernet.encrypt(value.encode('utf-8')).decode('utf-8')

def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    return fernet.decrypt(encrypted_value.encode('utf-8')).decode('utf-8')
