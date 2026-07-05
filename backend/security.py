import os
import time
import jwt
from dotenv import load_dotenv

load_dotenv()

# Carrega a chave secreta e define o algoritmo
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

def create_session_token(spotify_token: str) -> str:
    # token expira em 1 hora
    expiration_time = int(time.time()) + 3600
    payload = {
        "spotify_token": spotify_token,
        "exp": expiration_time
    }
    token_gerado = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_gerado
    

def verify_session_token(token: str) -> str:
    try:
        decoded_payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        spotify_token = decoded_payload.get("spotify_token")
        return spotify_token
    except jwt.ExpiredSignatureError:
        print("Erro de Segurança: O token de sessão expirou.")
        return None
    except jwt.InvalidTokenError:
        # Lançado se alguém alterar o token ou a assinatura for inválida
        print("Erro de Segurança: Token inválido.")
        return None