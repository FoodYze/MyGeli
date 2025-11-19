import customtkinter as ctk
from pathlib import Path
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from tkinter import messagebox
from PIL import Image
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib

try:
    from session_manager import SessionManager
except ImportError:
    print("Erro: session_manager.py não encontrado.")
    SessionManager = None

load_dotenv()

db_host = os.getenv('DB_HOST', "localhost")
db_name = os.getenv('DB_NAME', "mygeli")
db_usuario = os.getenv('DB_USER', "foodyzeadm")
db_senha = os.getenv('DB_PASS', "supfood0017admx")

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets" / "geral"

class HistoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.connection = self.conectar_mysql()
        if not self.connection:
            self.destroy()
            return

        self.user_id = self.obter_usuario_logado()
        if not self.user_id:
            messagebox.showwarning("Erro de Sessão", "Não foi possível identificar o usuário. Faça login novamente.")
            self.destroy()
            return

        ctk.set_appearance_mode("light")
        self.title("Histórico de Uso")
        
        width, height = 400, 650
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(400, 650)
        self.configure(fg_color="#F5F5F5")

        # Fontes
        self.title_font = ctk.CTkFont("Poppins Bold", 22)
        self.header_font = ctk.CTkFont("Poppins Medium", 16)
        self.item_font = ctk.CTkFont("Poppins Regular", 13)
        self.date_font = ctk.CTkFont("Poppins Light", 11)

        self.create_widgets()
        self.load_history()

    def conectar_mysql(self):
        try:
            conexao = mysql.connector.connect(host=db_host, database=db_name, user=db_usuario, password=db_senha)
            if conexao.is_connected():
                return conexao
        except Error as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
            return None

    def obter_usuario_logado(self):
        """Lógica para pegar o ID do usuário pelo Token de Sessão"""
        if not SessionManager: return None
        manager = SessionManager()
        token_data = manager.get_token()
        if not token_data: return None

        selector = token_data.get("selector")
        authenticator = token_data.get("authenticator")
        
        try:
            if not self.connection.is_connected(): self.connection.reconnect()
            cursor = self.connection.cursor(dictionary=True)
            # Verifica o token no banco
            query = "SELECT user_id, hashed_token, expires FROM login_tokens WHERE selector = %s"
            cursor.execute(query, (selector,))
            record = cursor.fetchone()
            cursor.close()

            if record and record['expires'] >= datetime.now():
                hashed_auth_check = hashlib.sha256(authenticator.encode()).hexdigest()
                if hashed_auth_check == record['hashed_token']:
                    print(f"Log (Histórico): Usuário ID {record['user_id']} identificado.")
                    return record['user_id']
        except Error as e:
            print(f"Erro ao validar sessão: {e}")
        return None

    def go_to_inventory(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
        self.destroy()
        try:
            subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui3.py")])
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir gui3.py: {e}")

    def _format_display_quantity(self, quantidade, unidade):
        try:
            qtd_float = float(quantidade)
            unidade_base = unidade.capitalize()
            if unidade_base == 'Gramas' and qtd_float >= 1000:
                return ("{:g}".format(qtd_float / 1000).replace('.', ','), "Kg")
            if unidade_base == 'Mililitros' and qtd_float >= 1000:
                return ("{:g}".format(qtd_float / 1000).replace('.', ','), "L")
            return ("{:g}".format(qtd_float).replace('.', ','), unidade)
        except (ValueError, TypeError):
            return (str(quantidade), unidade)

    def clear_all_history(self):
        if messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja apagar TODO o SEU histórico de uso?", icon='warning'):
            try:
                if not self.connection.is_connected(): self.connection.reconnect()
                cursor = self.connection.cursor()
                
                cursor.execute("DELETE FROM historico_uso WHERE id_user = %s", (self.user_id,))
                
                self.connection.commit()
                cursor.close()
                messagebox.showinfo("Sucesso", "Seu histórico foi limpo.")
                self.load_history()
            except Error as e:
                messagebox.showerror("Erro BD", f"Falha ao limpar histórico: {e}")

    def create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0084FF")
        header_frame.grid(row=0, column=0, sticky="new")
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(1, weight=1)

        try:
            seta_path = ASSETS_PATH / "seta.png"
            pil_seta_img = Image.open(seta_path).resize((30, 30), Image.LANCZOS)
            seta_image = ctk.CTkImage(light_image=pil_seta_img, size=(30, 30))
            back_btn = ctk.CTkButton(header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.go_to_inventory)
            back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")
        except Exception:
            ctk.CTkButton(header_frame, text="<", width=40, command=self.go_to_inventory).grid(row=0, column=0, padx=10, pady=20, sticky="w")
        
        ctk.CTkLabel(header_frame, text="Histórico de Uso", font=self.title_font, text_color="white").grid(row=0, column=1, pady=20, sticky="nsew")

        try:
            lixeira_path = ASSETS_PATH / "lixeira.png"
            pil_lixeira_img = Image.open(lixeira_path).resize((28, 28), Image.LANCZOS)
            lixeira_image = ctk.CTkImage(light_image=pil_lixeira_img, size=(28, 28))
            clear_btn = ctk.CTkButton(header_frame, text="", image=lixeira_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.clear_all_history)
            clear_btn.grid(row=0, column=2, padx=10, pady=20, sticky="e")
        except Exception:
            ctk.CTkButton(header_frame, text="X", width=40, fg_color="#E74C3C", command=self.clear_all_history).grid(row=0, column=2, padx=10, pady=20, sticky="e")

        self.history_container = ctk.CTkScrollableFrame(self, fg_color="#F5F5F5", corner_radius=0)
        self.history_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.history_container.grid_columnconfigure(0, weight=1)
        
    def load_history(self):
        for widget in self.history_container.winfo_children():
            widget.destroy()
        try:
            if not self.connection.is_connected(): self.connection.reconnect()
            cursor = self.connection.cursor(dictionary=True)
            
            query = "SELECT * FROM historico_uso WHERE id_user = %s ORDER BY data_hora_uso DESC"
            cursor.execute(query, (self.user_id,))
            
            history_entries = cursor.fetchall()
            cursor.close()
            
            if not history_entries:
                ctk.CTkLabel(self.history_container, text="Seu histórico está vazio.", font=self.header_font, text_color="#666").pack(pady=30)
                return
            
            for entry in history_entries:
                self.add_history_entry_widget(entry)
        except Error as e:
            messagebox.showerror("Erro BD", f"Falha ao carregar histórico: {e}")

    def add_history_entry_widget(self, entry_data):
        entry_frame = ctk.CTkFrame(self.history_container, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#E0E0E0")
        entry_frame.grid(sticky="ew", pady=(0, 8))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        top_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,0))
        top_frame.grid_columnconfigure(0, weight=1)
        
        recipe_name = entry_data.get('nome_receita', 'Desconhecida')
        ctk.CTkLabel(top_frame, text=f"Receita: {recipe_name}", font=self.header_font, text_color="#0084FF", anchor="w").grid(row=0, column=0, sticky="w")
        
        data_uso = entry_data.get('data_hora_uso')
        date_str = data_uso.strftime('%d/%m/%Y %H:%M') if data_uso else "--/--/--"
        
        ctk.CTkLabel(top_frame, text=date_str, font=self.date_font, text_color="#666", anchor="e").grid(row=0, column=1, sticky="e")

        formatted_qtd, display_unit = self._format_display_quantity(entry_data['quantidade_usada'], entry_data['unidade_medida'])
        details_text = f"{entry_data['nome_ingrediente']}: {formatted_qtd} {display_unit}"
        ctk.CTkLabel(entry_frame, text=details_text, font=self.item_font, anchor="w").grid(row=1, column=0, sticky="ew", padx=10, pady=(0,10))

if __name__ == "__main__":
    app = HistoryApp()
    app.mainloop()
    if hasattr(app, 'connection') and app.connection and app.connection.is_connected():
        app.connection.close()
        print("Log: Conexão fechada.")