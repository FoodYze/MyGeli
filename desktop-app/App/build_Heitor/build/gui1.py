import customtkinter as ctk
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from pathlib import Path
from PIL import Image, ImageSequence

from werkzeug.security import check_password_hash
from session_manager import SessionManager
from tkinter import messagebox

# --- Conexão com Banco de Dados ---
def conectar_mysql(host, database, user, password):
    """
    Tenta conectar ao banco de dados MySQL. Retorna a conexão ou None.
    """
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            print("Log: Conexão ao MySQL bem-sucedida!")
            return conexao
    except Error as e:
        print(f"Log: Erro ao conectar ao MySQL: {e}")
        return None

# --- Navegação entre Telas ---
def abrir_gui(nome_arquivo):
    """Fecha a janela atual e abre um novo script de GUI."""
    if app:
        app.destroy()
    try:
        caminho_script = str(Path(__file__).parent / nome_arquivo)
        subprocess.Popen([sys.executable, caminho_script])
    except Exception as e:
        print(f"Erro ao tentar abrir {nome_arquivo}: {e}")

# --- Classe Principal da Aplicação ---
class App(ctk.CTk):
    """
    A tela principal (menu) do aplicativo MyGeli.
    """
    # --- Constantes de Estilo para Padronização ---
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 650
    BG_COLOR = "#F5F5F5"
    HEADER_COLOR = "#0084FF"
    BUTTON_COLOR = "#0084FF"
    BUTTON_HOVER_COLOR = "#0066CC"
    BUTTON_TEXT_COLOR = "white"
    CARD_COLOR = "#FFFFFF"
    CARD_BORDER_COLOR = "#E0E0E0"

    def __init__(self, db_connection):
        super().__init__()
        
        self.db_connection = db_connection
        self.gif_frames = []
        self.current_frame_index = 0
        
        self.session_manager = SessionManager()
        self.user_id = self.session_manager.get_session()

        self._configurar_janela()
        self._criar_fontes()
        self._criar_widgets()
        
        self._atualizar_estado_login()

    def _configurar_janela(self):
        """Define as propriedades principais da janela (título, tamanho, etc.)."""
        self.title("MyGeli")
        ctk.set_appearance_mode("light")
        
        # Centraliza a janela na tela
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width / 2 - self.WINDOW_WIDTH / 2)
        center_y = int(screen_height / 2 - self.WINDOW_HEIGHT / 2)
        
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{center_x}+{center_y}")
        self.minsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.maxsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.configure(fg_color=self.BG_COLOR)

    def _criar_fontes(self):
            self.large_font = ctk.CTkFont("Poppins Bold", 28)
            self.medium_font = ctk.CTkFont("Poppins Medium", 18)
            self.small_font = ctk.CTkFont("Poppins Light", 14)
            self.button_font = ctk.CTkFont("Poppins SemiBold", 18)

    def _criar_widgets(self):
        # --- Configuração do Layout Principal ---
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Cabeçalho ---
        header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=self.HEADER_COLOR)
        header_frame.grid(row=0, column=0, sticky="new")
        header_frame.grid_propagate(False)

        assets_path = Path(__file__).parent / "assets" / "frame1"

        # Ícone de Usuário (continua na esquerda)
        user_icon_image = ctk.CTkImage(Image.open(assets_path / "user_icon.png").resize((32, 32), Image.LANCZOS), size=(40, 40))
        user_button = ctk.CTkButton(header_frame, text="", image=user_icon_image, width=45, height=45, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=self._acao_usuario)
        user_button.pack(side="left", padx=10, pady=10)

        # Ícone de Configurações (será posicionado na extrema direita)
        options_image = ctk.CTkImage(Image.open(assets_path / "options.png").resize((32, 32), Image.LANCZOS), size=(30, 30))
        options_button = ctk.CTkButton(header_frame, text="", image=options_image, width=40, height=40, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=None)
        options_button.pack(side="right", padx=5, pady=5)

        # --- NOVA ALTERAÇÃO AQUI ---
        # Ícone de Calendário (posicionado à esquerda do ícone de configurações)
        # O .pack(side="right") funciona como uma pilha: o último a ser empacotado fica mais à esquerda.
        calendario_image = ctk.CTkImage(Image.open(assets_path / "calendario.png").resize((32, 32), Image.LANCZOS), size=(30, 30))
        calendario_button = ctk.CTkButton(header_frame, text="", image=calendario_image, width=40, height=40, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=lambda: abrir_gui("gui5_planejamento.py"))
        calendario_button.pack(side="right", padx=5, pady=5)
        
        # --- Frame do Conteúdo Principal ---
        # Este frame principal conterá o conteúdo e o espaçador
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew")

        # --- Bloco de Conteúdo (Logo e Botões) ---
        # Este é o frame que agrupa tudo o que queremos que suba
        content_block_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_block_frame.pack(side="top", fill="x", pady=(50, 0)) # pady dá o espaçamento do topo

        # Logo Central
        logo_completo_path = assets_path / "MyGeli.png"
        original_logo_image = Image.open(logo_completo_path)
        original_width, original_height = original_logo_image.size
        target_width = 280
        aspect_ratio = original_height / original_width
        target_height = int(target_width * aspect_ratio)
        resized_logo = original_logo_image.resize((target_width, target_height), Image.LANCZOS)
        logo_image = ctk.CTkImage(light_image=resized_logo, size=(target_width, target_height))
        ctk.CTkLabel(content_block_frame, image=logo_image, text="").pack(pady=(0, 30))

        # Frame dos Botões
        buttons_frame = ctk.CTkFrame(content_block_frame, fg_color=self.CARD_COLOR, corner_radius=12, border_color=self.CARD_BORDER_COLOR, border_width=1)
        buttons_frame.pack(padx=30, fill="x")
        buttons_frame.grid_columnconfigure(0, weight=1)

        # Botões de Navegação
        ctk.CTkButton(buttons_frame, text="FALAR COM GELI", command=lambda: abrir_gui("gui0.py"), height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        ctk.CTkButton(buttons_frame, text="VER RECEITAS", command=lambda: abrir_gui("gui2.py"), height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR).grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="GERENCIAR ESTOQUE", command=lambda: abrir_gui("gui3.py"), height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR).grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkButton(buttons_frame, text="LISTA DE COMPRAS", command=lambda: abrir_gui("gui4.py"), height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR).grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        
    def _acao_usuario(self):
        """
        Verifica se o usuário está logado.
        Se sim, oferece logout. Se não, abre a tela de login.
        """
        if self.user_id:
            # Usuário está logado, perguntar se quer sair
            resposta = messagebox.askyesno("Logout", "Você já está logado. Deseja sair?")
            if resposta: # "Sim"
                self.session_manager.clear_session()
                self.user_id = None
                self._atualizar_estado_login()
        else:
            # Usuário não está logado, abrir tela de login
            self._abrir_tela_login()

    def _abrir_tela_login(self):
        """Cria a janela pop-up (Toplevel) para o login."""
        
        # Impede que múltiplas janelas de login sejam abertas
        if hasattr(self, 'login_window') and self.login_window.winfo_exists():
            self.login_window.focus()
            return

        self.login_window = ctk.CTkToplevel(self)
        self.login_window.title("Login MyGeli")
        self.login_window.geometry("350x300")
        self.login_window.transient(self) # Mantém no topo
        self.login_window.grab_set()      # Bloqueia a janela principal
        self.login_window.resizable(False, False)

        # Centralizar Toplevel (relativo à janela principal)
        x_app = self.winfo_x()
        y_app = self.winfo_y()
        w_app = self.winfo_width()
        h_app = self.winfo_height()
        x_login = x_app + (w_app // 2) - (350 // 2)
        y_login = y_app + (h_app // 2) - (300 // 2)
        self.login_window.geometry(f"350x300+{x_login}+{y_login}")

        # --- Widgets da Janela de Login ---
        
        ctk.CTkLabel(self.login_window, text="Login", font=self.large_font).pack(pady=(20, 10))
        
        # Email
        ctk.CTkLabel(self.login_window, text="E-mail:", font=self.small_font, anchor="w").pack(fill="x", padx=40)
        email_entry = ctk.CTkEntry(self.login_window, width=270, height=35)
        email_entry.pack(pady=(0, 10))
        
        # Senha
        ctk.CTkLabel(self.login_window, text="Senha:", font=self.small_font, anchor="w").pack(fill="x", padx=40)
        senha_entry = ctk.CTkEntry(self.login_window, width=270, height=35, show="*") # Oculta a senha
        senha_entry.pack(pady=(0, 10))

        # Label de Erro
        error_label = ctk.CTkLabel(self.login_window, text="", text_color="red", font=self.small_font)
        error_label.pack()

        # Botão Entrar
        ctk.CTkButton(self.login_window, text="Entrar", width=270, height=40, font=self.button_font,
                      command=lambda: self._executar_login(email_entry, senha_entry, error_label)
                      ).pack(pady=10)
        
        # Link de Cadastro
        link_cadastro = ctk.CTkLabel(self.login_window, text="Não tem uma conta? Crie uma.", text_color="#0066CC",
                                       font=ctk.CTkFont("Poppins Light", 12, underline=True), cursor="hand2")
        link_cadastro.pack()
        # link_cadastro.bind("<Button-1>", lambda e: self._abrir_tela_cadastro()) # Futuramente

    def _executar_login(self, email_entry, senha_entry, error_label):
        """Valida o login contra o banco de dados."""
        
        email = email_entry.get().strip()
        senha = senha_entry.get()

        if not email or not senha:
            error_label.configure(text="Preencha todos os campos.")
            return

        if not self.db_connection or not self.db_connection.is_connected():
            error_label.configure(text="Erro de conexão com o banco.")
            # Tenta reconectar
            self.db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
            return
        
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            query = "SELECT id, email, senha FROM usuarios WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            cursor.close()

            if not user:
                error_label.configure(text="E-mail incorreto! Tente novamente.")
                return
            
            # --- COMPARAÇÃO DA SENHA HASH ---
            # Compara o hash do banco (user['senha']) com a senha digitada (senha)
            if not check_password_hash(user['senha'], senha):
                error_label.configure(text="Senha incorreta! Tente novamente.")
                return
            
            # --- SUCESSO NO LOGIN ---
            self.user_id = user['id']
            self.session_manager.save_session(self.user_id)
            self._atualizar_estado_login()
            self.login_window.destroy() # Fecha a janela de login
            
        except Error as e:
            error_label.configure(text=f"Erro de banco: {e}")
            print(f"Log: Erro de MySQL em _executar_login: {e}")

    def _atualizar_estado_login(self):
        """Atualiza a GUI para refletir o estado de login."""
        if self.user_id:
            print(f"Log: Usuário {self.user_id} está logado.")
            # (Opcional) Mudar o ícone para um "logado"
            # assets_path = Path(__file__).parent / "assets" / "frame1"
            # logged_in_icon = ctk.CTkImage(Image.open(assets_path / "user_logged_in.png")...
            # self.user_button.configure(image=logged_in_icon)
        else:
            print("Log: Nenhum usuário logado.")
            # Garante que o ícone padrão está sendo usado
            # self.user_button.configure(image=self.user_icon_image)
            
    # --- FIM DAS NOVAS FUNÇÕES DE LOGIN ---

# --- Execução da Aplicação ---
if __name__ == "__main__":
    # Credenciais e conexão
    db_host = "localhost"
    db_name = "mygeli"
    db_usuario = "foodyzeadm"
    db_senha = "supfood0017admx"
    
    conexao_ativa = conectar_mysql(db_host, db_name, db_usuario, db_senha)

    app = App(db_connection=conexao_ativa)
    app.mainloop()

    # Fecha a conexão ao sair da aplicação
    if conexao_ativa and conexao_ativa.is_connected():
        conexao_ativa.close()
        print("Log: Conexão com o BD fechada ao finalizar o app.")