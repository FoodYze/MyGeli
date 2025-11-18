import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
from pathlib import Path
import os
from datetime import datetime, date, timedelta
import calendar
from collections import defaultdict
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, Text, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from contextlib import contextmanager
import hashlib
import re
from functools import partial

from session_manager import SessionManager

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / "assets" / "geral"

# --- CONFIGURAÇÃO DO BANCO 'mygeli' ---
DB_USER, DB_PASS, DB_HOST, DB_NAME, DB_PORT = "foodyzeadm", "supfood0017admx", "localhost", "mygeli", "3306"
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- MODELOS ---
class User(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column("nome", String(255))

class Recipe(Base):
    __tablename__ = "receitas"
    id = Column("idreceita", Integer, primary_key=True, index=True)
    title = Column("tituloreceita", String(255), nullable=False)
    description = Column("descreceita", Text) 
    user_id = Column("idusuario", Integer, ForeignKey("usuarios.id"))

class Ingredient(Base): __tablename__ = "ingredients"; id = Column(Integer, primary_key=True); name = Column(String(255), nullable=False); unit = Column(String(50))
class RecipeIngredient(Base): __tablename__ = "recipe_ingredients"; id = Column(Integer, primary_key=True); recipe_id = Column(Integer, ForeignKey("receitas.idreceita")); name = Column(String(255), nullable=False); quantity = Column(Float); unit = Column(String(50))
class MealPlan(Base): __tablename__ = "meal_plans"; id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("usuarios.id")); recipe_id = Column(Integer, ForeignKey("receitas.idreceita")); date = Column(Date, nullable=False); meal_type = Column(String(50))
class ShoppingListItem(Base): __tablename__ = "shopping_list_items"; id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("usuarios.id")); ingredient_name = Column(String(255), nullable=False); quantity = Column(Float); unit = Column(String(50))

# --- SERVIÇOS ---
def get_user_recipes(db: Session, user_id: int):
    return db.query(Recipe.id, Recipe.title).filter(Recipe.user_id == user_id).order_by(Recipe.id.desc()).all()

def get_recipe_details_by_id(db: Session, recipe_id: int):
    return db.query(Recipe.title, Recipe.description).filter(Recipe.id == recipe_id).first()

def add_recipe_to_meal_plan(db: Session, user_id: int, recipe_id: int, date_str: str, meal_type: str = "Refeição"):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    if not db.query(Recipe).filter(Recipe.id == recipe_id).first(): raise ValueError(f"Receita ID {recipe_id} não encontrada.")
    mp = MealPlan(user_id=user_id, recipe_id=recipe_id, date=date_obj, meal_type=meal_type)
    db.add(mp); db.commit(); db.refresh(mp); return mp

def remove_recipe_from_plan(db: Session, plan_id: int):
    db.query(MealPlan).filter(MealPlan.id == plan_id).delete()
    db.commit()

def get_monthly_plans(db: Session, user_id: int, year: int, month: int):
    """Retorna dados resumidos para preencher o calendário."""
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    
    plans = db.query(MealPlan.id, MealPlan.date, Recipe.title)\
        .join(Recipe, MealPlan.recipe_id == Recipe.id)\
        .filter(MealPlan.user_id == user_id, MealPlan.date >= start_date, MealPlan.date <= end_date)\
        .all()
    
    calendar_data = defaultdict(list)
    for mp_id, mp_date, title in plans:
        calendar_data[mp_date.day].append(title) # Apenas título para o calendário
    return calendar_data

def get_plans_for_specific_date(db: Session, user_id: int, target_date: date):
    """Retorna dados detalhados de um dia específico."""
    plans = db.query(MealPlan.id, Recipe.id, Recipe.title)\
        .join(Recipe, MealPlan.recipe_id == Recipe.id)\
        .filter(MealPlan.user_id == user_id, MealPlan.date == target_date)\
        .all()
    
    # Retorna lista de dicionários
    return [{'mp_id': mp_id, 'r_id': r_id, 'title': title} for mp_id, r_id, title in plans]

def parse_ingredients_from_text(text):
    if not text: return []
    ingredients = []
    try:
        if "INGREDIENTES:" in text and "PREPARO:" in text:
            block = text.split("INGREDIENTES:")[1].split("PREPARO:")[0]
        elif "INGREDIENTES:" in text:
            block = text.split("INGREDIENTES:")[1]
        else:
            block = text

        for line in block.splitlines():
            line = re.sub(r'\(.*?\)', '', line).strip()
            match = re.match(r"^\s*([\d\.,]+)\s*(\w*)\s*(?:de\s)?(.*)", line, re.IGNORECASE)
            if match:
                try:
                    qty = float(match.group(1).replace(',', '.'))
                    unit = match.group(2).strip()
                    name = match.group(3).strip()
                    if not name: name = unit; unit = "un"
                    ingredients.append({"name": name, "quantity": qty, "unit": unit})
                except: continue
    except Exception as e:
        print(f"Erro ao parsear texto: {e}")
    return ingredients

def generate_shopping_list_range(db: Session, user_id: int, start_date: date, end_date: date):
    meal_plans = db.query(MealPlan).filter(MealPlan.user_id == user_id, MealPlan.date >= start_date, MealPlan.date <= end_date).all()
    if not meal_plans: return {}

    aggregated = defaultdict(lambda: {"quantity": 0.0, "unit": None})
    
    for mp in meal_plans:
        sql_ingredients = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == mp.recipe_id).all()
        items_to_process = []
        if sql_ingredients:
            for i in sql_ingredients: 
                items_to_process.append({"name": i.name, "quantity": i.quantity, "unit": i.unit})
        else:
            recipe = db.query(Recipe).filter(Recipe.id == mp.recipe_id).first()
            if recipe and recipe.description:
                items_to_process = parse_ingredients_from_text(recipe.description)

        for item in items_to_process:
            name = item["name"].strip().capitalize()
            qty = item["quantity"] or 0.0
            unit = item["unit"] or ""
            
            if aggregated[name]["unit"] in (None, "", unit):
                aggregated[name]["quantity"] += float(qty)
                aggregated[name]["unit"] = unit
            else:
                aggregated[name]["quantity"] += float(qty)
                if not aggregated[name]["unit"]: aggregated[name]["unit"] = unit

    db.query(ShoppingListItem).filter(ShoppingListItem.user_id == user_id).delete()
    items = [ShoppingListItem(user_id=user_id, ingredient_name=name, quantity=info["quantity"] or None, unit=info["unit"] or None) for name, info in aggregated.items()]
    db.add_all(items); db.commit()
    return {itm.ingredient_name: {"quantity": itm.quantity, "unit": itm.unit} for itm in items}

# --- INTERFACE GRÁFICA ---
class PlanningApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.user_id = None
        self.selected_recipe_id = None 
        self.selected_recipe_title = None
        self.recipe_popup = None
        self.shopping_popup = None
        self.day_detail_popup = None # Referência para o popup do dia
        self.cal_date = datetime.now()
        
        if not self._validar_sessao():
            messagebox.showerror("Erro", "Sessão inválida.")
            self.destroy(); return
            
        self.title("MyGeli - Planejamento")
        ctk.set_appearance_mode("light")
        w, h = 1000, 750
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth() - w) // 2}+{(self.winfo_screenheight() - h) // 2}")
        self.minsize(900, 650)
        
        self.create_widgets()
        self.load_recipes_sidebar()
        self.render_calendar()

    def _validar_sessao(self):
        token_data = self.session_manager.get_token()
        if not token_data: return False
        try:
            with engine.connect() as connection:
                query = text("SELECT user_id, hashed_token, expires FROM login_tokens WHERE selector = :selector")
                result = connection.execute(query, {"selector": token_data.get("selector")}).fetchone()
                if not result or result[2] < datetime.now(): return False
                if hashlib.sha256(token_data.get("authenticator").encode()).hexdigest() == result[1]:
                    self.user_id = result[0]; return True
        except: pass
        return False

    def go_to_gui1(self):
        self.destroy()
        subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])

    def create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(0, weight=0)

        # Header
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#0084FF")
        header.grid(row=0, column=0, columnspan=2, sticky="new")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(header, text="<", command=self.go_to_gui1, width=40, font=("Arial", 22, "bold"), fg_color="transparent", hover_color="#0066CC").grid(row=0, column=0, padx=10, pady=15)
        ctk.CTkLabel(header, text="Planejamento de Refeições", font=("Arial", 22, "bold"), text_color="white").grid(row=0, column=1, sticky="ew")
        
        # Sidebar
        self.sidebar_frame = ctk.CTkScrollableFrame(self, width=250, corner_radius=0, label_text="Suas Receitas", label_font=("Arial", 14, "bold"))
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=0)
        
        # Conteúdo Principal
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)
        self.main_content.grid_rowconfigure(2, weight=1) 
        self.main_content.grid_columnconfigure(0, weight=1)
        
        # Painel Adição
        add_frame = ctk.CTkFrame(self.main_content, corner_radius=10, fg_color="white")
        add_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(add_frame, text="Adicionar ao Calendário", font=("Arial", 14, "bold")).pack(pady=(10, 2))
        self.selected_recipe_lbl = ctk.CTkLabel(add_frame, text="Selecione uma receita na barra lateral", font=("Arial", 12, "italic"), text_color="gray")
        self.selected_recipe_lbl.pack(pady=2)
        form = ctk.CTkFrame(add_frame, fg_color="transparent"); form.pack(pady=10)
        self.date_entry = ctk.CTkEntry(form, placeholder_text="AAAA-MM-DD", width=120); self.date_entry.pack(side="left", padx=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkButton(form, text="Agendar", fg_color="#0084FF", width=100, command=self.add_to_plan).pack(side="left", padx=5)

        # Controles
        cal_ctrl = ctk.CTkFrame(self.main_content, fg_color="transparent")
        cal_ctrl.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        ctk.CTkButton(cal_ctrl, text="<", width=40, command=self.prev_month, fg_color="#555").pack(side="left")
        self.lbl_month_year = ctk.CTkLabel(cal_ctrl, text="Mês Ano", font=("Arial", 18, "bold"), text_color="#333")
        self.lbl_month_year.pack(side="left", expand=True)
        ctk.CTkButton(cal_ctrl, text=">", width=40, command=self.next_month, fg_color="#555").pack(side="right")

        # Grid
        self.calendar_grid = ctk.CTkFrame(self.main_content, fg_color="white", border_width=1, border_color="#ccc")
        self.calendar_grid.grid(row=2, column=0, sticky="nsew")
        for i in range(7): self.calendar_grid.grid_columnconfigure(i, weight=1, uniform="col")
        self.calendar_grid.grid_rowconfigure(0, weight=0)
        for i in range(1, 7): self.calendar_grid.grid_rowconfigure(i, weight=1, uniform="row")

        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        for i, d in enumerate(days):
            lbl = ctk.CTkLabel(self.calendar_grid, text=d, font=("Arial", 11, "bold"), text_color="#555", fg_color="#f0f0f0", corner_radius=4)
            lbl.grid(row=0, column=i, sticky="ew", padx=1, pady=1)

        # Botão Compras
        ctk.CTkButton(self.main_content, text="🛒 LISTA DE COMPRAS (MÊS ATUAL)", height=45, font=("Arial", 15, "bold"), fg_color="#27ae60", hover_color="#219150", command=self.open_shopping_list_popup).grid(row=3, column=0, sticky="ew", pady=(15, 0))

    def load_recipes_sidebar(self):
        for w in self.sidebar_frame.winfo_children(): w.destroy()
        try:
            with get_db() as db:
                recipes = get_user_recipes(db, self.user_id)
            if not recipes:
                ctk.CTkLabel(self.sidebar_frame, text="Sem receitas.", text_color="gray").pack(pady=10); return
            for r_id, r_title in recipes:
                btn = ctk.CTkButton(self.sidebar_frame, text=r_title, anchor="w", fg_color="transparent", text_color="black", hover_color="#D6E4FF", command=partial(self.select_recipe, r_id, r_title))
                btn.pack(fill="x", pady=2, padx=5)
        except: pass

    def select_recipe(self, r_id, r_title):
        self.selected_recipe_id = r_id
        self.selected_recipe_title = r_title
        self.selected_recipe_lbl.configure(text=f"Selecionado: {r_title}", text_color="#0084FF", font=("Arial", 12, "bold"))

    def render_calendar(self):
        for w in self.calendar_grid.winfo_children():
            if int(w.grid_info()["row"]) > 0: w.destroy()

        year, month = self.cal_date.year, self.cal_date.month
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.lbl_month_year.configure(text=f"{meses[month]} {year}")

        try:
            with get_db() as db: plans = get_monthly_plans(db, self.user_id, year, month)
        except: plans = {}

        cal = calendar.monthcalendar(year, month)
        today = date.today()

        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day == 0: continue
                is_today = (day == today.day and month == today.month and year == today.year)
                
                # Frame do Dia - Clicável
                d_frame = ctk.CTkFrame(self.calendar_grid, fg_color="#E8F0FE" if is_today else "white", border_width=1, border_color="#0084FF" if is_today else "#eeeeee", corner_radius=0)
                d_frame.grid(row=r+1, column=c, sticky="nsew", padx=1, pady=1)
                
                # Número
                ctk.CTkLabel(d_frame, text=str(day), font=("Arial", 10, "bold" if is_today else "normal"), text_color="#0084FF" if is_today else "#333").pack(anchor="nw", padx=3, pady=0)
                
                # Conteúdo resumido
                if day in plans:
                    # Mostra até 3 itens como preview
                    for title in plans[day][:3]: 
                        short = (title[:8] + '..') if len(title) > 8 else title
                        ctk.CTkLabel(d_frame, text=f"• {short}", font=("Arial", 9), text_color="#2d3436", anchor="w").pack(fill="x", padx=2)
                    if len(plans[day]) > 3:
                        ctk.CTkLabel(d_frame, text=f"+ {len(plans[day])-3} ver todos", font=("Arial", 8, "bold"), text_color="#0084FF").pack(anchor="se", padx=2)
                
                # Ao clicar no dia, abre popup de detalhes
                cmd_open = partial(self.open_day_details, year, month, day)
                d_frame.bind("<Button-1>", cmd_open)
                # Bind recursivo para garantir que clicar no texto também abra
                for child in d_frame.winfo_children(): child.bind("<Button-1>", cmd_open)

    def open_day_details(self, year, month, day, event=None):
        """Abre um popup com a lista completa e botões de ação."""
        # Preenche o campo de data automaticamente ao clicar
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, f"{year}-{month:02d}-{day:02d}")
        
        target_date = date(year, month, day)
        
        try:
            with get_db() as db:
                day_plans = get_plans_for_specific_date(db, self.user_id, target_date)
            
            if not day_plans: return # Se não tem nada, não abre popup, só preenche a data

            if self.day_detail_popup and self.day_detail_popup.winfo_exists(): self.day_detail_popup.destroy()
            
            self.day_detail_popup = ctk.CTkToplevel(self)
            self.day_detail_popup.title(f"Refeições do Dia {day}/{month}")
            self.day_detail_popup.geometry("400x500")
            
            # Configurações de Popup
            self.day_detail_popup.transient(self)
            self.day_detail_popup.lift()
            self.day_detail_popup.attributes("-topmost", True)
            self.day_detail_popup.grab_set()
            
            # Centralizar
            x = self.winfo_x() + 100; y = self.winfo_y() + 100
            self.day_detail_popup.geometry(f"+{x}+{y}")
            
            ctk.CTkLabel(self.day_detail_popup, text=f"Menu de {day}/{month}/{year}", font=("Arial", 16, "bold")).pack(pady=15)
            
            scroll = ctk.CTkScrollableFrame(self.day_detail_popup, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=10, pady=10)
            
            for item in day_plans:
                row = ctk.CTkFrame(scroll, fg_color="white", corner_radius=8, border_width=1, border_color="#ddd")
                row.pack(fill="x", pady=5)
                
                # Nome Clicável
                lbl = ctk.CTkLabel(row, text=item['title'], font=("Arial", 12, "bold"), text_color="#0084FF", anchor="w", cursor="hand2")
                lbl.pack(side="left", padx=10, pady=10, fill="x", expand=True)
                lbl.bind("<Button-1>", partial(self.view_recipe_details, item['r_id']))
                
                # Botão Excluir
                btn = ctk.CTkButton(row, text="×", width=30, height=30, font=("Arial", 14, "bold"), fg_color="#ff5e57", hover_color="#ff3b30", text_color="white", 
                                    command=partial(self.delete_plan_from_popup, item['mp_id'], year, month, day))
                btn.pack(side="right", padx=10)

            ctk.CTkButton(self.day_detail_popup, text="Fechar", command=self.day_detail_popup.destroy, fg_color="#555").pack(pady=10)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir detalhes: {e}")

    def delete_plan_from_popup(self, mp_id, year, month, day):
        """Deleta e atualiza tanto o calendário quanto o popup."""
        if messagebox.askyesno("Confirmar", "Remover esta receita do dia?"):
            try:
                with get_db() as db:
                    remove_recipe_from_plan(db, mp_id)
                
                # Atualiza o fundo (calendário)
                self.render_calendar()
                
                # Reabre/Atualiza o popup para mostrar que sumiu (simplesmente chamando de novo)
                # Se for o último item, o popup pode fechar ou ficar vazio.
                self.open_day_details(year, month, day)
                
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível remover: {e}")

    def view_recipe_details(self, recipe_id, event=None):
        try:
            with get_db() as db:
                data = get_recipe_details_by_id(db, recipe_id)
            
            if not data: return
            title, desc = data
            
            if self.recipe_popup and self.recipe_popup.winfo_exists(): self.recipe_popup.destroy()
            self.recipe_popup = ctk.CTkToplevel(self)
            self.recipe_popup.geometry("500x600")
            self.recipe_popup.title(title)
            self.recipe_popup.transient(self); self.recipe_popup.lift(); self.recipe_popup.attributes("-topmost", True); self.recipe_popup.grab_set()
            
            x = self.winfo_x() + 50; y = self.winfo_y() + 50
            self.recipe_popup.geometry(f"+{x}+{y}")
            
            ctk.CTkLabel(self.recipe_popup, text=title, font=("Arial", 18, "bold"), text_color="#0084FF", wraplength=450).pack(pady=15)
            sf = ctk.CTkScrollableFrame(self.recipe_popup, fg_color="transparent")
            sf.pack(fill="both", expand=True, padx=10, pady=5)
            ctk.CTkLabel(sf, text=desc, font=("Arial", 14), justify="left", anchor="w", wraplength=430).pack()
            ctk.CTkButton(self.recipe_popup, text="Fechar", command=self.recipe_popup.destroy).pack(pady=15)
            
        except Exception as e: messagebox.showerror("Erro", f"{e}")

    def on_day_click(self, y, m, d, e):
        # Esta função agora é chamada apenas para preencher a data se o dia estiver VAZIO.
        # Se tiver receitas, o `open_day_details` assume.
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, f"{y}-{m:02d}-{d:02d}")

    def prev_month(self):
        self.cal_date = (self.cal_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        self.render_calendar()

    def next_month(self):
        next_m = self.cal_date.replace(day=28) + timedelta(days=4)
        self.cal_date = next_m.replace(day=1)
        self.render_calendar()

    def add_to_plan(self):
        if not self.selected_recipe_id:
            messagebox.showwarning("Aviso", "Selecione uma receita primeiro."); return
        try:
            with get_db() as db: 
                add_recipe_to_meal_plan(db, self.user_id, self.selected_recipe_id, self.date_entry.get())
            self.render_calendar()
        except Exception as e: messagebox.showerror("Erro", f"{e}")

    def open_shopping_list_popup(self):
        year, month = self.cal_date.year, self.cal_date.month
        start, end = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        try:
            with get_db() as db:
                shopping_list = generate_shopping_list_range(db, self.user_id, start, end)
            if self.shopping_popup and self.shopping_popup.winfo_exists(): self.shopping_popup.destroy()
            self.shopping_popup = ctk.CTkToplevel(self)
            self.shopping_popup.geometry("400x500")
            self.shopping_popup.title("Lista de Compras")
            self.shopping_popup.transient(self); self.shopping_popup.lift(); self.shopping_popup.attributes("-topmost", True); self.shopping_popup.grab_set()
            x = self.winfo_x() + 50; y = self.winfo_y() + 50
            self.shopping_popup.geometry(f"+{x}+{y}")
            ctk.CTkLabel(self.shopping_popup, text=f"Compras - {month}/{year}", font=("Arial", 16, "bold")).pack(pady=15)
            txt = ctk.CTkTextbox(self.shopping_popup, font=("Arial", 14))
            txt.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            content = "Nada planejado." if not shopping_list else "\n".join([f"- {k}: {v['quantity']:.1f} {v['unit']}" for k, v in shopping_list.items()])
            txt.insert("0.0", content); txt.configure(state="disabled")
            ctk.CTkButton(self.shopping_popup, text="Fechar", command=self.shopping_popup.destroy).pack(pady=(0,15))
        except Exception as e: messagebox.showerror("Erro", f"{e}")

if __name__ == "__main__":
    PlanningApp().mainloop()