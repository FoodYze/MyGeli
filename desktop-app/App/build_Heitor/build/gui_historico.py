import customtkinter as ctk
from pathlib import Path
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from tkinter import messagebox
from PIL import Image

def conectar_mysql(host, database, user, password):
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            print("Log (Histórico): Conexão ao MySQL bem-sucedida!")
            return conexao
    except Error as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
        return None

# --- SUAS CREDENCIAIS ---
db_host = "localhost"
db_name = "mygeli"
db_usuario = "foodyzeadm"
db_senha = "supfood0017admx"

# --- CAMINHOS GERAIS ---
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets" / "geral"

class HistoryApp(ctk.CTk):
    def __init__(self, db_connection):
        super().__init__()
        self.connection = db_connection
        if not self.connection:
            self.destroy()
            return
        
        ctk.set_appearance_mode("light")
        self.title("Histórico de Uso")
        self.geometry("400x650")
        self.minsize(400, 650)
        self.configure(fg_color="#F5F5F5")
        
        self.update_idletasks()
        width, height = 400, 650
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        self.title_font = ctk.CTkFont("Poppins Bold", 22)
        self.header_font = ctk.CTkFont("Poppins Medium", 16)
        self.item_font = ctk.CTkFont("Poppins Regular", 13)
        self.date_font = ctk.CTkFont("Poppins Light", 11)
        self.dialog_font = ctk.CTkFont("Poppins Regular", 12)
        
        self.create_widgets()
        self.load_history()

    def go_to_inventory(self):
        """ Volta para a tela de gerenciamento de estoque. """
        # Fecha a conexão atual ANTES de sair desta tela.
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Log (histórico): Conexão com o BD fechada antes de voltar ao estoque.")

        self.destroy()
        try:
            subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui3.py")])
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir gui3.py: {e}")

    # Função de formatação copiada e adaptada de gui3.py
    def _format_display_quantity(self, quantidade, unidade):
        """Formata a quantidade e a unidade para exibição, convertendo g->Kg e ml->L."""
        try:
            qtd_float = float(quantidade)
            unidade_base = unidade.capitalize()

            # Converte Gramas para Quilos (Kg) se for >= 1000
            if unidade_base == 'Gramas' and qtd_float >= 1000:
                qtd_convertida = qtd_float / 1000
                return ("{:g}".format(qtd_convertida).replace('.', ','), "Kg")
            
            # Converte Mililitros para Litros (L) se for >= 1000
            if unidade_base == 'Mililitros' and qtd_float >= 1000:
                qtd_convertida = qtd_float / 1000
                return ("{:g}".format(qtd_convertida).replace('.', ','), "L")

            # Se não precisar converter, apenas formata o número original
            return ("{:g}".format(qtd_float).replace('.', ','), unidade)
        except (ValueError, TypeError):
            return (str(quantidade), unidade)

    # Função para limpar todo o histórico
    def clear_all_history(self):
        """Apaga todos os registros da tabela de histórico após confirmação."""
        if messagebox.askyesno("Confirmar Exclusão", "Tem certeza que deseja apagar TODO o histórico de uso?\n\nEsta ação não pode ser desfeita.", icon='warning'):
            try:
                if not self.connection.is_connected():
                    self.connection.reconnect()
                
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM historico_uso")
                self.connection.commit()
                cursor.close()
                messagebox.showinfo("Sucesso", "Histórico de uso foi limpo com sucesso.")
                self.load_history()
            except Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Falha ao limpar o histórico: {e}")

    def create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0084FF")
        header_frame.grid(row=0, column=0, sticky="new")
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(1, weight=1)

        try:
            seta_path = ASSETS_PATH / "seta.png" #
            pil_seta_img = Image.open(seta_path).resize((30, 30), Image.LANCZOS)
            seta_image = ctk.CTkImage(light_image=pil_seta_img, size=(30, 30))
            back_btn = ctk.CTkButton(header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.go_to_inventory)
            back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")
        except Exception as e:
            print(f"Erro ao carregar imagem da seta: {e}")
            back_btn = ctk.CTkButton(header_frame, text="Voltar", command=self.go_to_inventory)
            back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")
        
        ctk.CTkLabel(header_frame, text="Histórico de Uso", font=self.title_font, text_color="white").grid(row=0, column=1, pady=20, sticky="nsew")

        #Botão de excluir histórico no cabeçalho
        try:
            lixeira_path = ASSETS_PATH / "lixeira.png" #
            pil_lixeira_img = Image.open(lixeira_path).resize((28, 28), Image.LANCZOS)
            lixeira_image = ctk.CTkImage(light_image=pil_lixeira_img, size=(28, 28))
            clear_btn = ctk.CTkButton(header_frame, text="", image=lixeira_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.clear_all_history)
            clear_btn.grid(row=0, column=2, padx=10, pady=20, sticky="e")
        except Exception as e:
            print(f"Erro ao carregar imagem da lixeira: {e}")
            clear_btn = ctk.CTkButton(header_frame, text="Limpar", command=self.clear_all_history, fg_color="#E74C3C")
            clear_btn.grid(row=0, column=2, padx=10, pady=20, sticky="e")

        self.history_container = ctk.CTkScrollableFrame(self, fg_color="#F5F5F5", corner_radius=0)
        self.history_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.history_container.grid_columnconfigure(0, weight=1)
        
    def load_history(self):
        for widget in self.history_container.winfo_children():
            widget.destroy()
        try:
            if not self.connection.is_connected():
                self.connection.reconnect()
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM historico_uso ORDER BY data_hora_uso DESC")
            history_entries = cursor.fetchall()
            cursor.close()
            if not history_entries:
                ctk.CTkLabel(self.history_container, text="Seu histórico de uso está vazio.", font=self.header_font, text_color="#666").pack(pady=30)
                return
            for entry in history_entries:
                self.add_history_entry_widget(entry)
        except Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao carregar o histórico: {e}")

    def add_history_entry_widget(self, entry_data):
        entry_frame = ctk.CTkFrame(self.history_container, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#E0E0E0")
        entry_frame.grid(sticky="ew", pady=(0, 8))
        entry_frame.grid_columnconfigure(0, weight=1)
        
        top_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,0))
        top_frame.grid_columnconfigure(0, weight=1)
        
        recipe_name = entry_data['nome_receita']
        ctk.CTkLabel(top_frame, text=f"Receita: {recipe_name}", font=self.header_font, text_color="#0084FF", anchor="w").grid(row=0, column=0, sticky="w")
        date_time = entry_data['data_hora_uso'].strftime('%d/%m/%Y %H:%M')
        ctk.CTkLabel(top_frame, text=date_time, font=self.date_font, text_color="#666", anchor="e").grid(row=0, column=1, sticky="e")

        #Usando a nova função de formatação
        formatted_qtd, display_unit = self._format_display_quantity(entry_data['quantidade_usada'], entry_data['unidade_medida'])
        details_text = f"{entry_data['nome_ingrediente']}: {formatted_qtd} {display_unit}"
        ctk.CTkLabel(entry_frame, text=details_text, font=self.item_font, anchor="w").grid(row=1, column=0, sticky="ew", padx=10, pady=(0,10))

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    if db_connection:
        app = HistoryApp(db_connection)
        app.mainloop()
        if app.connection and app.connection.is_connected():
            app.connection.close()
            print("Log (histórico): Conexão com o BD fechada ao finalizar o app.")        