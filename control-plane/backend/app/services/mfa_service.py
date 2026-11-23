"""
Servicio Criptográfico de Multi-Factor Authentication (MFA) conforme a RFC 6238 (TOTP).
Genera secretos Base32, URIs otpauth para aplicaciones autenticadoras y códigos de recuperación.
"""
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from typing import List, Tuple
from urllib.parse import quote


class MFAService:
    @staticmethod
    def generate_totp_secret() -> str:
        """Genera un secreto aleatorio Base32 de 160 bits (20 bytes)."""
        random_bytes = os.urandom(20)
        return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")

    @staticmethod
    def get_provisioning_uri(secret: str, user_email: str, issuer: str = "SOFIA ERP") -> str:
        """
        Construye la URI estándar otpauth:// para escaneo en Google Authenticator,
        Microsoft Authenticator o Bitwarden.
        """
        label = f"{issuer}:{user_email}"
        return f"otpauth://totp/{quote(label, safe=':@')}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"

    @staticmethod
    def generate_totp_code(secret: str, for_time: int = None, interval: int = 30) -> str:
        """Calcula el código TOTP de 6 dígitos para un momento dado según RFC 6238."""
        if for_time is None:
            for_time = int(time.time())
        
        counter = int(for_time // interval)
        # Asegurar relleno Base32 para decodificación estándar
        padding = "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(secret.upper() + padding)
        
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        
        # Truncamiento dinámico según RFC 4226
        offset = h[-1] & 0x0F
        code_int = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        code_str = str(code_int % 1000000).zfill(6)
        return code_str

    @classmethod
    def verify_totp_code(cls, secret: str, code: str, window: int = 1) -> bool:
        """
        Valida el código TOTP ingresado admitiendo una ventana de tolerancia de ±1 paso (±30s)
        para mitigar desajustes leves de reloj entre cliente y servidor.
        """
        if not code or len(code.strip()) != 6 or not code.strip().isdigit():
            return False

        clean_code = code.strip()
        current_time = int(time.time())
        interval = 30

        for offset in range(-window, window + 1):
            check_time = current_time + (offset * interval)
            expected_code = cls.generate_totp_code(secret, for_time=check_time, interval=interval)
            # Comparación en tiempo constante para mitigar ataques de temporización
            if hmac.compare_digest(clean_code, expected_code):
                return True
        return False

    @staticmethod
    def generate_recovery_codes(count: int = 8) -> Tuple[List[str], List[str]]:
        """
        Genera un conjunto de códigos de recuperación únicos de un solo uso.
        Retorna (codigos_planos, hashes_sha256_para_almacenar).
        """
        plain_codes = []
        hashed_codes = []
        for _ in range(count):
            # Formato: xxxx-xxxx (8 caracteres alfanuméricos en dos bloques)
            part1 = secrets.token_hex(2).upper()
            part2 = secrets.token_hex(2).upper()
            code = f"{part1}-{part2}"
            plain_codes.append(code)
            
            # Almacenar únicamente el hash SHA-256 en base de datos
            code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
            hashed_codes.append(code_hash)
            
        return plain_codes, hashed_codes

    @staticmethod
    def verify_recovery_code(code: str, stored_hashes: List[str]) -> Tuple[bool, List[str]]:
        """
        Verifica si un código de recuperación es válido. Si coincide, lo remueve
        de la lista para garantizar que sea de un solo uso.
        """
        clean_code = code.strip().upper()
        incoming_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

        for idx, stored_hash in enumerate(stored_hashes):
            if hmac.compare_digest(incoming_hash, stored_hash):
                # Eliminar el código usado
                updated_hashes = stored_hashes[:idx] + stored_hashes[idx + 1:]
                return True, updated_hashes

        return False, stored_hashes
