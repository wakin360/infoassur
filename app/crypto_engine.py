import base64
import os
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad

def generate_key() -> bytes:
    return os.urandom(32)

def encrypt_secret_answer(secret_text: str, key: bytes) -> tuple[str, str]:
    clean_bytes = secret_text.strip().lower().encode('utf-8')
    padded_bytes = pad(clean_bytes, AES.block_size)
    
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded_bytes)
    
    return (
        base64.b64encode(ciphertext).decode('utf-8'),
        base64.b64encode(iv).decode('utf-8')
    )

def decrypt_secret_answer(ciphertext_b64: str, iv_b64: str, key: bytes) -> str:
    ciphertext = base64.b64decode(ciphertext_b64)
    iv = base64.b64decode(iv_b64)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded = cipher.decrypt(ciphertext)
    unpadded_bytes = unpad(decrypted_padded, AES.block_size)
    
    return unpadded_bytes.decode('utf-8')

def verify_student_claim(user_input: str, ciphertext_b64: str, iv_b64: str, key: bytes) -> tuple[bool, str]:
    """
    FLEXIBLE VERIFICATION LOGIC:
    1. Decrypts the stored secret answer.
    2. Checks for exact match OR key word overlap.
    """
    try:
        decrypted_secret = decrypt_secret_answer(ciphertext_b64, iv_b64, key).lower()
        clean_user_input = user_input.strip().lower()
        
        # Exact match
        if clean_user_input == decrypted_secret:
            return True, decrypted_secret
            
        # Partial / Keyword Overlap match
        # Breaks secret into significant words (ignoring short words like 'a', 'in', 'on', 'the')
        stop_words = {'a', 'an', 'the', 'is', 'it', 'on', 'in', 'of', 'at', 'by', 'for', 'with', 'theres', 'there'}
        secret_words = [w for w in decrypted_secret.split() if w not in stop_words and len(w) > 2]
        user_words = set(clean_user_input.split())
        
        # If at least 60% of key secret words are found in student's attempt
        if secret_words:
            matched_words = [w for w in secret_words if w in user_words]
            match_score = len(matched_words) / len(secret_words)
            
            if match_score >= 0.5:  # 50% or higher word overlap match
                return True, decrypted_secret

        return False, decrypted_secret
    except Exception:
        return False, ""