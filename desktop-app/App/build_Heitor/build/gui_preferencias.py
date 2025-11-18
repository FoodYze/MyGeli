import customtkinter as ctk
from tkinter import messagebox
import mysql.connector
from mysql.connector import Error
import subprocess
import sys
from pathlib import Path
import re
import os
from dotenv import load_dotenv
import hashlib
from datetime import datetime

from session_manager import SessionManager

load_dotenv()

# --- CREDENCIAIS DO BANCO (Carregadas do .env) ---
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_usuario = os.getenv('DB_USER')
db_senha = os.getenv('DB_PASS')

# --- CAMINHOS ---
OUTPUT_PATH = Path(__file__).parent

def conectar_mysql(host, database, user, password):
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            print("Log: Conexão ao MySQL bem-sucedida para a página de preferências!")
            return conexao
    except Error as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
        return None

class PreferencesApp(ctk.CTk):
    def __init__(self, conexao_bd):
        super().__init__()
        
        ctk.set_appearance_mode("light")

        self.conexao = conexao_bd
        self.session_manager = SessionManager()
        self.user_id = None

        if not self._validar_sessao():
            messagebox.showerror("Erro de Sessão", "Sessão inválida ou expirada. Por favor, faça login novamente.")
            self.after(100, self.destroy)
            return
        
        # --- Configuração da Janela ---
        self.title("Meu Perfil e Preferências | MyGeli")
        window_width = 600
        window_height = 650
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.minsize(500, 600)
        
        # --- Constantes de UI ---
        self.NORMAL_TEXT_COLOR = "#000000"
        self.PLACEHOLDER_COLOR = "gray65"
        
        # --- Fontes ---
        self.title_font = ctk.CTkFont(family="Helvetica", size=24, weight="bold")
        self.label_font = ctk.CTkFont(family="Helvetica", size=14, weight="bold")
        self.text_font = ctk.CTkFont(family="Helvetica", size=14)

        # --- Layout Principal ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#007AFF")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.back_btn = ctk.CTkButton(self.header_frame, text="← Voltar", width=80, fg_color="transparent", hover_color="#0066CC", font=("Helvetica", 16, "bold"), text_color="white", command=self.voltar)
        self.back_btn.pack(side="left", padx=10, pady=10)

        # Frame Principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(self.main_frame, text="Perfil de Usuário", font=self.title_font, text_color=self.NORMAL_TEXT_COLOR)
        title_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        
        # Abas
        self.tab_view = ctk.CTkTabview(self.main_frame)
        self.tab_view.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.tab_view.add("Perfil"); self.tab_view.add("Preferências")
        self.tab_view._segmented_button.grid(sticky="ew")
        self.tab_view.tab("Perfil").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Preferências").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Preferências").grid_rowconfigure(0, weight=1)

        # --- Widgets da Aba "Perfil" ---
        ctk.CTkLabel(self.tab_view.tab("Perfil"), text="Nome:", font=self.label_font, text_color=self.NORMAL_TEXT_COLOR).pack(anchor="w", padx=10, pady=(10,0))
        self.name_entry = ctk.CTkEntry(self.tab_view.tab("Perfil"), font=self.text_font, state="disabled")
        self.name_entry.pack(fill="x", pady=(2, 15), padx=10)
        ctk.CTkLabel(self.tab_view.tab("Perfil"), text="Email:", font=self.label_font, text_color=self.NORMAL_TEXT_COLOR).pack(anchor="w", padx=10)
        self.email_entry = ctk.CTkEntry(self.tab_view.tab("Perfil"), font=self.text_font, state="disabled")
        self.email_entry.pack(fill="x", pady=(2, 15), padx=10)

        # --- Frame Rolável para as Preferências ---
        preferences_scroll_frame = ctk.CTkScrollableFrame(self.tab_view.tab("Preferências"), fg_color="transparent")
        preferences_scroll_frame.grid(row=0, column=0, sticky="nsew")
        preferences_scroll_frame.grid_columnconfigure(0, weight=1)

        # Widgets dentro do frame rolável
        ctk.CTkLabel(preferences_scroll_frame, text="Alergias", font=self.label_font, text_color=self.NORMAL_TEXT_COLOR).pack(anchor="w", padx=10, pady=(10,0))
        self.allergies_textbox = ctk.CTkTextbox(preferences_scroll_frame, height=100, font=self.text_font, wrap="word")
        self.allergies_textbox.pack(fill="x", pady=(2, 15), padx=10, expand=True)

        ctk.CTkLabel(preferences_scroll_frame, text="Restrições Alimentares", font=self.label_font, text_color=self.NORMAL_TEXT_COLOR).pack(anchor="w", padx=10)
        self.restrictions_textbox = ctk.CTkTextbox(preferences_scroll_frame, height=100, font=self.text_font, wrap="word")
        self.restrictions_textbox.pack(fill="x", pady=(2, 15), padx=10, expand=True)

        ctk.CTkLabel(preferences_scroll_frame, text="Outras Preferências", font=self.label_font, text_color=self.NORMAL_TEXT_COLOR).pack(anchor="w", padx=10)
        self.other_textbox = ctk.CTkTextbox(preferences_scroll_frame, height=100, font=self.text_font, wrap="word")
        self.other_textbox.pack(fill="x", pady=(2, 15), padx=10, expand=True)
        
        # --- Dicionário de placeholders e configuração ---
        self.placeholders = {
            self.allergies_textbox: "Ex: Glúten, lactose, amendoim...",
            self.restrictions_textbox: "Ex: Vegetariano, vegano, baixo carboidrato...",
            self.other_textbox: "Ex: Prefiro comidas apimentadas, não gosto de coentro..."
        }
        for widget, text in self.placeholders.items():
            self._setup_placeholder(widget, text)

        # Botão Salvar
        self.save_button = ctk.CTkButton(self, text="Salvar Preferências", height=40, font=("Helvetica", 16, "bold"), command=self.save_preferences)
        self.save_button.grid(row=2, column=0, padx=30, pady=20, sticky="ew")

        # Carregar dados
        self.load_user_data()

    # --- CORREÇÃO: Lógica de Placeholder Refinada ---
    def _setup_placeholder(self, widget, text):
        """Associa os eventos de foco para simular um placeholder em um CTkTextbox."""
        def on_focus_in(event):
            # Se o texto atual for o placeholder (identificado pela cor)
            if widget.cget("text_color") == self.PLACEHOLDER_COLOR:
                widget.delete("1.0", "end")
                widget.configure(text_color=self.NORMAL_TEXT_COLOR)

        def on_focus_out(event):
            # Se o widget estiver vazio após o usuário sair
            if not widget.get("1.0", "end-1c").strip():
                widget.delete("1.0", "end") # Garante que está limpo
                widget.insert("1.0", text)
                widget.configure(text_color=self.PLACEHOLDER_COLOR)

        widget.bind("<FocusIn>", on_focus_in)
        widget.bind("<FocusOut>", on_focus_out)
        
    def _validar_sessao(self):
        token_data = self.session_manager.get_token()
        if not token_data: return False
        selector, authenticator = token_data.get("selector"), token_data.get("authenticator")
        if not selector or not authenticator: return False
        try:
            if not self.conexao or not self.conexao.is_connected():
                 self.conexao = conectar_mysql(db_host, db_name, db_usuario, db_senha)
                 if not self.conexao: return False
            cursor = self.conexao.cursor(dictionary=True)
            query = """SELECT t.user_id, t.hashed_token, t.expires, u.nome 
                       FROM login_tokens t JOIN usuarios u ON t.user_id = u.id WHERE t.selector = %s"""
            cursor.execute(query, (selector,))
            record = cursor.fetchone()
            cursor.close()
            if not record or record['expires'] < datetime.now(): return False
            if hashlib.sha256(authenticator.encode()).hexdigest() == record['hashed_token']:
                self.user_id = record['user_id']
                return True
            return False
        except Error as e:
            print(f"Log (Preferências): Erro ao validar sessão: {e}")
            return False

    def load_user_data(self):
        try:
            cursor = self.conexao.cursor(dictionary=True)
            cursor.execute("SELECT nome, email, preferencias FROM usuarios WHERE id = %s", (self.user_id,))
            user_data = cursor.fetchone()
            cursor.close()

            if user_data:
                self.name_entry.configure(state="normal"); self.name_entry.insert(0, user_data.get('nome', '')); self.name_entry.configure(state="disabled")
                self.email_entry.configure(state="normal"); self.email_entry.insert(0, user_data.get('email', '')); self.email_entry.configure(state="disabled")
                self.parse_and_display_preferences(user_data.get('preferencias'))
        except Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao carregar dados: {e}")

    # --- CORREÇÃO: Carregamento de Dados que Respeita o Placeholder ---
    def parse_and_display_preferences(self, prefs_string):
        """Preenche os widgets com dados do BD ou com o placeholder correto."""
        for widget, key in [(self.allergies_textbox, "Alergias"), 
                              (self.restrictions_textbox, "Restrições Alimentares"), 
                              (self.other_textbox, "Outras Preferências")]:
            
            # Procura pelo conteúdo da preferência na string do banco
            match = re.search(fr"{key}:\s*(.*?)(?:\n\n[A-Z]|$)", prefs_string or "", re.DOTALL)
            content = match.group(1).strip() if match else ""
            
            widget.delete("1.0", "end") # Sempre limpa o widget primeiro
            
            if content:
                # Se encontrou conteúdo, insere e colore como texto normal
                widget.insert("1.0", content)
                widget.configure(text_color=self.NORMAL_TEXT_COLOR)
            else:
                # Se não encontrou, insere o texto do placeholder e colore como cinza
                placeholder_text = self.placeholders.get(widget)
                widget.insert("1.0", placeholder_text)
                widget.configure(text_color=self.PLACEHOLDER_COLOR)

    # --- CORREÇÃO: Salvamento que Ignora Placeholders ---
    def save_preferences(self):
        """Salva os dados, garantindo que o texto do placeholder não seja salvo."""
        def get_clean_text(widget):
            # A forma mais segura de saber se é um placeholder é pela cor
            if widget.cget("text_color") == self.PLACEHOLDER_COLOR:
                return "" # Retorna vazio se for um placeholder
            return widget.get("1.0", "end-1c").strip()

        # Pega o texto limpo de cada campo
        allergies = get_clean_text(self.allergies_textbox)
        restrictions = get_clean_text(self.restrictions_textbox)
        other = get_clean_text(self.other_textbox)

        # Monta a string final apenas com os campos que têm conteúdo real
        final_prefs_list = []
        if allergies: final_prefs_list.append(f"Alergias: {allergies}")
        if restrictions: final_prefs_list.append(f"Restrições Alimentares: {restrictions}")
        if other: final_prefs_list.append(f"Outras Preferências: {other}")
        
        final_prefs_string = "\n\n".join(final_prefs_list)

        try:
            cursor = self.conexao.cursor()
            cursor.execute("UPDATE usuarios SET preferencias = %s WHERE id = %s", (final_prefs_string, self.user_id))
            self.conexao.commit()
            cursor.close()
            messagebox.showinfo("Sucesso", "Suas preferências foram salvas com sucesso!")
        except Error as e:
            self.conexao.rollback()
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível salvar as preferências: {e}")

    def voltar(self):
        self.destroy()
        try:
            main_menu_path = str(OUTPUT_PATH / "gui1.py")
            subprocess.Popen([sys.executable, main_menu_path])
        except Exception as e:
            print(f"Erro ao tentar abrir a tela principal: {e}")

if __name__ == "__main__":
    conexao = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    if conexao:
        app = PreferencesApp(conexao_bd=conexao)
        app.mainloop()
        if conexao.is_connected():
            conexao.close()
            print("Log: Conexão com o BD fechada ao finalizar o app de preferências.")
    else:
        print("CRÍTICO: A aplicação de preferências não pôde ser iniciada.")