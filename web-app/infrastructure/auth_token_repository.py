# Cole este código em infrastructure/auth_token_repository.py

import os
import hashlib
from datetime import datetime, timedelta

class RememberMeTokenRepository:
    def __init__(self, db_connection):
        self.db = db_connection

    def create_remember_token(self):
        selector = os.urandom(16).hex()
        authenticator = os.urandom(32).hex()
        hashed_authenticator = hashlib.sha256(authenticator.encode('utf-8')).hexdigest()
        return selector, authenticator, hashed_authenticator

    def save_remember_token(self, user_id, selector, hashed_authenticator, days_valid=30):
        expires = datetime.utcnow() + timedelta(days=days_valid)
        cnx = self.db.get_connection()
        cursor = cnx.cursor()
        try:
            # Primeiro, remove tokens antigos do mesmo usuário para evitar acúmulo
            cursor.execute("DELETE FROM login_tokens WHERE user_id = %s", (user_id,))
            
            # Insere o novo token
            query = """
                INSERT INTO login_tokens (user_id, selector, hashed_token, expires)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, selector, hashed_authenticator, expires))
            cnx.commit()
        except Exception as e:
            cnx.rollback()
            raise RuntimeError(f"Erro ao salvar token de 'lembrar-me': {e}")
        finally:
            cursor.close()
            cnx.close()