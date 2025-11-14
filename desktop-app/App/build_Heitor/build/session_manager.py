import json
from pathlib import Path
import os
import sys

class SessionManager:
    """
    Gerencia a sessão do usuário (ID e Nome) em um arquivo JSON
    localizado na pasta de dados do aplicativo do usuário (ex: %LOCALAPPDATA%).
    """

    def __init__(self):
        """
        Define o caminho do arquivo de sessão com base no sistema operacional.
        """
        APP_NAME = "MyGeli"

        # Tenta usar %LOCALAPPDATA% no Windows
        # (C:\Users\<user>\AppData\Local\MyGeli)
        local_app_data = os.getenv('LOCALAPPDATA')

        if local_app_data:
            self.data_dir = Path(local_app_data) / APP_NAME
        
        # Fallback para Mac/Linux (ou se %LOCALAPPDATA% falhar)
        # (home/<user>/.mygeli)
        else:
            self.data_dir = Path.home() / f".{APP_NAME.lower()}"

        # Cria o diretório se ele não existir
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Log CRÍTICO: Não foi possível criar o diretório de sessão: {e}")
            # Como último recurso, salva localmente (comportamento antigo)
            self.data_dir = Path(__file__).parent 

        # Define o caminho completo do arquivo de sessão
        self.SESSION_FILE = self.data_dir / "session.json"
        print(f"Log: Caminho da sessão definido para: {self.SESSION_FILE}")


    def save_session(self, user_id, first_name):
        """Salva o ID e o primeiro nome do usuário no arquivo de sessão."""
        try:
            data = {"user_id": user_id, "first_name": first_name}
            # Usa self.SESSION_FILE definido no __init__
            with open(self.SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            print(f"Log: Sessão salva. Data: {data}")
        except Exception as e:
            print(f"Log: Erro ao salvar sessão: {e}")

    def get_session(self):
        """Lê os dados da sessão do arquivo, se existir."""
        try:
            # Usa self.SESSION_FILE definido no __init__
            if not self.SESSION_FILE.exists():
                return {}  # Retorna dicionário vazio se não há sessão
            
            with open(self.SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Log: Sessão carregada. Data: {data}")
                return data
        except Exception as e:
            print(f"Log: Erro ao ler sessão: {e}")
            return {}

    def clear_session(self):
        """Limpa a sessão (logout)."""
        try:
            # Usa self.SESSION_FILE definido no __init__
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()
            print("Log: Sessão limpa (logout).")
        except Exception as e:
            print(f"Log: Erro ao limpar sessão: {e}")