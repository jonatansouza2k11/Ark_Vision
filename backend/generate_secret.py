"""
generate_secret.py
Gera SECRET_KEY segura para .env
"""

import secrets
import string

def generate_secret_key(length: int = 64) -> str:
    """Gera chave segura"""
    alphabet = string.ascii_letters + string.digits + "_-"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    key = generate_secret_key()
    print("=" * 70)
    print("🔐 SUA SECRET_KEY:")
    print("=" * 70)
    print(key)
    print("=" * 70)
    print("\n✅ Copie e cole no .env.fastapi:")
    print(f"SECRET_KEY={key}")
    print("=" * 70)
