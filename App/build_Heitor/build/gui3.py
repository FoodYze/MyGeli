import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk
import subprocess
import sys
import mysql.connector
from mysql.connector import Error
from tkinter import messagebox
import google.generativeai as genai
import json
from dotenv import load_dotenv
import os

# --- CONFIGURAÇÃO DA API KEY POR VARIÁVEL DE AMBIENTE---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Erro ao configurar a API do Google: {e}")
        messagebox.showwarning("API Key", "Não foi possível configurar a API do Google. Verifique sua chave.")
else:
    print("AVISO: A variável de ambiente GOOGLE_API_KEY não está configurada.")


def get_nutritional_info_from_api(item_name):
    """Busca informações nutricionais de um item usando a API do Google Gemini."""
    if not GOOGLE_API_KEY:
        print("API Key do Google não configurada.")
        return None
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Forneça as informações nutricionais para 100g do alimento '{item_name}'.
        Responda APENAS com um objeto JSON contendo as seguintes chaves (sem texto adicional antes ou depois):
        "valor_energetico_kcal", "acucares_totais_g", "acucares_adicionados_g", "carboidratos_g",
        "proteinas_g", "gorduras_totais_g", "gorduras_saturadas_g", "gorduras_trans_g",
        "fibra_alimentar_g", "sodio_g".
        Use o valor 0 se a informação não for encontrada ou não se aplicar. Use 'null' se for desconhecido.
        Exemplo de resposta:
        {{
          "valor_energetico_kcal": 52,
          "acucares_totais_g": 10.4,
          "acucares_adicionados_g": 0,
          "carboidratos_g": 14,
          "proteinas_g": 0.3,
          "gorduras_totais_g": 0.2,
          "gorduras_saturadas_g": 0.1,
          "gorduras_trans_g": 0,
          "fibra_alimentar_g": 2.4,
          "sodio_g": 1
        }}
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        print(f"Resposta da API para '{item_name}':\n{cleaned_response}")
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Erro ao chamar a API Gemini: {e}")
        messagebox.showerror("Erro de API", f"Não foi possível obter os dados nutricionais para '{item_name}'.\nDetalhes: {e}")
        return None

def conectar_mysql(host, database, user, password):
    """ Tenta conectar ao banco de dados MySQL. """
    try:
        conexao = mysql.connector.connect(host=host, database=database, user=user, password=password)
        if conexao.is_connected():
            print(f"Conectado ao MySQL com sucesso!")
            return conexao
    except Error as e:
        print(f"Log: Erro CRÍTICO ao conectar ao MySQL: {e}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao banco de dados:\n{e}")
        return None

# --- SUAS CREDENCIAIS ---
db_host = "localhost"
db_name = "foodyze"
db_usuario = "foodyzeadm"
db_senha = "supfood0017admx"

# --- CAMINHOS DOS ARQUIVOS ---
OUTPUT_PATH = Path(__file__).parent
SETA_IMAGE_PATH = OUTPUT_PATH / "seta.png"
UP_ARROW_IMAGE_PATH = OUTPUT_PATH / "up_arrow.png"
DOWN_ARROW_IMAGE_PATH = OUTPUT_PATH / "down_arrow.png"

class InventoryApp(ctk.CTk):
    def __init__(self, db_connection):
        super().__init__()
        self.connection = db_connection
        self.local_stock = {}
        if not self.connection:
            self.destroy()
            return
        ctk.set_appearance_mode("light")
        self.title("Estoque"); self.geometry("400x650"); self.minsize(400, 650); self.maxsize(400, 650)
        self.configure(fg_color="#F5F5F5")
        self.vcmd = (self.register(self._validate_numeric_input), '%P')
        self.setup_fonts()
        self.measurement_units = ["Unidades", "Quilos (Kg)", "Gramas (g)", "Litros (L)", "Mililitros (ml)"]
        self.mass_units = ["Gramas (g)", "Quilos (Kg)"]
        self.volume_units = ["Mililitros (ml)", "Litros (L)"]
        self.unit_units = ["Unidades"]
        self.create_widgets()

    def setup_fonts(self):
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

    def _validate_numeric_input(self, value_if_allowed):
        if value_if_allowed == "": return True
        try:
            float(value_if_allowed.replace(',', '.'))
            return True
        except ValueError:
            return False

    def converter_para_base(self, quantidade, unidade):
        unidade_lower = unidade.lower()
        if 'kg' in unidade_lower: return (float(quantidade) * 1000, 'Gramas')
        if 'g' in unidade_lower: return (float(quantidade), 'Gramas')
        if 'l' in unidade_lower: return (float(quantidade) * 1000, 'ml')
        if 'ml' in unidade_lower: return (float(quantidade), 'ml')
        if 'unidades' in unidade_lower: return (int(quantidade), 'Unidades')
        return (float(quantidade), unidade)
    
    def formatar_exibicao(self, quantidade, unidade):
        qtd_float = float(quantidade)
        if unidade == 'Gramas' and qtd_float >= 1000: return ("{:g}".format(qtd_float / 1000).replace('.', ','), "Kg")
        if unidade == 'ml' and qtd_float >= 1000: return ("{:g}".format(qtd_float / 1000).replace('.', ','), "L")
        return ("{:g}".format(qtd_float).replace('.', ','), unidade)
    
    def go_to_gui1(self):
        if self.connection and self.connection.is_connected(): self.connection.close()
        self.destroy()
        try: subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
        except Exception as e: messagebox.showerror("Erro", f"Ocorreu um erro ao tentar abrir gui1.py: {e}")

    def load_stock_from_db(self, search_term=""):
        try:
            if not self.connection.is_connected(): self.connection.reconnect()
            cursor = self.connection.cursor(dictionary=True)
            base_query = "SELECT * FROM produtos"
            if search_term:
                query = f"{base_query} WHERE nome_produto LIKE %s ORDER BY nome_produto ASC"
                cursor.execute(query, (f"%{search_term}%",))
            else:
                query = f"{base_query} ORDER BY nome_produto ASC"
                cursor.execute(query)
            self.local_stock = {product['nome_produto']: product for product in cursor.fetchall()}
            cursor.close()
        except Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao carregar o estoque: {e}")
            self.local_stock = {}

    def _try_update_nutritional_info_if_missing(self, name, cursor):
        """Verifica se um item tem dados nutricionais e tenta buscá-los se não tiver."""
        try:
            cursor.execute("SELECT valor_energetico_kcal FROM produtos WHERE nome_produto = %s", (name,))
            result = cursor.fetchone()
            # 2. Tenta buscar novamente se a informação estiver faltando (NULL no DB)
            if result and result['valor_energetico_kcal'] is None:
                print(f"Dados nutricionais faltando para '{name}'. Tentando buscar na API...")
                nutritional_data = get_nutritional_info_from_api(name)
                if nutritional_data:
                    keys = ["valor_energetico_kcal", "acucares_totais_g", "acucares_adicionados_g", "carboidratos_g", "proteinas_g", "gorduras_totais_g", "gorduras_saturadas_g", "gorduras_trans_g", "fibra_alimentar_g", "sodio_g"]
                    query = f"UPDATE produtos SET {', '.join([f'{k} = %s' for k in keys])} WHERE nome_produto = %s"
                    values = [nutritional_data.get(k) for k in keys] + [name]
                    cursor.execute(query, tuple(values))
                    self.connection.commit()
                    print(f"Dados nutricionais de '{name}' atualizados com sucesso no banco de dados.")
                    return True # Retorna True se atualizou
        except Error as e:
            print(f"Erro de BD ao tentar atualizar info nutricional para {name}: {e}")
        return False # Retorna False se não atualizou

    def _on_search_typing(self, event=None):
        self._refresh_item_list(self.search_entry.get().strip())

    def create_widgets(self):
        self.grid_rowconfigure(0, weight=0); self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0084FF"); header.grid(row=0, column=0, sticky="nsew"); header.grid_propagate(False); header.grid_columnconfigure(0, weight=0); header.grid_columnconfigure(1, weight=1)
        try:
            seta_image = ctk.CTkImage(light_image=Image.open(SETA_IMAGE_PATH).resize((30, 30), Image.LANCZOS), size=(30, 30))
            ctk.CTkButton(header, text="", image=seta_image, width=40, height=40, fg_color="transparent", hover_color="#0066CC", command=self.go_to_gui1).grid(row=0, column=0, padx=10, pady=20, sticky="w")
        except Exception: ctk.CTkButton(header, text="Voltar", command=self.go_to_gui1).grid(row=0, column=0, padx=10, sticky="w")
        ctk.CTkLabel(header, text="Estoque", font=self.title_font, text_color="white").grid(row=0, column=1, pady=20, sticky="nsew")
        
        content = ctk.CTkFrame(self, fg_color="#F5F5F5"); content.grid(row=1, column=0, sticky="nsew"); content.grid_columnconfigure(0, weight=1); content.grid_rowconfigure(2, weight=1) 
        self.search_entry = ctk.CTkEntry(content, placeholder_text="🔎 Pesquisar item...", font=self.item_name_font, height=40); self.search_entry.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5)); self.search_entry.bind("<KeyRelease>", self._on_search_typing)
        
        actions = ctk.CTkFrame(content, fg_color="transparent"); actions.grid(row=1, column=0, pady=(5, 10)); actions.grid_columnconfigure((0, 4), weight=1)
        try: up_img = ctk.CTkImage(light_image=Image.open(UP_ARROW_IMAGE_PATH).resize((40,40)), size=(40,40))
        except: up_img = None
        try: down_img = ctk.CTkImage(light_image=Image.open(DOWN_ARROW_IMAGE_PATH).resize((40,40)), size=(40,40))
        except: down_img = None
        ctk.CTkButton(actions, text="", image=up_img, width=50, height=50, fg_color="#0084FF", hover_color="#0066CC", command=self.open_add_item_dialog).grid(row=0, column=1, padx=10)
        ctk.CTkLabel(actions, text="Gerenciar Itens", font=self.header_font, text_color="#333333").grid(row=0, column=2, padx=10)
        ctk.CTkButton(actions, text="", image=down_img, width=50, height=50, fg_color="#0084FF", hover_color="#0066CC", command=self.open_remove_item_dialog).grid(row=0, column=3, padx=10)
        
        self.items_container = ctk.CTkScrollableFrame(content, fg_color="#F5F5F5"); self.items_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5); self.items_container.grid_columnconfigure(0, weight=1)
        self._refresh_item_list()

    def _refresh_item_list(self, search_term=""):
        self.load_stock_from_db(search_term)
        for widget in self.items_container.winfo_children(): widget.destroy()
        if not self.local_stock: ctk.CTkLabel(self.items_container, text="Nenhum item encontrado." if search_term else "Seu estoque está vazio.").pack(pady=30)
        else:
            for i, (name, data) in enumerate(self.local_stock.items()): self._add_item_widget(name, data["quantidade_produto"], data["tipo_volume"], i)

    def _add_item_widget(self, name, qty, unit, row_index):
        is_low = False
        try: is_low = (unit == 'Unidades' and float(qty) <= 2) or (unit in ['Gramas', 'ml'] and float(qty) <= 500)
        except: pass
        
        item_frame = ctk.CTkFrame(self.items_container, fg_color="#FFA500" if is_low else "#0084FF", height=60); item_frame.grid(row=row_index, column=0, sticky="ew", pady=5); item_frame.grid_propagate(False); item_frame.grid_columnconfigure(0, weight=1)
        name_lbl = ctk.CTkLabel(item_frame, text=name, text_color="#000" if is_low else "#FFF", font=self.item_name_font, anchor="w"); name_lbl.grid(row=0, column=0, padx=15, sticky="ew")
        
        f_qty, f_unit = self.formatar_exibicao(qty, unit)
        qty_lbl = ctk.CTkLabel(item_frame, text=f"{f_qty} {f_unit}", text_color="#000" if is_low else "#FFF", font=self.qty_font); qty_lbl.grid(row=0, column=1, padx=15, sticky="e")
        
        for widget in [item_frame, name_lbl, qty_lbl]: widget.bind("<Button-1>", lambda e, n=name: self._show_nutritional_info(n))

    def _show_nutritional_info(self, item_name):
        try:
            cursor = self.connection.cursor(dictionary=True)
            if self._try_update_nutritional_info_if_missing(item_name, cursor):
                # Se os dados foram atualizados, recarregue o estoque local para obter os novos dados
                self.load_stock_from_db(self.search_entry.get().strip())
            cursor.close()
        except Error as e:
            messagebox.showerror("Erro de BD", f"Não foi possível verificar as informações nutricionais: {e}")
            return

        item_data = self.local_stock.get(item_name)
        if not item_data: return
        
        dialog = ctk.CTkToplevel(self); dialog.title(f"Info: {item_name}"); dialog.configure(fg_color="white"); self._center_dialog(dialog, 320, 480)
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent"); main_frame.pack(pady=15, padx=20, fill="both", expand=True); main_frame.grid_columnconfigure(0, weight=3); main_frame.grid_columnconfigure(1, weight=1)

        try: title_font, table_font, legend_font = ctk.CTkFont("Arial", 14, "bold"), ctk.CTkFont("Arial", 12), ctk.CTkFont("Arial", 10, "italic")
        except: title_font, table_font, legend_font = ("Arial", 14, "bold"), ("Arial", 12), ("Arial", 10, "italic")

        ctk.CTkLabel(main_frame, text="INFORMAÇÕES NUTRICIONAIS", font=title_font, text_color="black").grid(row=0, column=0, columnspan=2, pady=(0, 5))
        ctk.CTkLabel(main_frame, text="Porção: 100g", font=table_font, text_color="gray50").grid(row=1, column=0, columnspan=2, pady=(0, 15))
        
        nutrients_map = {"Valor energético": ("valor_energetico_kcal", "kcal"), "Açúcares totais": ("acucares_totais_g", "g"), "Açúcares adicionados": ("acucares_adicionados_g", "g"), "Carboidratos": ("carboidratos_g", "g"), "Proteínas": ("proteinas_g", "g"), "Gorduras totais": ("gorduras_totais_g", "g"), "Gorduras saturadas": ("gorduras_saturadas_g", "g"), "Gorduras trans": ("gorduras_trans_g", "g"), "Fibra alimentar": ("fibra_alimentar_g", "g"), "Sódio": ("sodio_g", "g")}

        last_row = 0
        for i, (label, (db_key, unit)) in enumerate(nutrients_map.items(), start=2):
            ctk.CTkLabel(main_frame, text=label, font=table_font, text_color="black", anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            value = item_data.get(db_key)
            value_text = f"{value:.2f} {unit}" if value is not None else "*"
            ctk.CTkLabel(main_frame, text=value_text, font=table_font, text_color="black", anchor="e").grid(row=i, column=1, sticky="e", pady=2)
            last_row = i
        
        ctk.CTkLabel(main_frame, text="* informação não aplicável/indisponível", font=legend_font, text_color="gray50").grid(row=last_row + 1, column=0, columnspan=2, pady=(15, 0), sticky="w")
        dialog.after(100, dialog.lift)

    def _center_dialog(self, dialog, width, height):
        self.update_idletasks(); px, py, pw, ph = self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height(); dialog.geometry(f"{width}x{height}+{px + (pw//2) - (width//2)}+{py + (ph//2) - (height//2)}")

    def open_add_item_dialog(self):
        self._refresh_item_list()
        item_names = list(self.local_stock.keys())
        dialog = ctk.CTkToplevel(self); dialog.title("Adicionar Item"); dialog.configure(fg_color="#FFF"); self._center_dialog(dialog, 360, 270); dialog.transient(self); dialog.grab_set()
        
        form = ctk.CTkFrame(dialog, fg_color="transparent"); form.pack(fill="both", expand=True, padx=20, pady=15); form.grid_columnconfigure(1, weight=1)
        unidade_var = ctk.StringVar(value=self.measurement_units[0])
        unidade_cb = ctk.CTkComboBox(form, values=self.measurement_units, variable=unidade_var, state="readonly", width=150)
        
        def on_item_select(name):
            norm_name = name.strip().capitalize()
            if norm_name in self.local_stock:
                unit = self.local_stock[norm_name]["tipo_volume"]
                vals, default = (self.mass_units, self.mass_units[0]) if unit == "Gramas" else ((self.volume_units, self.volume_units[0]) if unit == "ml" else (self.unit_units, self.unit_units[0]))
                unidade_cb.configure(values=vals); unidade_var.set(default)
            else: unidade_cb.configure(values=self.measurement_units); unidade_var.set(self.measurement_units[0])
        
        ctk.CTkLabel(form, text="Nome do Item:", font=self.dialog_label_font).grid(row=0, column=0, columnspan=2, sticky="w")
        ctk.CTkLabel(form, text="Digite um novo nome ou selecione um existente", font=self.dialog_hint_font, text_color="#666").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0,5))
        nome_cb = ctk.CTkComboBox(form, values=item_names, command=on_item_select); nome_cb.grid(row=2, column=0, columnspan=2, pady=(0,10), sticky="ew"); nome_cb.bind('<KeyRelease>', lambda e: on_item_select(nome_cb.get())); nome_cb.set("")
        ctk.CTkLabel(form, text="Quantidade:", font=self.dialog_label_font).grid(row=3, column=0, sticky="w", pady=5)
        qtd_entry = ctk.CTkEntry(form, width=100, validate="key", validatecommand=self.vcmd); qtd_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(form, text="Unidade:", font=self.dialog_label_font).grid(row=4, column=0, sticky="w", pady=5)
        unidade_cb.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        def _save():
            name = nome_cb.get().strip().capitalize()
            qty_str = qtd_entry.get().strip().replace(',', '.')
            if not name or not qty_str: messagebox.showerror("Erro", "Todos os campos são obrigatórios.", parent=dialog); return
            try:
                if float(qty_str) <= 0: raise ValueError
            except: messagebox.showerror("Erro", "Quantidade deve ser um número positivo.", parent=dialog); return
            
            qty_base, unit_base = self.converter_para_base(float(qty_str), unidade_var.get())
            try:
                cursor = self.connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM produtos WHERE nome_produto = %s", (name,))
                result = cursor.fetchone()
                
                if result:
                    if result['tipo_volume'] != unit_base:
                        messagebox.showerror("Erro", f"Unidade incompatível para '{name}'.", parent=dialog); cursor.close(); return
                    self._try_update_nutritional_info_if_missing(name, cursor)
                    new_qty = float(result['quantidade_produto']) + qty_base
                    cursor.execute("UPDATE produtos SET quantidade_produto = %s WHERE nome_produto = %s", (new_qty, name))
                else:
                    data = get_nutritional_info_from_api(name)
                    if not data:
                        if not GOOGLE_API_KEY:
                            if not messagebox.askyesno("API Key Faltando", "Deseja adicionar o item sem informações nutricionais?", parent=dialog): return
                        else:
                             if not messagebox.askyesno("Falha na API", "Não foi possível obter dados. Adicionar mesmo assim?", parent=dialog): return
                        data = {}
                    
                    keys = ["valor_energetico_kcal", "acucares_totais_g", "acucares_adicionados_g", "carboidratos_g", "proteinas_g", "gorduras_totais_g", "gorduras_saturadas_g", "gorduras_trans_g", "fibra_alimentar_g", "sodio_g"]
                    final_data = {k: data.get(k) for k in keys}
                    query = f"INSERT INTO produtos (nome_produto, quantidade_produto, tipo_volume, {', '.join(keys)}) VALUES (%s, %s, %s, {', '.join(['%s']*len(keys))})"
                    values = (name, qty_base, unit_base) + tuple(final_data.values())
                    cursor.execute(query, values)
                
                self.connection.commit(); cursor.close(); self._refresh_item_list(); dialog.destroy()
            except Error as e: messagebox.showerror("Erro de BD", f"Falha ao salvar: {e}", parent=dialog)
        
        btns = ctk.CTkFrame(dialog, fg_color="transparent"); btns.pack(fill="x", padx=20, pady=(15,10))
        ctk.CTkButton(btns, text="Salvar", command=_save, height=35).pack(side="right")
        ctk.CTkButton(btns, text="Cancelar", command=dialog.destroy, fg_color="#f44336", hover_color="#CC3322", height=35).pack(side="right", padx=10)
        nome_cb.focus_set()

    def open_remove_item_dialog(self):
        self._refresh_item_list()
        if not self.local_stock: messagebox.showinfo("Estoque Vazio", "Não há itens para remover."); return
        dialog = ctk.CTkToplevel(self); dialog.title("Remover Itens"); dialog.configure(fg_color="#FFF"); self._center_dialog(dialog, 360, 280); dialog.transient(self); dialog.grab_set()
        
        form = ctk.CTkFrame(dialog, fg_color="transparent"); form.pack(fill="both", expand=True, padx=20, pady=15); form.grid_columnconfigure(1, weight=1)
        item_names = list(self.local_stock.keys())
        item_var = ctk.StringVar(value=item_names[0])
        unit_var = ctk.StringVar()
        unit_cb = ctk.CTkComboBox(form, variable=unit_var, state="readonly", width=150)

        def on_item_select(name):
            if name in self.local_stock:
                unit = self.local_stock[name]["tipo_volume"]
                vals, default = (self.mass_units, self.mass_units[0]) if unit == "Gramas" else ((self.volume_units, self.volume_units[0]) if unit == "ml" else (self.unit_units, self.unit_units[0]))
                unit_cb.configure(values=vals); unit_var.set(default)

        ctk.CTkLabel(form, text="Item:", font=self.dialog_label_font).grid(row=0, column=0, sticky="w", pady=10)
        item_cb = ctk.CTkComboBox(form, variable=item_var, values=item_names, state="readonly", command=on_item_select); item_cb.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        ctk.CTkLabel(form, text="Quantidade:", font=self.dialog_label_font).grid(row=1, column=0, sticky="w", pady=10)
        qtd_entry = ctk.CTkEntry(form, validate="key", validatecommand=self.vcmd); qtd_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        ctk.CTkLabel(form, text="Unidade:", font=self.dialog_label_font).grid(row=2, column=0, sticky="w", pady=10)
        unit_cb.grid(row=2, column=1, padx=5, pady=10, sticky="w"); on_item_select(item_cb.get())
        
        def _remove():
            name = item_var.get(); qty_str = qtd_entry.get().strip().replace(',', '.')
            if not qty_str: messagebox.showerror("Erro", "Insira a quantidade.", parent=dialog); return
            try:
                if float(qty_str) <= 0: raise ValueError
            except: messagebox.showerror("Erro", "Quantidade inválida.", parent=dialog); return
            
            qty_base_rem, unit_base_rem = self.converter_para_base(float(qty_str), unit_var.get())
            stock_data = self.local_stock[name]
            if stock_data["tipo_volume"] != unit_base_rem: messagebox.showerror("Erro", "Unidade incompatível.", parent=dialog); return
            if float(stock_data["quantidade_produto"]) < qty_base_rem: messagebox.showwarning("Aviso", "Qtd. insuficiente.", parent=dialog); return
            
            try:
                cursor = self.connection.cursor(dictionary=True)
                if self._try_update_nutritional_info_if_missing(name, cursor): self._refresh_item_list() # Recarrega dados se a API foi chamada
                new_qty = float(stock_data["quantidade_produto"]) - qty_base_rem
                if abs(new_qty) < 0.001: cursor.execute("DELETE FROM produtos WHERE nome_produto = %s", (name,))
                else: cursor.execute("UPDATE produtos SET quantidade_produto = %s WHERE nome_produto = %s", (new_qty, name))
                self.connection.commit(); cursor.close(); self._refresh_item_list(self.search_entry.get().strip()); dialog.destroy()
            except Error as e: messagebox.showerror("Erro de BD", f"Falha ao remover: {e}", parent=dialog)
        
        btns = ctk.CTkFrame(dialog, fg_color="transparent"); btns.pack(fill="x", padx=20, pady=(20,10))
        ctk.CTkButton(btns, text="Remover", command=_remove, fg_color="#f44336", hover_color="#CC3322", height=35).pack(side="right")
        ctk.CTkButton(btns, text="Cancelar", command=dialog.destroy, fg_color="#95a5a6", hover_color="#7F8C8D", height=35).pack(side="right", padx=10)
        if item_names: qtd_entry.focus_set()

if __name__ == "__main__":
    db_connection = conectar_mysql(db_host, db_name, db_usuario, db_senha)
    if db_connection:
        app = InventoryApp(db_connection)
        app.mainloop()
        if app.connection and app.connection.is_connected():
            app.connection.close()

