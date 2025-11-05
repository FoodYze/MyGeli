# Salve este arquivo como session_manager.py
import json
from pathlib import Path

# O 'app' do CustomTkinter não é um servidor, então o 'app.secret_key' não é necessário.
# O 'DatabaseRepository' parece ser de outro projeto, vamos focar no essencial.

class SessionManager:
    """
    Gerencia a sessão do usuário em um arquivo JSON.
    Isso permite que diferentes scripts GUI (processos) compartilhem o estado de login.
    """
    SESSION_FILE = Path(__file__).parent / "session.json"

    def __init__(self):
        pass

    def save_session(self, user_id):
        """Salva o ID do usuário no arquivo de sessão."""
        try:
            with open(self.SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump({"user_id": user_id}, f)
            print(f"Log: Sessão salva. UserID: {user_id}")
        except Exception as e:
            print(f"Log: Erro ao salvar sessão: {e}")

    def get_session(self):
        """Lê o ID do usuário do arquivo de sessão, se existir."""
        try:
            if not self.SESSION_FILE.exists():
                return None
            
            with open(self.SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_id = data.get("user_id")
                print(f"Log: Sessão carregada. UserID: {user_id}")
                return user_id
        except Exception as e:
            print(f"Log: Erro ao ler sessão: {e}")
            return None

    def clear_session(self):
        """Limpa a sessão (logout)."""
        try:
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()
            print("Log: Sessão limpa (logout).")
        except Exception as e:
            print(f"Log: Erro ao limpar sessão: {e}")