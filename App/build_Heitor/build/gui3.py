import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from tkinter import messagebox
import json
import os
import google.generativeai as genai
import threading
from gui0 import GOOGLE_API_KEY

# --- NOVOS IMPORTS PARA COMANDO DE VOZ ---
import speech_recognition as sr
import re
import time

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"AVISO: Não foi possível configurar a API do Gemini. A função de nutrição estará desabilitada. Erro: {e}")
    model = None


def get_nutritional_info_from_api(item_name):
    model = genai.GenerativeModel('gemini-2.5-flash')
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "SUA_CHAVE_API_AQUI":
        print("API Key do Google não configurada.")
        return None
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = (
                f"Forneça as informações nutricionais para 100g do alimento '{item_name}'.\n"
                f"Responda APENAS com um objeto JSON contendo as seguintes chaves (sem texto adicional antes ou depois): "
                f"'valor_energetico_kcal', 'acucares_totais_g', 'acucares_adicionados_g', 'carboidratos_g', "
                f"'proteinas_g', 'gorduras_totais_g', 'gorduras_saturadas_g', 'gorduras_trans_g', "
                f"'fibra_alimentar_g', 'sodio_g'.\n"
                f"Use o valor 0 se a informação não for encontrada ou não se aplicar. Use o valor numérico null se for desconhecido."
                f"Exemplo de resposta: {{\"valor_energetico_kcal\": 52, ...}}"
        )
        response = model.generate_content(prompt)

        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()

        print(f"Resposta da API para '{item_name}':\n{cleaned_response}")
        return json.loads(cleaned_response)
    
    except Exception as e:
        print(f"Erro ao chamar a API Gemini: {e}")
        messagebox.showerror("Erro de API", f"Não foi possível obter os dados nutricionais para '{item_name}'.\nDetalhes: {e}")
        return None

def conectar_mysql(host, database, user, password):
    try:
        conexao = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        if conexao.is_connected():
            db_info = conexao.get_server_info()
            print(f"Conectado ao MySQL versão {db_info}")
            cursor = conexao.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print(f"Você está conectado ao banco de dados: {record[0]}")
            print("Log: Conexão ao MySQL bem-sucedida!")
            return conexao
    except Error as e:
        print(f"Log: Erro CRÍTICO ao conectar ao MySQL: {e}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}\n\nVerifique suas credenciais e se o servidor MySQL está rodando.")
        return None

# --- SUAS CREDENCIAIS ---
db_host = "localhost"
db_name = "mygeli"
db_usuario = "foodyzeadm"
db_senha = "supfood0017admx"

# --- CAMINHOS DOS ARQUIVOS ---
OUTPUT_PATH = Path(__file__).parent
SETA_IMAGE_PATH = OUTPUT_PATH / "assets" / "geral" / "seta.png"
UP_ARROW_IMAGE_PATH = OUTPUT_PATH / "assets" / "geral" / "up_arrow.png"
DOWN_ARROW_IMAGE_PATH = OUTPUT_PATH / "assets" / "geral" / "down_arrow.png"
# --- NOVO ÍCONE ---
MIC_IMAGE_PATH = OUTPUT_PATH / "assets" / "geral" / "mic_icon.png" 

class InventoryApp(ctk.CTk):
    def __init__(self, db_connection):
        super().__init__()

        self.connection = db_connection
        self.local_stock = {}
        self.voice_feedback_window = None

        if not self.connection:
            self.destroy()
            return
    
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Estoque")
        window_width = 400
        window_height = 650
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.minsize(400, 650); self.maxsize(400, 650)
        self.configure(fg_color="#F5F5F5")

        self.vcmd = (self.register(self._validate_numeric_input), '%P')
        
        # --- NOVAS VARIÁVEIS DE ESTADO PARA GRAVAÇÃO ---
        self.recognizer = sr.Recognizer()
        self.is_recording = False
        self.audio_frames = []
        self.recording_thread = None
        self.sample_rate = None
        self.sample_width = None


        try:
            self.title_font = ctk.CTkFont("Poppins Bold", 22)
            self.header_font = ctk.CTkFont("Poppins Medium", 16)
            self.item_name_font = ctk.CTkFont("Poppins Medium", 14)
            self.qty_font = ctk.CTkFont("Poppins Regular", 14)
            self.dialog_label_font = ctk.CTkFont("Poppins Regular", 12)
            self.dialog_hint_font = ctk.CTkFont("Poppins Regular", 10, slant="italic") 
            self.dialog_entry_font = ctk.CTkFont("Poppins Regular", 12)
            self.dialog_button_font = ctk.CTkFont("Poppins Medium", 12)
        except Exception:
            self.title_font, self.header_font, self.item_name_font, self.qty_font, self.dialog_label_font, self.dialog_hint_font, self.dialog_entry_font, self.dialog_button_font = ("Arial", 22, "bold"), ("Arial", 16), ("Arial", 14), ("Arial", 14), ("Arial", 12), ("Arial", 10, "italic"), ("Arial", 12), ("Arial", 12, "bold")

        self.measurement_units = ["Unidades", "Quilos (Kg)", "Gramas (g)", "Litros (L)", "Mililitros (ml)"]
        self.mass_units = ["Gramas (g)", "Quilos (Kg)"]
        self.volume_units = ["Mililitros (ml)", "Litros (L)"]
        self.unit_units = ["Unidades"]
        
        self.create_widgets()
        self.after(100, self.check_low_stock_on_startup)

    # --- INÍCIO DA SEÇÃO DE COMANDO DE VOZ (LÓGICA PUSH-TO-TALK) ---

    def _show_voice_feedback(self, message):
        """Cria ou atualiza uma janela de feedback para o comando de voz."""
        if self.voice_feedback_window is None or not self.voice_feedback_window.winfo_exists():
            self.voice_feedback_window = ctk.CTkToplevel(self)
            self.voice_feedback_window.title("Comando de Voz")
            self.voice_feedback_window.transient(self)
            self.voice_feedback_window.grab_set()
            self.voice_feedback_window.resizable(False, False)
            self._center_dialog(self.voice_feedback_window, 300, 100)
            self.voice_feedback_label = ctk.CTkLabel(self.voice_feedback_window, text=message, font=self.item_name_font)
            self.voice_feedback_label.pack(expand=True, padx=20, pady=20)
        else:
            self.voice_feedback_label.configure(text=message)
        self.voice_feedback_window.update()

    def _close_voice_feedback(self, delay=2000):
        """Fecha a janela de feedback após um tempo."""
        if self.voice_feedback_window and self.voice_feedback_window.winfo_exists():
            self.after(delay, self.voice_feedback_window.destroy)

    def _start_recording(self, event):
        """Inicia a gravação de áudio em uma thread separada."""
        self.audio_frames.clear()
        self.is_recording = True
        
        # CRIA a janela de feedback PRIMEIRO
        self._show_voice_feedback("Ouvindo... (solte para parar)")

        # Associa o evento de soltar o botão À JANELA de feedback, que tem o foco
        if self.voice_feedback_window and self.voice_feedback_window.winfo_exists():
            self.voice_feedback_window.bind("<ButtonRelease-1>", self._stop_recording_and_process)

        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()

    def _record_loop(self):
        """Loop que captura áudio do microfone enquanto is_recording for True."""
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
            self.sample_rate = source.SAMPLE_RATE
            self.sample_width = source.SAMPLE_WIDTH
            while self.is_recording:
                try:
                    self.audio_frames.append(source.stream.read(source.CHUNK))
                except Exception as e:
                    print(f"Erro ao ler o stream de áudio: {e}")
                    break
    
    def _stop_recording_and_process(self, event):
        """Para a gravação e inicia o processamento em uma nova thread."""
        # Desassocia o evento para evitar chamadas múltiplas ou acidentais
        if self.voice_feedback_window and self.voice_feedback_window.winfo_exists():
            self.voice_feedback_window.unbind("<ButtonRelease-1>")

        if not self.is_recording:
            return
        
        self.is_recording = False
        self._show_voice_feedback("Processando...")
        
        # Inicia uma thread para aguardar o fim da gravação e processar o áudio
        # Isso evita que a UI congele enquanto espera a thread de gravação terminar.
        threading.Thread(target=self._process_audio_in_background, daemon=True).start()

    def _process_audio_in_background(self):
        """Aguarda o fim da gravação e então processa os dados de áudio."""
        if self.recording_thread:
            self.recording_thread.join() # Aguarda a thread de gravação finalizar

        if not self.audio_frames:
            self.after(0, self._show_voice_feedback, "Nenhum áudio gravado.")
            self.after(0, self._close_voice_feedback)
            return

        recorded_data = b"".join(self.audio_frames)
        audio_data = sr.AudioData(recorded_data, self.sample_rate, self.sample_width)

        try:
            texto = self.recognizer.recognize_google(audio_data, language='pt-BR')
            print(f"Log (Voz): Texto reconhecido: '{texto}'")
            
            # CORREÇÃO: Chama a função do Gemini e verifica a resposta
            comando = self._interpretar_comando_com_gemini(texto)
            
            if comando and "erro" not in comando:
                msg_confirmacao = f"Entendido:\n{comando['acao'].capitalize()} {comando['quantidade']:g} {comando['unidade']} de {comando['item']}".replace('.',',')
                self.after(0, self._show_voice_feedback, msg_confirmacao)
                self.after(1500, self._executar_acao_db, comando)
            else:
                erro_msg = comando.get('erro', 'Comando não reconhecido.') if isinstance(comando, dict) else 'Comando não reconhecido.'
                self.after(0, self._show_voice_feedback, f"Erro: {erro_msg}")
                self.after(0, self._close_voice_feedback, 3000)

        except sr.UnknownValueError:
            self.after(0, self._show_voice_feedback, "Não entendi. Fale claramente.")
            self.after(0, self._close_voice_feedback)
        except sr.RequestError as e:
            self.after(0, self._show_voice_feedback, "Erro de conexão com API de voz.")
            self.after(0, self._close_voice_feedback)
            print(f"Log (Voz): Erro na API do Google; {e}")

    def _interpretar_comando_com_gemini(self, texto):
        """Envia o texto transcrito para a API Gemini para interpretação e formatação."""
        if not model:
            messagebox.showwarning("API Desabilitada", "A funcionalidade de voz com Gemini não está ativa. Verifique a chave da API.")
            return {"erro": "API do Gemini não configurada."}
        if not texto:
            return None

        prompt = (
            "Você é um assistente de um aplicativo de gerenciamento de despensa. Sua tarefa é analisar a transcrição de um comando de voz do usuário e extraí-la para um formato JSON estruturado e sem formatação markdown.\n"
            "O JSON de saída deve ter as seguintes chaves:\n"
            "- `acao`: pode ser \"adicionar\" ou \"remover\".\n"
            "- `quantidade`: um número (float ou int).\n"
            "- `unidade`: uma das seguintes opções padronizadas: \"Unidades\", \"Quilos (Kg)\", \"Gramas (g)\", \"Litros (L)\", \"Mililitros (ml)\". Se nenhuma unidade for mencionada para um item contável, use \"Unidades\".\n"
            "- `item`: o nome do produto, corrigindo possíveis erros de transcrição.\n\n"
            "Regras:\n"
            "- Normalize as ações: 'tirar', 'retirar', 'remover' devem se tornar \"remover\". 'adicionar', 'colocar', 'incluir' devem se tornar \"adicionar\".\n"
            "- Normalize as unidades: 'quilo'/'quilos'/'kg' para \"Quilos (Kg)\", 'grama'/'gramas'/'g' para \"Gramas (g)\", 'litro'/'litros'/'l' para \"Litros (L)\", 'mililitro'/'mililitros'/'ml' para \"Mililitros (ml)\".\n"
            "- Se o texto não parecer um comando válido, retorne um JSON com a chave 'erro' e a mensagem 'Comando não reconhecido.'.\n"
            "- Corrija erros de digitação ou transcrição no nome do item. Por exemplo, 'arros' deve virar 'arroz'.\n\n"
            "Exemplos:\n"
            "1. Texto de entrada: \"adicionar dois quilos e meio de arroz\"\n"
            "   JSON de saída: {\"acao\": \"adicionar\", \"quantidade\": 2.5, \"unidade\": \"Quilos (Kg)\", \"item\": \"arroz\"}\n"
            "2. Texto de entrada: \"tira 500g de farinha\"\n"
            "   JSON de saída: {\"acao\": \"remover\", \"quantidade\": 500, \"unidade\": \"Gramas (g)\", \"item\": \"farinha\"}\n"
            "3. Texto de entrada: \"coloca 3 ovos\"\n"
            "   JSON de saída: {\"acao\": \"adicionar\", \"quantidade\": 3, \"unidade\": \"Unidades\", \"item\": \"ovos\"}\n"
            "4. Texto de entrada: \"qual a previsão do tempo\"\n"
            "   JSON de saída: {\"erro\": \"Comando não reconhecido.\"}\n"
            "5. Texto de entrada: \"remover um litro de leiti\"\n"
            "   JSON de saída: {\"acao\": \"remover\", \"quantidade\": 1, \"unidade\": \"Litros (L)\", \"item\": \"leite\"}\n\n"
            f"Agora, processe o seguinte texto e retorne APENAS o objeto JSON:\n"
            f"'{texto}'"
        )

        try:
            print("Log (Voz/Gemini): Enviando prompt para a API.")
            response = model.generate_content(prompt)
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
            print(f"Log (Voz/Gemini): Resposta recebida:\n{cleaned_response}")
            
            comando = json.loads(cleaned_response)
            return comando
            
        except Exception as e:
            print(f"Erro ao processar comando com Gemini: {e}")
            return {"erro": "Falha ao contatar a IA."}

    def _executar_acao_db(self, comando):
        """Executa a ação de adicionar ou remover item no banco de dados."""
        if not comando: return
        name, qty_input, selected_unit = comando['item'], comando['quantidade'], comando['unidade']
        qty_base, unit_base = self.converter_para_base(qty_input, selected_unit)
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM produtos WHERE nome_produto = %s", (name,))
            result = cursor.fetchone()
            if comando['acao'] == 'adicionar':
                if result:
                    if result['tipo_volume'] != unit_base:
                        messagebox.showerror("Erro de Voz", f"Unidade incompatível. '{name}' é medido em '{result['tipo_volume']}'.")
                        return
                    new_qty = float(result['quantidade_produto']) + qty_base
                    cursor.execute("UPDATE produtos SET quantidade_produto = %s WHERE nome_produto = %s", (new_qty, name))
                else:
                    nutritional_data = get_nutritional_info_from_api(name) or {}
                    keys = ["valor_energetico_kcal", "acucares_totais_g", "acucares_adicionados_g", "carboidratos_g", "proteinas_g", "gorduras_totais_g", "gorduras_saturadas_g", "fibra_alimentar_g", "sodio_g"]
                    query = f"INSERT INTO produtos (nome_produto, quantidade_produto, tipo_volume, {', '.join(keys)}) VALUES (%s, %s, %s, {', '.join(['%s']*len(keys))})"
                    values = (name, qty_base, unit_base) + tuple(nutritional_data.get(k) for k in keys)
                    cursor.execute(query, values)
            elif comando['acao'] == 'remover':
                if not result:
                    messagebox.showerror("Erro de Voz", f"Item '{name}' não encontrado no estoque."); return
                stock_qty_base = float(result["quantidade_produto"])
                if result['tipo_volume'] != unit_base:
                     messagebox.showerror("Erro de Voz", f"Unidade incompatível. '{name}' é medido em '{result['tipo_volume']}'."); return
                if stock_qty_base < qty_base:
                    messagebox.showwarning("Erro de Voz", f"Quantidade insuficiente para remover de '{name}'."); return
                nova_quantidade = stock_qty_base - qty_base
                if abs(nova_quantidade) < 0.001: cursor.execute("DELETE FROM produtos WHERE nome_produto = %s", (name,))
                else: cursor.execute("UPDATE produtos SET quantidade_produto = %s WHERE nome_produto = %s", (nova_quantidade, name))
            self.connection.commit()
            cursor.close()
            self._refresh_item_list()
            self.after(0, self._show_voice_feedback, "Estoque atualizado!")
            self._close_voice_feedback()
        except Error as e:
            self.connection.rollback()
            self.after(0, self._show_voice_feedback, "Erro no banco de dados.")
            self._close_voice_feedback(3000)
            messagebox.showerror("Erro de BD", f"Falha na operação por voz: {e}")

    # --- FIM DA SEÇÃO DE COMANDO DE VOZ ---

    def _validate_numeric_input(self, value_if_allowed):
        if value_if_allowed == "": return True
        try:
            float(value_if_allowed.replace(',', '.'))
            return True
        except ValueError:
            return False

    def open_history_window(self):
        print("Abrindo a tela de histórico (gui_historico.py).")
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Log (gui3): Conexão com o BD fechada antes de abrir o histórico.")
        self.destroy()
        try:
            subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui_historico.py")])
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir gui_historico.py: {e}")
    
    def _show_nutritional_info(self, item_name):
        try:
            cursor = self.connection.cursor(dictionary=True)
            dados_foram_atualizados = self._try_update_nutritional_info_if_missing(item_name, cursor)
            cursor.close()
            if dados_foram_atualizados:
                print("Log: Cache local (self.local_stock) desatualizado. Recarregando do BD...")
                self.load_stock_from_db(self.search_entry.get().strip())
        except Error as e:
            messagebox.showerror("Erro de BD", f"Não foi possível verificar as informações nutricionais: {e}")
            return

        item_data = self.local_stock.get(item_name)
        if not item_data: return
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Info: {item_name}")
        dialog.configure(fg_color="white")
        self._center_dialog(dialog, 320, 480)
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(pady=15, padx=20, fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=1)
       
        try:
            title_font, table_font, legend_font = ctk.CTkFont("Arial", 14, "bold"), ctk.CTkFont("Arial", 12), ctk.CTkFont("Arial", 10, "italic")
        except:
            title_font, table_font, legend_font = ("Arial", 14, "bold"), ("Arial", 12), ("Arial", 10, "italic")
            
        ctk.CTkLabel(main_frame, text="INFORMAÇÕES NUTRICIONAIS", font=title_font, text_color="black").grid(row=0, column=0, columnspan=2, pady=(0, 5))
        ctk.CTkLabel(main_frame, text="Porção: 100g", font=table_font, text_color="gray50").grid(row=1, column=0, columnspan=2, pady=(0, 15))
        
        nutrients_map = {
            "Valor energético": ("valor_energetico_kcal", "kcal"),
            "Açúcares Totais": ("acucares_totais_g", "g"),
            "Açúcares Adicionados": ("acucares_adicionados_g", "g"),
            "Carboidratos": ("carboidratos_g", "g"), 
            "Proteínas": ("proteinas_g", "g"),
            "Gorduras totais": ("gorduras_totais_g", "g"),
            "Gorduras saturadas": ("gorduras_saturadas_g", "g"),
            "Fibra alimentar": ("fibra_alimentar_g", "g"), 
            "Sódio": ("sodio_g", "g")
        }
        
        last_row = 0
        for i, (label, (db_key, unit)) in enumerate(nutrients_map.items(), start=2):
            ctk.CTkLabel(main_frame, text=label, font=table_font, text_color="black", anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            value = item_data.get(db_key)
            value_text = f"{value:.1f} {unit}".replace('.', ',') if value is not None else "*"
            ctk.CTkLabel(main_frame, text=value_text, font=table_font, text_color="black", anchor="e").grid(row=i, column=1, sticky="e", pady=2)
            last_row = i
            
        ctk.CTkLabel(main_frame, text="* informação indisponível", font=legend_font, text_color="gray50").grid(row=last_row + 1, column=0, columnspan=2, pady=(15, 0), sticky="w")
        dialog.after(100, dialog.lift)
    
    def _try_update_nutritional_info_if_missing(self, name, cursor):
        try:
            campos_nutricionais = "valor_energetico_kcal, acucares_totais_g, acucares_adicionados_g, carboidratos_g, proteinas_g, gorduras_totais_g, gorduras_saturadas_g, fibra_alimentar_g, sodio_g"
            cursor.execute(f"SELECT {campos_nutricionais} FROM produtos WHERE nome_produto = %s", (name,))
            result = cursor.fetchone()

            if result and any(value is None for value in result.values()):
                print(f"Dados nutricionais incompletos para '{name}'. Buscando na API...")
                nutritional_data = get_nutritional_info_from_api(name)
                
                if nutritional_data:
                    keys = list(result.keys())
                    query = f"UPDATE produtos SET {', '.join([f'{k} = %s' for k in keys])} WHERE nome_produto = %s"
                    values = [nutritional_data.get(k) for k in keys] + [name]
                    cursor.execute(query, tuple(values))
                    self.connection.commit()
                    print(f"Dados nutricionais de '{name}' atualizados com sucesso no banco de dados.")
                    return True
        except Error as e:
            print(f"Erro de BD ao tentar atualizar info nutricional para {name}: {e}")
        return False

    def converter_para_base(self, quantidade, unidade):
        unidade_lower = unidade.lower()
        if 'kg' in unidade_lower or 'quilos' in unidade_lower:
            return (float(quantidade) * 1000, 'Gramas')
        elif 'g' in unidade_lower or 'gramas' in unidade_lower:
            return (float(quantidade), 'Gramas')
        if 'ml' in unidade_lower or 'mililitros' in unidade_lower:
            return (float(quantidade), 'Mililitros')
        elif 'l' in unidade_lower or 'litros' in unidade_lower:
            return (float(quantidade) * 1000, 'Mililitros')
        if 'unidades' in unidade_lower:
            return (int(quantidade), 'Unidades')
        return (float(quantidade), unidade)
    
    def formatar_exibicao(self, quantidade, unidade):
        qtd_float = float(quantidade)
        if unidade == 'Gramas' and qtd_float >= 1000:
            qtd_convertida = qtd_float / 1000
            return ("{:g}".format(qtd_convertida).replace('.', ','), "Kg")
        if unidade == 'Mililitros' and qtd_float >= 1000:
            qtd_convertida = qtd_float / 1000
            return ("{:g}".format(qtd_convertida).replace('.', ','), "L")
        return ("{:g}".format(qtd_float).replace('.', ','), unidade)
    
    def go_to_gui1(self):
        print("Botão Voltar clicado! Voltando para a tela inicial (gui1.py).")
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Log: Conexão com o BD fechada.")
        self.destroy()
        try:
            subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir gui1.py: {e}")

    def load_stock_from_db(self, search_term=""):
        try:
            if not self.connection.is_connected():
                self.connection.reconnect()
            cursor = self.connection.cursor(dictionary=True)
            if search_term:
                query = "SELECT * FROM produtos WHERE nome_produto LIKE %s ORDER BY nome_produto ASC"
                cursor.execute(query, (f"%{search_term}%",))
            else:
                query = "SELECT * FROM produtos ORDER BY nome_produto ASC"
                cursor.execute(query)
            products_from_db = cursor.fetchall()
            self.local_stock.clear()
            for product in products_from_db:
                self.local_stock[product['nome_produto']] = product
            cursor.close()
            print(f"Log: Estoque carregado. {len(self.local_stock)} itens encontrados para o termo '{search_term}'.")
        except Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao carregar o estoque: {e}")
            self.local_stock = {}

    def _on_search_typing(self, event=None):
        search_term = self.search_entry.get().strip()
        self._refresh_item_list(search_term)

    def create_widgets(self):
        self.grid_rowconfigure(0, weight=0); self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)
        self.header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0084FF"); self.header_frame.grid(row=0, column=0, sticky="nsew"); self.header_frame.grid_propagate(False); self.header_frame.grid_columnconfigure(0, weight=0); self.header_frame.grid_columnconfigure(1, weight=1)
        try:
            pil_seta_img = Image.open(SETA_IMAGE_PATH).resize((30, 30), Image.LANCZOS).convert("RGBA"); seta_image = ctk.CTkImage(light_image=pil_seta_img, dark_image=pil_seta_img, size=(30, 30)); self.back_btn = ctk.CTkButton(self.header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.go_to_gui1)
        except Exception:
            self.back_btn = ctk.CTkButton(self.header_frame, text="Voltar", font=self.header_font, fg_color="transparent", hover_color="#0066CC", text_color="white", command=self.go_to_gui1)
        self.back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")
        ctk.CTkLabel(self.header_frame, text="Estoque", font=self.title_font, text_color="white", bg_color="transparent").grid(row=0, column=1, pady=20, sticky="nsew")
        
        self.content_frame = ctk.CTkFrame(self, fg_color="#F5F5F5", corner_radius=0)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0); self.content_frame.grid_rowconfigure(1, weight=0); self.content_frame.grid_rowconfigure(3, weight=1) 

        self.search_entry = ctk.CTkEntry(self.content_frame, placeholder_text="🔎 Pesquisar item...", font=self.item_name_font, height=40, corner_radius=10, border_width=1, border_color="#0084FF")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        self.search_entry.bind("<KeyRelease>", self._on_search_typing)

        self.action_buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.action_buttons_frame.grid(row=1, column=0, pady=(5, 10))
        self.action_buttons_frame.grid_columnconfigure(0, weight=1); self.action_buttons_frame.grid_columnconfigure(1, weight=0) 
        self.action_buttons_frame.grid_columnconfigure(2, weight=0); self.action_buttons_frame.grid_columnconfigure(3, weight=0)
        self.action_buttons_frame.grid_columnconfigure(4, weight=1) 
        
        up_arrow_image = None; down_arrow_image = None; mic_image = None
        try: pil_up_arrow = Image.open(UP_ARROW_IMAGE_PATH).resize((40, 40), Image.LANCZOS); up_arrow_image = ctk.CTkImage(light_image=pil_up_arrow, size=(40, 40))
        except Exception as e: print(f"Erro ao carregar 'up_arrow.png': {e}")
        try: pil_down_arrow = Image.open(DOWN_ARROW_IMAGE_PATH).resize((40, 40), Image.LANCZOS); down_arrow_image = ctk.CTkImage(light_image=pil_down_arrow, size=(40, 40))
        except Exception as e: print(f"Erro ao carregar 'down_arrow.png': {e}")
        try: pil_mic = Image.open(MIC_IMAGE_PATH).resize((40, 40), Image.LANCZOS); mic_image = ctk.CTkImage(light_image=pil_mic, size=(40, 40))
        except Exception as e: print(f"Erro ao carregar 'mic_icon.png': {e}")

        self.btn_up = ctk.CTkButton(self.action_buttons_frame, text="" if up_arrow_image else "ADD", image=up_arrow_image, width=50, height=50, fg_color="#0084FF", hover_color="#0066CC", corner_radius=12, command=self.open_add_item_dialog); self.btn_up.grid(row=0, column=1, padx=10, pady=5)
        
        self.btn_voice = ctk.CTkButton(self.action_buttons_frame, text="" if mic_image else "VOZ", image=mic_image, width=60, height=60, fg_color="#5856D6", hover_color="#4341A7", corner_radius=30); self.btn_voice.grid(row=0, column=2, padx=10, pady=5)
        self.btn_voice.bind("<ButtonPress-1>", self._start_recording)
        # O evento de soltar o botão agora é gerenciado dinamicamente

        self.btn_remove = ctk.CTkButton(self.action_buttons_frame, text="" if down_arrow_image else "REM", image=down_arrow_image, width=50, height=50, fg_color="#0084FF", hover_color="#0066CC", corner_radius=12, command=self.open_remove_item_dialog); self.btn_remove.grid(row=0, column=3, padx=10, pady=5)
        
        ctk.CTkLabel(self.action_buttons_frame, text="Adicionar  |  Por Voz  |  Remover", font=self.header_font, text_color="#333333").grid(row=1, column=1, columnspan=3, pady=(0,10))

        self.btn_history = ctk.CTkButton(self.content_frame, text="Histórico de Uso", height=40, fg_color="#95a5a6", hover_color="#7F8C8D", corner_radius=10, command=self.open_history_window, font=self.header_font)
        self.btn_history.grid(row=2, column=0, pady=(5,10), padx=20, sticky="ew")

        self.items_container = ctk.CTkScrollableFrame(self.content_frame, fg_color="#F5F5F5", corner_radius=0)
        self.items_container.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 2))
        self.items_container.grid_columnconfigure(0, weight=1)

        self._refresh_item_list()

    def _refresh_item_list(self, search_term=""):
        self.load_stock_from_db(search_term)
        for widget in self.items_container.winfo_children():
            widget.destroy()
        if not self.local_stock:
            msg = "Nenhum item encontrado." if search_term else "Seu estoque está vazio.\nAdicione um item para começar."
            ctk.CTkLabel(self.items_container, text=msg, font=self.item_name_font, text_color="#666666").pack(pady=30)
        else:
            for i, (name, data) in enumerate(self.local_stock.items()):
                self._add_item_widget(name, data["quantidade_produto"], data["tipo_volume"], i)
        self.items_container.update_idletasks()

    def _add_item_widget(self, name, qty, unit, row_index):
        item_color = "#0084FF"; text_color = "white"; is_low_stock = False
        try:
            numeric_qty = float(qty)
            if (unit == 'Unidades' and numeric_qty <= 2) or \
               (unit == 'Gramas' and numeric_qty <= 500) or \
               (unit == 'Mililitros' and numeric_qty <= 500):
                is_low_stock = True
            if is_low_stock: item_color = "#FFA500"; text_color = "#000000"
        except (ValueError, TypeError): pass
        item_frame = ctk.CTkFrame(self.items_container, fg_color=item_color, corner_radius=12, height=60)
        item_frame.grid(row=row_index, column=0, sticky="ew", pady=5, padx=2); item_frame.grid_propagate(False)
        item_frame.grid_columnconfigure(0, weight=1); item_frame.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(item_frame, text=name, fg_color="transparent", text_color=text_color, font=self.item_name_font, anchor="w").grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        formatted_qtd, display_unit = self.formatar_exibicao(qty, unit)
        qty_label = ctk.CTkLabel(item_frame, text=f"{formatted_qtd} {display_unit}", fg_color="transparent", text_color=text_color, font=self.qty_font)
        qty_label.grid(row=0, column=1, padx=(5, 15), pady=10, sticky="e")
        for widget in [item_frame, item_frame.winfo_children()[0], qty_label]:
            widget.bind("<Button-1>", lambda event, n=name: self._show_nutritional_info(n))

    def _center_dialog(self, dialog, width, height):
        self.update_idletasks(); parent_x = self.winfo_x(); parent_y = self.winfo_y(); parent_width = self.winfo_width(); parent_height = self.winfo_height(); center_x = parent_x + (parent_width // 2) - (width // 2); center_y = parent_y + (parent_height // 2) - (height // 2); dialog.geometry(f"{width}x{height}+{center_x}+{center_y}")

    def check_low_stock_on_startup(self):
        low_stock_items = []
        for name, data in self.local_stock.items():
            try:
                numeric_qty = float(data["quantidade_produto"])
                unit = data["tipo_volume"]
                is_low = (unit == 'Unidades' and numeric_qty <= 2) or \
                         (unit == 'Gramas' and numeric_qty <= 500) or \
                         (unit == 'Mililitros' and numeric_qty <= 500)
                if is_low:
                    formatted_qty, display_unit = self.formatar_exibicao(numeric_qty, unit)
                    low_stock_items.append(f"- {name}: {formatted_qty} {display_unit}")
            except (ValueError, TypeError): continue
        if low_stock_items:
            message = "Os seguintes itens estão com baixo estoque:\n\n" + "\n".join(low_stock_items)
            messagebox.showwarning("Alerta de Estoque Baixo", message)

    def open_add_item_dialog(self):
        self._refresh_item_list() 
        item_names = list(self.local_stock.keys())
        dialog = ctk.CTkToplevel(self)
        dialog.title("Adicionar Item"); dialog.resizable(False, False); dialog.transient(self); dialog.grab_set(); dialog.configure(fg_color="#FFFFFF"); self._center_dialog(dialog, 360, 320)
        
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent"); form_frame.pack(fill="both", expand=True, padx=20, pady=15); form_frame.grid_columnconfigure(1, weight=1)
        unidade_var = ctk.StringVar(value=self.measurement_units[0])
        unidade_combobox = ctk.CTkComboBox(form_frame, values=self.measurement_units, variable=unidade_var, font=self.dialog_entry_font, corner_radius=8, state="readonly", width=150)
        
        def on_item_select_for_add(selected_item_name):
            normalized_name = selected_item_name.strip().capitalize()
            if normalized_name in self.local_stock:
                base_unit = self.local_stock[normalized_name]["tipo_volume"]
                if base_unit == "Gramas": unidade_combobox.configure(values=self.mass_units); unidade_var.set(self.mass_units[0])
                elif base_unit == "Mililitros": unidade_combobox.configure(values=self.volume_units); unidade_var.set(self.volume_units[0])
                else: unidade_combobox.configure(values=self.unit_units); unidade_var.set(self.unit_units[0])
            else: unidade_combobox.configure(values=self.measurement_units); unidade_var.set(self.measurement_units[0])
        
        ctk.CTkLabel(form_frame, text="Nome do Item:", font=self.dialog_label_font).grid(row=0, column=0, columnspan=2, sticky="w")
        nome_combobox = ctk.CTkComboBox(form_frame, values=item_names, width=200, font=self.dialog_entry_font, corner_radius=8, command=on_item_select_for_add)
        nome_combobox.grid(row=1, column=0, columnspan=2, pady=(0,10), sticky="ew")
        nome_combobox.bind('<KeyRelease>', lambda event: on_item_select_for_add(nome_combobox.get())); nome_combobox.set("")
        ctk.CTkLabel(form_frame, text="Quantidade:", font=self.dialog_label_font).grid(row=2, column=0, sticky="w", pady=5)
        qtd_entry = ctk.CTkEntry(form_frame, width=100, font=self.dialog_entry_font, corner_radius=8, validate="key", validatecommand=self.vcmd)
        qtd_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(form_frame, text="Unidade:", font=self.dialog_label_font).grid(row=3, column=0, sticky="w", pady=5)
        unidade_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        def _save_item_action():
            name_raw = nome_combobox.get().strip(); qty_str = qtd_entry.get().strip().replace(',', '.')
            if not name_raw or not qty_str: messagebox.showerror("Erro", "Preencha todos os campos.", parent=dialog); return
            try:
                comando = {"acao": "adicionar", "quantidade": float(qty_str), "unidade": unidade_var.get(), "item": name_raw}
                self._executar_acao_db(comando)
                dialog.destroy()
            except ValueError: messagebox.showerror("Erro", "Quantidade inválida.", parent=dialog)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent"); btn_frame.pack(fill="x", padx=20, pady=(15, 10))
        save_btn = ctk.CTkButton(btn_frame, text="Salvar", command=_save_item_action, font=self.dialog_button_font, fg_color="#0084FF", hover_color="#0066CC"); save_btn.pack(side="right")
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, font=self.dialog_button_font, fg_color="#95a5a6", hover_color="#7F8C8D"); cancel_btn.pack(side="right", padx=10)
        nome_combobox.focus_set()

    def open_remove_item_dialog(self):
        self._refresh_item_list()
        if not self.local_stock: messagebox.showinfo(title="Estoque Vazio", message="Não há itens para remover."); return
        dialog = ctk.CTkToplevel(self); dialog.title("Remover Itens"); dialog.resizable(False, False); dialog.transient(self); dialog.grab_set(); dialog.configure(fg_color="#FFFFFF"); self._center_dialog(dialog, 360, 280)
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent"); form_frame.pack(fill="both", expand=True, padx=20, pady=15); form_frame.grid_columnconfigure(1, weight=1)
        
        item_names = list(self.local_stock.keys()); item_var = ctk.StringVar(value=item_names[0]); unidade_remover_var = ctk.StringVar()

        def on_item_select(selected_item_name):
            unit = self.local_stock[selected_item_name]["tipo_volume"]
            if unit == "Gramas": unidade_remover_combobox.configure(values=self.mass_units); unidade_remover_var.set(self.mass_units[0])
            elif unit == "Mililitros": unidade_remover_combobox.configure(values=self.volume_units); unidade_remover_var.set(self.volume_units[0])
            else: unidade_remover_combobox.configure(values=self.unit_units); unidade_remover_var.set(self.unit_units[0])

        ctk.CTkLabel(form_frame, text="Item:", font=self.dialog_label_font).grid(row=0, column=0, sticky="w", pady=10)
        item_combobox = ctk.CTkComboBox(form_frame, variable=item_var, values=item_names, font=self.dialog_entry_font, state="readonly", command=on_item_select); item_combobox.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(form_frame, text="Quantidade:", font=self.dialog_label_font).grid(row=1, column=0, sticky="w", pady=10)
        qtd_entry = ctk.CTkEntry(form_frame, font=self.dialog_entry_font, validate="key", validatecommand=self.vcmd); qtd_entry.grid(row=1, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(form_frame, text="Unidade:", font=self.dialog_label_font).grid(row=2, column=0, sticky="w", pady=10)
        unidade_remover_combobox = ctk.CTkComboBox(form_frame, variable=unidade_remover_var, font=self.dialog_entry_font, state="readonly", width=150); unidade_remover_combobox.grid(row=2, column=1, sticky="w", padx=5)
        on_item_select(item_combobox.get())
        
        def _remove_item_action():
            name = item_var.get(); qty_str = qtd_entry.get().strip().replace(',', '.')
            if not name or not qty_str: messagebox.showerror("Erro", "Preencha todos os campos.", parent=dialog); return
            try:
                comando = {"acao": "remover", "quantidade": float(qty_str), "unidade": unidade_remover_var.get(), "item": name}
                self._executar_acao_db(comando)
                dialog.destroy()
            except ValueError: messagebox.showerror("Erro", "Quantidade inválida.", parent=dialog)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent"); btn_frame.pack(fill="x", padx=20, pady=(20,10))
        remove_btn = ctk.CTkButton(btn_frame, text="Remover", command=_remove_item_action, font=self.dialog_button_font, fg_color="#f44336", hover_color="#CC3322"); remove_btn.pack(side="right")
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, font=self.dialog_button_font, fg_color="#95a5a6", hover_color="#7F8C8D"); cancel_btn.pack(side="right", padx=10)
        qtd_entry.focus_set()


if __name__ == "__main__":
    db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)

    if db_connection:
        app = InventoryApp(db_connection)
        app.mainloop()

        if app.connection and app.connection.is_connected():
            app.connection.close()
            print("Log: Conexão com o BD fechada ao finalizar o app.")

