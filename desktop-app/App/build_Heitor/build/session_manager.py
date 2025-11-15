import json
from pathlib import Path
import os

class SessionManager:
    """
    Gerencia a sessão persistente usando tokens locais.
    Salva em %LOCALAPPDATA% no Windows.
    """
    def __init__(self):
        APP_NAME = "MyGeli"
        # Define o caminho correto (%LOCALAPPDATA%)
        local_app_data = os.getenv('LOCALAPPDATA')
        if local_app_data:
            self.data_dir = Path(local_app_data) / APP_NAME
        else:
            self.data_dir = Path.home() / f".{APP_NAME.lower()}"
            
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Log CRÍTICO: Falha ao criar diretório de sessão: {e}")
            self.data_dir = Path(__file__).parent 

        self.SESSION_FILE = self.data_dir / "auth_token.json"

    def save_token(self, selector, authenticator):
        """Salva o par de tokens localmente (como um cookie)."""
        try:
            data = {"selector": selector, "authenticator": authenticator}
            with open(self.SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            print("Log: Token de persistência salvo localmente.")
        except Exception as e:
            print(f"Log: Erro ao salvar token local: {e}")

    def get_token(self):
        """Lê o token local, se existir."""
        try:
            if not self.SESSION_FILE.exists():
                return None
            with open(self.SESSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def clear_session(self):
        """Apaga o token local (Logout)."""
        try:
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()
            print("Log: Token local apagado (logout).")
        except Exception as e:
            print(f"Log: Erro ao limpar token local: {e}")
