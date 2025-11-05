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

# --- CONFIGURAÇÃO ÚNICA DA API GEMINI ---
try:
    if GOOGLE_API_KEY and GOOGLE_API_KEY != "SUA_CHAVE_API_AQUI":
        genai.configure(api_key=GOOGLE_API_KEY)
        # Usando o modelo solicitado
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("Log: API do Gemini configurada com sucesso com o modelo 'gemini-2.5-flash'.")
    else:
        print("AVISO: GOOGLE_API_KEY não encontrada ou é um placeholder. Funções de IA estarão desabilitadas.")
        model = None
except Exception as e:
    print(f"AVISO: Não foi possível configurar a API do Gemini. Funções de IA estarão desabilitadas. Erro: {e}")
    model = None


def get_nutritional_info_from_api(item_name):
    """Busca informações nutricionais de um item usando a API Gemini."""
    # Usa a instância global do modelo, verificando se foi inicializada com sucesso.
    if not model:
        print("Log (Nutrição): API do Gemini não configurada. Impossível buscar dados nutricionais.")
        return None
    
    try:
        prompt = (
                f"Forneça as informações nutricionais para 100g do alimento '{item_name}'.\n"
                f"Responda APENAS com um objeto JSON contendo as seguintes chaves (sem texto adicional, markdown ou explicações): "
                f"'valor_energetico_kcal', 'acucares_totais_g', 'acucares_adicionados_g', 'carboidratos_g', "
                f"'proteinas_g', 'gorduras_totais_g', 'gorduras_saturadas_g', 'gorduras_trans_g', "
                f"'fibra_alimentar_g', 'sodio_g'.\n"
                f"Use o valor numérico 0 se a informação não for encontrada ou não se aplicar. Use null se o valor for desconhecido.\n"
                f"Exemplo de resposta estrita: {{\"valor_energetico_kcal\": 52, \"acucares_totais_g\": 0.1, ...}}"
        )
        response = model.generate_content(prompt)

        # Log da resposta bruta para depuração
        raw_response_text = response.text
        print(f"Log (Nutrição): Resposta bruta da API para '{item_name}':\n---\n{raw_response_text}\n---")
        
        cleaned_response = raw_response_text.strip().replace("```json", "").replace("```", "").strip()

        if not cleaned_response:
             print(f"Log (Nutrição): Erro - A API retornou uma resposta vazia para '{item_name}'.")
             return None

        return json.loads(cleaned_response)
    
    except json.JSONDecodeError:
        print(f"Log (Nutrição): Erro de decodificação JSON para '{item_name}'. A resposta da API não era um JSON válido.")
        return None
    except Exception as e:
        print(f"Log (Nutrição): Erro ao chamar a API Gemini para dados nutricionais de '{item_name}': {e}")
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

    # --- INÍCIO DA SEÇÃO DE COMANDO DE VOZ ---

    def _show_voice_feedback(self, message):
        """Cria ou atualiza uma janela de feedback para o comando de voz."""
        if self.voice_feedback_window is None or not self.voice_feedback_window.winfo_exists():
            self.voice_feedback_window = ctk.CTkToplevel(self)
            self.voice_feedback_window.title("Comando de Voz")
            self.voice_feedback_window.transient(self)
            self.voice_feedback_window.grab_set()
            self.voice_feedback_window.resizable(False, False)
            self._center_dialog(self.voice_feedback_window, 300, 100)
            self.voice_feedback_label = ctk.CTkLabel(self.voice_feedback_window, text=message, font=self.item_name_font, wraplength=280)
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
        self._show_voice_feedback("Ouvindo... (solte para parar)")
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
        if self.voice_feedback_window and self.voice_feedback_window.winfo_exists():
            self.voice_feedback_window.unbind("<ButtonRelease-1>")
        if not self.is_recording: return
        self.is_recording = False
        self._show_voice_feedback("Processando...")
        threading.Thread(target=self._process_audio_in_background, daemon=True).start()

    def _process_audio_in_background(self):
        """Aguarda o fim da gravação e então processa os dados de áudio."""
        if self.recording_thread: self.recording_thread.join()
        if not self.audio_frames:
            self.after(0, self._show_voice_feedback, "Nenhum áudio gravado.")
            self.after(0, self._close_voice_feedback); return

        recorded_data = b"".join(self.audio_frames)
        audio_data = sr.AudioData(recorded_data, self.sample_rate, self.sample_width)

        try:
            texto = self.recognizer.recognize_google(audio_data, language='pt-BR')
            print(f"Log (Voz): Texto reconhecido: '{texto}'")
            comandos = self._interpretar_comando_com_gemini(texto)
            
            if isinstance(comandos, list) and comandos:
                num_itens = len(comandos)
                msg = f"Entendido. Processando {num_itens} {'item' if num_itens == 1 else 'itens'}..."
                self.after(0, self._show_voice_feedback, msg)
                self.after(1000, self._executar_lista_de_acoes_db, comandos)
            elif isinstance(comandos, dict) and "erro" in comandos:
                erro_msg = comandos.get('erro', 'Comando não reconhecido.')
                self.after(0, self._show_voice_feedback, f"Erro: {erro_msg}")
                self.after(0, self._close_voice_feedback, 3000)
            else:
                self.after(0, self._show_voice_feedback, "Comando não reconhecido.")
                self.after(0, self._close_voice_feedback, 3000)

        except sr.UnknownValueError:
            self.after(0, self._show_voice_feedback, "Não entendi. Fale claramente.")
            self.after(0, self._close_voice_feedback)
        except sr.RequestError as e:
            self.after(0, self._show_voice_feedback, "Erro de conexão com API de voz.")
            self.after(0, self._close_voice_feedback)
            print(f"Log (Voz): Erro na API do Google Speech Recognition; {e}")

    def _interpretar_comando_com_gemini(self, texto):
        """Envia o texto transcrito para a API Gemini para interpretação e formatação em uma lista de comandos."""
        if not model:
            print("Log (Voz/Gemini): A API do Gemini não está configurada ou falhou ao inicializar.")
            return {"erro": "A IA não está configurada."}
        if not texto: return None

        prompt = (
            "Sua tarefa é analisar a transcrição de um comando de voz para um aplicativo de gerenciamento de despensa e extrair as ações para um formato de ARRAY JSON. Responda APENAS com o JSON, sem markdown ou qualquer outro texto.\n"
            "Cada objeto no array JSON deve ter as chaves: `acao` (\"adicionar\" ou \"remover\"), `quantidade` (número), `unidade` (\"Unidades\", \"Quilos (Kg)\", \"Gramas (g)\", \"Litros (L)\", \"Mililitros (ml)\"), e `item` (nome do produto).\n\n"
            "Regras Importantes:\n"
            "- Normalize ações: 'tirar', 'usar' -> \"remover\". 'colocar', 'incluir' -> \"adicionar\".\n"
            "- Normalize unidades: 'quilo(s)'/'kg' -> \"Quilos (Kg)\", 'grama(s)'/'g' -> \"Gramas (g)\", etc.\n"
            "- Para itens contáveis sem unidade (ex: '3 ovos'), use \"Unidades\".\n"
            "- Corrija nomes de itens com base no contexto (ex: 'leiti' -> 'leite').\n"
            "- Se o texto não for um comando de estoque válido (ex: 'qual a previsão do tempo'), retorne um objeto JSON com uma única chave 'erro'. Ex: {\"erro\": \"Comando não reconhecido.\"}\n"
            "- SEMPRE retorne um array JSON para comandos válidos, mesmo que contenha apenas um item.\n\n"
            "Exemplos de Saída:\n"
            "- Entrada: \"adicionar dois quilos e meio de arroz e 3 latas de milho\"\n"
            "  Saída: [{\"acao\": \"adicionar\", \"quantidade\": 2.5, \"unidade\": \"Quilos (Kg)\", \"item\": \"arroz\"}, {\"acao\": \"adicionar\", \"quantidade\": 3, \"unidade\": \"Unidades\", \"item\": \"latas de milho\"}]\n"
            "- Entrada: \"tira 500g de farinha\"\n"
            "  Saída: [{\"acao\": \"remover\", \"quantidade\": 500, \"unidade\": \"Gramas (g)\", \"item\": \"farinha\"}]\n"
            "- Entrada: \"qual a previsão do tempo\"\n"
            "  Saída: {\"erro\": \"Comando não reconhecido.\"}\n\n"
            f"Processe o seguinte texto:\n"
            f"'{texto}'"
        )

        try:
            print("Log (Voz/Gemini): Enviando prompt para a API.")
            response = model.generate_content(prompt)
            raw_response_text = response.text
            print(f"Log (Voz/Gemini): Resposta bruta recebida:\n---\n{raw_response_text}\n---")
            cleaned_response = raw_response_text.strip().replace("```json", "").replace("```", "").strip()
            
            if not cleaned_response:
                 print("Log (Voz/Gemini): Erro - A API retornou uma resposta vazia.")
                 return {"erro": "A IA retornou uma resposta vazia."}
            
            return json.loads(cleaned_response)
        
        except json.JSONDecodeError:
            print(f"Log (Voz/Gemini): Erro de decodificação JSON. A resposta da API não era um JSON válido.")
            return {"erro": "A IA retornou um formato inválido."}
        except Exception as e:
            print(f"Log (Voz/Gemini): Ocorreu um erro inesperado ao contatar a API Gemini: {e}")
            return {"erro": "Falha na comunicação com a IA."}

    def _executar_acao_db(self, comando):
        """Executa a ação para UM ÚNICO item (usado pelos diálogos da GUI) e mostra erro na tela se houver."""
        erros = self._executar_lista_de_acoes_db([comando], show_feedback=False)
        if erros:
            messagebox.showerror("Erro de Operação", "\n".join(erros))

    def _executar_lista_de_acoes_db(self, comandos, show_feedback=True):
        """Executa uma lista de ações no banco de dados em uma única transação."""
        erros = []
        try:
            cursor = self.connection.cursor(dictionary=True)
            for comando in comandos:
                try:
                    name_raw, qty_input, selected_unit, acao = comando.get('item'), comando.get('quantidade'), comando.get('unidade'), comando.get('acao')
                    if not all([name_raw, qty_input is not None, selected_unit, acao]):
                        erros.append(f"Comando malformado ignorado: {comando}"); continue
                    
                    name = name_raw.strip().capitalize()
                    qty_base, unit_base = self.converter_para_base(qty_input, selected_unit)
                    
                    cursor.execute("SELECT * FROM produtos WHERE nome_produto = %s", (name,))
                    result = cursor.fetchone()

                    if acao == 'adicionar':
                        if result:
                            if result['tipo_volume'] != unit_base:
                                erros.append(f"Unidade incompatível para '{name}'. O estoque usa '{result['tipo_volume']}'."); continue
                            new_qty = float(result['quantidade_produto']) + qty_base
                            cursor.execute("UPDATE produtos SET quantidade_produto = %s WHERE nome_produto = %s", (new_qty, name))
                        else:
                            nutritional_data = get_nutritional_info_from_api(name) or {}
                            keys = ["valor_energetico_kcal", "acucares_totais_g", "acucares_adicionados_g", "carboidratos_g", "proteinas_g", "gorduras_totais_g", "gorduras_saturadas_g", "fibra_alimentar_g", "sodio_g"]
                            query = f"INSERT INTO produtos (nome_produto, quantidade_produto, tipo_volume, {', '.join(keys)}) VALUES (%s, %s, %s, {', '.join(['%s']*len(keys))})"
                            values = (name, qty_base, unit_base) + tuple(nutritional_data.get(k) for k in keys)
                            cursor.execute(query, values)
                    elif acao == 'remover':
                        if not result:
                            erros.append(f"Item '{name}' não encontrado no estoque."); continue
                        if result['tipo_volume'] != unit_base:
                            erros.append(f"Unidade incompatível para '{name}'. O estoque usa '{result['tipo_volume']}'."); continue
                        if float(result["quantidade_produto"]) < qty_base:
                            erros.append(f"Quantidade insuficiente para remover de '{name}'."); continue
                        
                        nova_quantidade = float(result["quantidade_produto"]) - qty_base
                        if abs(nova_quantidade) < 0.001: cursor.execute("DELETE FROM produtos WHERE nome_produto = %s", (name,))
                        else: cursor.execute("UPDATE produtos SET quantidade_produto = %s WHERE nome_produto = %s", (nova_quantidade, name))
                except Exception as item_error:
                    erros.append(f"Erro ao processar '{comando.get('item', 'item?')}': {item_error}")

            self.connection.commit()
            cursor.close()
            self._refresh_item_list()

            if show_feedback:
                if not erros:
                    self.after(0, self._show_voice_feedback, "Estoque atualizado com sucesso!")
                    self._close_voice_feedback()
                else:
                    msg_final = f"{len(comandos) - len(erros)} itens atualizados.\n\nErros:\n- " + "\n- ".join(erros)
                    self.after(0, self._show_voice_feedback, "Operação concluída com erros.")
                    self.after(500, lambda: self.voice_feedback_window.destroy() if self.voice_feedback_window else None) 
                    messagebox.showwarning("Aviso de Operação", msg_final)
            return erros

        except Error as e:
            self.connection.rollback()
            if show_feedback:
                self.after(0, self._show_voice_feedback, "Erro no banco de dados.")
                self._close_voice_feedback(3000)
                messagebox.showerror("Erro de BD", f"Falha na operação por voz: {e}")
            return [f"Erro de Banco de Dados: {e}"]

    # --- FIM DA SEÇÃO DE COMANDO DE VOZ ---

    def _validate_numeric_input(self, value_if_allowed):
        if value_if_allowed == "": return True
        try: float(value_if_allowed.replace(',', '.')); return True
        except ValueError: return False

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
            messagebox.showerror("Erro de BD", f"Não foi possível verificar as informações nutricionais: {e}"); return

        item_data = self.local_stock.get(item_name)
        if not item_data: return
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Info: {item_name}"); dialog.configure(fg_color="white")
        self._center_dialog(dialog, 320, 480); dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(pady=15, padx=20, fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=3); main_frame.grid_columnconfigure(1, weight=1)
       
        try: title_font, table_font, legend_font = ctk.CTkFont("Arial", 14, "bold"), ctk.CTkFont("Arial", 12), ctk.CTkFont("Arial", 10, "italic")
        except: title_font, table_font, legend_font = ("Arial", 14, "bold"), ("Arial", 12), ("Arial", 10, "italic")
            
        ctk.CTkLabel(main_frame, text="INFORMAÇÕES NUTRICIONAIS", font=title_font, text_color="black").grid(row=0, column=0, columnspan=2, pady=(0, 5))
        ctk.CTkLabel(main_frame, text="Porção: 100g", font=table_font, text_color="gray50").grid(row=1, column=0, columnspan=2, pady=(0, 15))
        
        nutrients_map = {"Valor energético": ("valor_energetico_kcal", "kcal"),"Açúcares Totais": ("acucares_totais_g", "g"),"Açúcares Adicionados": ("acucares_adicionados_g", "g"),"Carboidratos": ("carboidratos_g", "g"), "Proteínas": ("proteinas_g", "g"),"Gorduras totais": ("gorduras_totais_g", "g"),"Gorduras saturadas": ("gorduras_saturadas_g", "g"),"Fibra alimentar": ("fibra_alimentar_g", "g"), "Sódio": ("sodio_g", "g")}
        
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
            campos = "valor_energetico_kcal, acucares_totais_g, acucares_adicionados_g, carboidratos_g, proteinas_g, gorduras_totais_g, gorduras_saturadas_g, fibra_alimentar_g, sodio_g"
            cursor.execute(f"SELECT {campos} FROM produtos WHERE nome_produto = %s", (name,))
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
        except Error as e: print(f"Erro de BD ao tentar atualizar info nutricional para {name}: {e}")
        return False

    def converter_para_base(self, quantidade, unidade):
        unidade_lower = unidade.lower(); qtd = float(str(quantidade).replace(',', '.'))
        if 'kg' in unidade_lower or 'quilos' in unidade_lower: return (qtd * 1000, 'Gramas')
        if 'g' in unidade_lower or 'gramas' in unidade_lower: return (qtd, 'Gramas')
        if 'ml' in unidade_lower or 'mililitros' in unidade_lower: return (qtd, 'Mililitros')
        if 'l' in unidade_lower or 'litros' in unidade_lower: return (qtd * 1000, 'Mililitros')
        if 'unidades' in unidade_lower: return (int(qtd), 'Unidades')
        return (qtd, unidade.capitalize())
    
    def formatar_exibicao(self, quantidade, unidade):
        qtd_float = float(quantidade)
        if unidade == 'Gramas' and qtd_float >= 1000: return ("{:g}".format(qtd_float / 1000).replace('.', ','), "Kg")
        if unidade == 'Mililitros' and qtd_float >= 1000: return ("{:g}".format(qtd_float / 1000).replace('.', ','), "L")
        return ("{:g}".format(qtd_float).replace('.', ','), unidade)
    
    def go_to_gui1(self):
        print("Botão Voltar clicado! Voltando para a tela inicial (gui1.py).")
        if self.connection and self.connection.is_connected(): self.connection.close(); print("Log: Conexão com o BD fechada.")
        self.destroy()
        try: subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
        except Exception as e: messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir gui1.py: {e}")

    def load_stock_from_db(self, search_term=""):
        try:
            if not self.connection.is_connected(): self.connection.reconnect()
            cursor = self.connection.cursor(dictionary=True)
            if search_term:
                query = "SELECT * FROM produtos WHERE nome_produto LIKE %s ORDER BY nome_produto ASC"
                cursor.execute(query, (f"%{search_term}%",))
            else:
                query = "SELECT * FROM produtos ORDER BY nome_produto ASC"
                cursor.execute(query)
            
            self.local_stock = {product['nome_produto']: product for product in cursor.fetchall()}
            cursor.close()
            print(f"Log: Estoque carregado. {len(self.local_stock)} itens encontrados para o termo '{search_term}'.")
        except Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao carregar o estoque: {e}"); self.local_stock = {}

    def _on_search_typing(self, event=None): self._refresh_item_list(self.search_entry.get().strip())

    def create_widgets(self):
        self.grid_rowconfigure(0, weight=0); self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)
        self.header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0084FF"); self.header_frame.grid(row=0, column=0, sticky="nsew"); self.header_frame.grid_propagate(False); self.header_frame.grid_columnconfigure(0, weight=0); self.header_frame.grid_columnconfigure(1, weight=1)
        try:
            seta_image = ctk.CTkImage(light_image=Image.open(SETA_IMAGE_PATH).resize((30, 30), Image.LANCZOS), size=(30, 30)); self.back_btn = ctk.CTkButton(self.header_frame, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.go_to_gui1)
        except Exception: self.back_btn = ctk.CTkButton(self.header_frame, text="Voltar", font=self.header_font, fg_color="transparent", hover_color="#0066CC", text_color="white", command=self.go_to_gui1)
        self.back_btn.grid(row=0, column=0, padx=10, pady=20, sticky="w")
        ctk.CTkLabel(self.header_frame, text="Estoque", font=self.title_font, text_color="white").grid(row=0, column=1, pady=20, sticky="nsew")
        
        self.content_frame = ctk.CTkFrame(self, fg_color="#F5F5F5"); self.content_frame.grid(row=1, column=0, sticky="nsew"); self.content_frame.grid_columnconfigure(0, weight=1); self.content_frame.grid_rowconfigure(3, weight=1) 
        self.search_entry = ctk.CTkEntry(self.content_frame, placeholder_text="🔎 Pesquisar item...", font=self.item_name_font, height=40, corner_radius=10, border_width=1, border_color="#0084FF"); self.search_entry.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5)); self.search_entry.bind("<KeyRelease>", self._on_search_typing)
        
        self.action_buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent"); self.action_buttons_frame.grid(row=1, column=0, pady=(5, 10)); self.action_buttons_frame.grid_columnconfigure((0,4), weight=1) 
        try: up_arrow_image = ctk.CTkImage(light_image=Image.open(UP_ARROW_IMAGE_PATH).resize((40, 40), Image.LANCZOS), size=(40, 40))
        except: up_arrow_image = None
        try: down_arrow_image = ctk.CTkImage(light_image=Image.open(DOWN_ARROW_IMAGE_PATH).resize((40, 40), Image.LANCZOS), size=(40, 40))
        except: down_arrow_image = None
        try: mic_image = ctk.CTkImage(light_image=Image.open(MIC_IMAGE_PATH).resize((40, 40), Image.LANCZOS), size=(40, 40))
        except: mic_image = None

        self.btn_up = ctk.CTkButton(self.action_buttons_frame, text="" if up_arrow_image else "ADD", image=up_arrow_image, width=50, height=50, fg_color="#0084FF", hover_color="#0066CC", corner_radius=12, command=self.open_add_item_dialog); self.btn_up.grid(row=0, column=1, padx=10, pady=5)
        self.btn_voice = ctk.CTkButton(self.action_buttons_frame, text="" if mic_image else "VOZ", image=mic_image, width=60, height=60, fg_color="#5856D6", hover_color="#4341A7", corner_radius=30); self.btn_voice.grid(row=0, column=2, padx=10, pady=5); self.btn_voice.bind("<ButtonPress-1>", self._start_recording)
        self.btn_remove = ctk.CTkButton(self.action_buttons_frame, text="" if down_arrow_image else "REM", image=down_arrow_image, width=50, height=50, fg_color="#0084FF", hover_color="#0066CC", corner_radius=12, command=self.open_remove_item_dialog); self.btn_remove.grid(row=0, column=3, padx=10, pady=5)
        ctk.CTkLabel(self.action_buttons_frame, text="Adicionar  |  Por Voz  |  Remover", font=self.header_font, text_color="#333333").grid(row=1, column=1, columnspan=3, pady=(0,10))

        self.btn_history = ctk.CTkButton(self.content_frame, text="Histórico de Uso", height=40, fg_color="#95a5a6", hover_color="#7F8C8D", corner_radius=10, command=self.open_history_window, font=self.header_font); self.btn_history.grid(row=2, column=0, pady=(5,10), padx=20, sticky="ew")
        self.items_container = ctk.CTkScrollableFrame(self.content_frame, fg_color="#F5F5F5", corner_radius=0); self.items_container.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 2)); self.items_container.grid_columnconfigure(0, weight=1)
        self._refresh_item_list()

    def _refresh_item_list(self, search_term=""):
        self.load_stock_from_db(search_term)
        for widget in self.items_container.winfo_children(): widget.destroy()
        if not self.local_stock:
            msg = "Nenhum item encontrado." if search_term else "Seu estoque está vazio."
            ctk.CTkLabel(self.items_container, text=msg, font=self.item_name_font, text_color="#666666").pack(pady=30)
        else:
            for i, (name, data) in enumerate(self.local_stock.items()): self._add_item_widget(name, data["quantidade_produto"], data["tipo_volume"], i)
        self.items_container.update_idletasks()

    def _add_item_widget(self, name, qty, unit, row_index):
        is_low_stock = False
        try:
            numeric_qty = float(qty)
            if (unit == 'Unidades' and numeric_qty <= 2) or (unit in ['Gramas', 'Mililitros'] and numeric_qty <= 500): is_low_stock = True
        except (ValueError, TypeError): pass
        
        item_color = "#FFA500" if is_low_stock else "#0084FF"
        text_color = "#000000" if is_low_stock else "white"
        
        item_frame = ctk.CTkFrame(self.items_container, fg_color=item_color, corner_radius=12, height=60)
        item_frame.grid(row=row_index, column=0, sticky="ew", pady=5, padx=2); item_frame.grid_propagate(False)
        item_frame.grid_columnconfigure(0, weight=1); item_frame.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(item_frame, text=name, text_color=text_color, font=self.item_name_font, anchor="w").grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        formatted_qtd, display_unit = self.formatar_exibicao(qty, unit)
        qty_label = ctk.CTkLabel(item_frame, text=f"{formatted_qtd} {display_unit}", text_color=text_color, font=self.qty_font)
        qty_label.grid(row=0, column=1, padx=(5, 15), pady=10, sticky="e")
        
        for widget in item_frame.winfo_children() + [item_frame]:
            widget.bind("<Button-1>", lambda event, n=name: self._show_nutritional_info(n))

    def _center_dialog(self, dialog, width, height):
        self.update_idletasks(); parent_x = self.winfo_x(); parent_y = self.winfo_y(); parent_width = self.winfo_width(); parent_height = self.winfo_height(); center_x = parent_x + (parent_width // 2) - (width // 2); center_y = parent_y + (parent_height // 2) - (height // 2); dialog.geometry(f"{width}x{height}+{center_x}+{center_y}")

    def check_low_stock_on_startup(self):
        low_stock_items = []
        for name, data in self.local_stock.items():
            try:
                numeric_qty = float(data["quantidade_produto"]); unit = data["tipo_volume"]
                if (unit == 'Unidades' and numeric_qty <= 2) or (unit in ['Gramas', 'Mililitros'] and numeric_qty <= 500):
                    formatted_qty, display_unit = self.formatar_exibicao(numeric_qty, unit)
                    low_stock_items.append(f"- {name}: {formatted_qty} {display_unit}")
            except (ValueError, TypeError): continue
        if low_stock_items: messagebox.showwarning("Alerta de Estoque Baixo", "Itens com baixo estoque:\n\n" + "\n".join(low_stock_items))

    def open_add_item_dialog(self):
        self._refresh_item_list(); item_names = list(self.local_stock.keys())
        dialog = ctk.CTkToplevel(self); dialog.title("Adicionar Item"); dialog.resizable(False, False); dialog.transient(self); dialog.grab_set(); dialog.configure(fg_color="#FFFFFF"); self._center_dialog(dialog, 360, 320)
        
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent"); form_frame.pack(fill="both", expand=True, padx=20, pady=15); form_frame.grid_columnconfigure(1, weight=1)
        unidade_var = ctk.StringVar(value=self.measurement_units[0])
        unidade_cb = ctk.CTkComboBox(form_frame, values=self.measurement_units, variable=unidade_var, font=self.dialog_entry_font, corner_radius=8, state="readonly", width=150)
        
        def on_item_select(name):
            item_data = self.local_stock.get(name.strip().capitalize())
            if item_data:
                base_unit = item_data["tipo_volume"]
                if base_unit == "Gramas": unidade_cb.configure(values=self.mass_units); unidade_var.set(self.mass_units[0])
                elif base_unit == "Mililitros": unidade_cb.configure(values=self.volume_units); unidade_var.set(self.volume_units[0])
                else: unidade_cb.configure(values=self.unit_units); unidade_var.set(self.unit_units[0])
            else: unidade_cb.configure(values=self.measurement_units); unidade_var.set(self.measurement_units[0])
        
        ctk.CTkLabel(form_frame, text="Nome do Item:", font=self.dialog_label_font).grid(row=0, column=0, columnspan=2, sticky="w")
        nome_cb = ctk.CTkComboBox(form_frame, values=item_names, width=200, font=self.dialog_entry_font, corner_radius=8, command=on_item_select); nome_cb.grid(row=1, column=0, columnspan=2, pady=(0,10), sticky="ew"); nome_cb.bind('<KeyRelease>', lambda e: on_item_select(nome_cb.get())); nome_cb.set("")
        ctk.CTkLabel(form_frame, text="Quantidade:", font=self.dialog_label_font).grid(row=2, column=0, sticky="w", pady=5)
        qtd_entry = ctk.CTkEntry(form_frame, width=100, font=self.dialog_entry_font, corner_radius=8, validate="key", validatecommand=self.vcmd); qtd_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(form_frame, text="Unidade:", font=self.dialog_label_font).grid(row=3, column=0, sticky="w", pady=5); unidade_cb.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        def _save():
            name = nome_cb.get().strip(); qty = qtd_entry.get().strip()
            if not name or not qty: messagebox.showerror("Erro", "Preencha todos os campos.", parent=dialog); return
            self._executar_acao_db({"acao": "adicionar", "quantidade": qty, "unidade": unidade_var.get(), "item": name}); dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent"); btn_frame.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkButton(btn_frame, text="Salvar", command=_save, font=self.dialog_button_font, fg_color="#0084FF", hover_color="#0066CC").pack(side="right")
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, font=self.dialog_button_font, fg_color="#95a5a6", hover_color="#7F8C8D").pack(side="right", padx=10)
        nome_cb.focus_set()

    def open_remove_item_dialog(self):
        self._refresh_item_list()
        if not self.local_stock: messagebox.showinfo("Estoque Vazio", "Não há itens para remover."); return
        dialog = ctk.CTkToplevel(self); dialog.title("Remover Itens"); dialog.resizable(False, False); dialog.transient(self); dialog.grab_set(); dialog.configure(fg_color="#FFFFFF"); self._center_dialog(dialog, 360, 280)
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent"); form_frame.pack(fill="both", expand=True, padx=20, pady=15); form_frame.grid_columnconfigure(1, weight=1)
        
        item_names = list(self.local_stock.keys()); item_var = ctk.StringVar(value=item_names[0]); unidade_var = ctk.StringVar()
        unidade_cb = ctk.CTkComboBox(form_frame, variable=unidade_var, font=self.dialog_entry_font, state="readonly", width=150); unidade_cb.grid(row=2, column=1, sticky="w", padx=5)

        def on_item_select(name):
            unit = self.local_stock[name]["tipo_volume"]
            if unit == "Gramas": unidade_cb.configure(values=self.mass_units); unidade_var.set(self.mass_units[0])
            elif unit == "Mililitros": unidade_cb.configure(values=self.volume_units); unidade_var.set(self.volume_units[0])
            else: unidade_cb.configure(values=self.unit_units); unidade_var.set(self.unit_units[0])

        ctk.CTkLabel(form_frame, text="Item:", font=self.dialog_label_font).grid(row=0, column=0, sticky="w", pady=10)
        item_cb = ctk.CTkComboBox(form_frame, variable=item_var, values=item_names, font=self.dialog_entry_font, state="readonly", command=on_item_select); item_cb.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(form_frame, text="Quantidade:", font=self.dialog_label_font).grid(row=1, column=0, sticky="w", pady=10)
        qtd_entry = ctk.CTkEntry(form_frame, font=self.dialog_entry_font, validate="key", validatecommand=self.vcmd); qtd_entry.grid(row=1, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(form_frame, text="Unidade:", font=self.dialog_label_font).grid(row=2, column=0, sticky="w", pady=10)
        on_item_select(item_cb.get())
        
        def _remove():
            name = item_var.get(); qty = qtd_entry.get().strip()
            if not name or not qty: messagebox.showerror("Erro", "Preencha todos os campos.", parent=dialog); return
            self._executar_acao_db({"acao": "remover", "quantidade": qty, "unidade": unidade_var.get(), "item": name}); dialog.destroy()
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent"); btn_frame.pack(fill="x", padx=20, pady=(20,10))
        ctk.CTkButton(btn_frame, text="Remover", command=_remove, font=self.dialog_button_font, fg_color="#f44336", hover_color="#CC3322").pack(side="right")
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, font=self.dialog_button_font, fg_color="#95a5a6", hover_color="#7F8C8D").pack(side="right", padx=10)
        qtd_entry.focus_set()

if __name__ == "__main__":
    db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    if db_connection:
        app = InventoryApp(db_connection)
        app.mainloop()
        if app.connection and app.connection.is_connected():
            app.connection.close()
            print("Log: Conexão com o BD fechada ao finalizar o app.")

