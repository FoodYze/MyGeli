# Cole este código CORRETO em application/auth_service.py

from werkzeug.security import generate_password_hash, check_password_hash
from infrastructure.database_repository import AuthRepository
from infrastructure.auth_token_repository import RememberMeTokenRepository
from datetime import datetime, timedelta

class AuthService:
    def __init__(self, auth_repo: AuthRepository, token_repo: RememberMeTokenRepository):
        self.auth_repo = auth_repo
        self.token_repo = token_repo

    def register_user(self, name, phone, email, password, confirm_password):
        if password != confirm_password:
            raise ValueError("As senhas não coincidem.")
        if len(password) < 6:
            raise ValueError("A senha deve conter no mínimo 6 caracteres!")
        
        password_hash = generate_password_hash(password)
        try:
            user_id = self.auth_repo.insert_new_user(name, phone, email, password_hash)
            return user_id
        except Exception:
            raise ValueError("Já existe um usuário com esse e-mail.")
        
    def login_user(self, email, password):
        user = self.auth_repo.get_user_by_email(email)

        if not user or not check_password_hash(user['senha'], password):
            raise ValueError("E-mail ou senha inválidos.")
        
        return user['id']
    
    def create_and_save_remember_token(self, user_id):
        selector, authenticator, hashed_authenticator = self.token_repo.create_remember_token()
        self.token_repo.save_remember_token(user_id, selector, hashed_authenticator)
        return selector, authenticator