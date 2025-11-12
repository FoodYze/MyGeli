import json
from pathlib import Path

class SessionManager:
    """
    Gerencia a sessão do usuário (ID e Nome) em um arquivo JSON.
    """
    SESSION_FILE = Path(__file__).parent / "session.json"

    def save_session(self, user_id, first_name):
        """Salva o ID e o primeiro nome do usuário no arquivo de sessão."""
        try:
            data = {"user_id": user_id, "first_name": first_name}
            with open(self.SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            print(f"Log: Sessão salva. Data: {data}")
        except Exception as e:
            print(f"Log: Erro ao salvar sessão: {e}")

    def get_session(self):
        """Lê os dados da sessão do arquivo, se existir."""
        try:
            if not self.SESSION_FILE.exists():
                return {}  # Retorna dicionário vazio se não há sessão
            
            with open(self.SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Log: Sessão carregada. Data: {data}")
                return data
        except Exception as e:
            print(f"Log: Erro ao ler sessão: {e}")
            return {} # Retorna dicionário vazio em caso de erro

    def clear_session(self):
        """Limpa a sessão (logout)."""
        try:
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()
            print("Log: Sessão limpa (logout).")
        except Exception as e:
            print(f"Log: Erro ao limpar sessão: {e}")
