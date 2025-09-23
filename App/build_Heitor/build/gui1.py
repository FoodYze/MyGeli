import customtkinter as ctk
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from pathlib import Path
from PIL import Image, ImageSequence

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

        self._configurar_janela()
        self._criar_fontes()
        self._criar_widgets()

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
        
        # Ícone de Usuário
        user_icon_image = ctk.CTkImage(Image.open(assets_path / "user_icon.png").resize((32, 32), Image.LANCZOS), size=(40, 40))
        user_button = ctk.CTkButton(header_frame, text="", image=user_icon_image, width=45, height=45, fg_color="transparent", hover_color=self.BUTTON_HOVER_COLOR, command=None)
        user_button.pack(side="left", padx=10, pady=10)
        
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
        ctk.CTkButton(buttons_frame, text="GUI4 FUTURA LISTA D COMPRAS", command=lambda: abrir_gui("gui4.py"), height=55, font=self.button_font, fg_color=self.BUTTON_COLOR, hover_color=self.BUTTON_HOVER_COLOR).grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")

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