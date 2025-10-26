# gui5_planejamento.py

import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
from pathlib import Path
from PIL import Image
import os
from datetime import datetime
from collections import defaultdict
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, Text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

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

# --- MODELOS (Mapeados para o seu mygeli.sql) ---
class User(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column("nome", String(255))

class Recipe(Base):
    __tablename__ = "receitas"
    id = Column("idreceita", Integer, primary_key=True, index=True)
    title = Column("tituloreceita", String(255), nullable=False)
    user_id = Column("idusuario", Integer, ForeignKey("usuarios.id"))

# --- NOVAS TABELAS ---
class Ingredient(Base): __tablename__ = "ingredients"; id = Column(Integer, primary_key=True); name = Column(String(255), nullable=False); unit = Column(String(50))
class RecipeIngredient(Base): __tablename__ = "recipe_ingredients"; id = Column(Integer, primary_key=True); recipe_id = Column(Integer, ForeignKey("receitas.idreceita")); name = Column(String(255), nullable=False); quantity = Column(Float); unit = Column(String(50))
class MealPlan(Base): __tablename__ = "meal_plans"; id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("usuarios.id")); recipe_id = Column(Integer, ForeignKey("receitas.idreceita")); date = Column(Date, nullable=False); meal_type = Column(String(50))
class ShoppingListItem(Base): __tablename__ = "shopping_list_items"; id = Column(Integer, primary_key=True); user_id = Column(Integer, ForeignKey("usuarios.id")); ingredient_name = Column(String(255), nullable=False); quantity = Column(Float); unit = Column(String(50))

# --- SERVIÇOS (Lógica de Negócio) ---
def add_recipe_to_meal_plan(db: Session, user_id: int, recipe_id: int, date_str: str, meal_type: str = "Jantar"):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    if not db.query(Recipe).filter(Recipe.id == recipe_id).first(): raise ValueError(f"Receita ID {recipe_id} não encontrada.")
    if not db.query(User).filter(User.id == user_id).first(): raise ValueError(f"Usuário ID {user_id} não encontrado.")
    mp = MealPlan(user_id=user_id, recipe_id=recipe_id, date=date_obj, meal_type=meal_type)
    db.add(mp); db.commit(); db.refresh(mp); return mp

def generate_shopping_list(db: Session, user_id: int, start_date=None, end_date=None):
    q = db.query(MealPlan).filter(MealPlan.user_id == user_id)
    if start_date: q = q.filter(MealPlan.date >= start_date)
    if end_date: q = q.filter(MealPlan.date <= end_date)
    meal_plans = q.all()
    if not meal_plans: return {}
    aggregated = defaultdict(lambda: {"quantity": 0.0, "unit": None})
    for mp in meal_plans:
        for ri in db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == mp.recipe_id).all():
            name, qty, unit = ri.name.strip().lower(), ri.quantity or 0.0, ri.unit or ""
            if aggregated[name]["unit"] in (None, "", unit):
                aggregated[name]["quantity"] += float(qty)
                aggregated[name]["unit"] = unit
            else:
                aggregated[name]["quantity"] += float(qty)
                aggregated[name]["unit"] = (aggregated[name]["unit"] + " | " + unit) if aggregated[name]["unit"] else unit
    db.query(ShoppingListItem).filter(ShoppingListItem.user_id == user_id).delete()
    items = [ShoppingListItem(user_id=user_id, ingredient_name=name, quantity=info["quantity"] or None, unit=info["unit"] or None) for name, info in aggregated.items()]
    db.add_all(items); db.commit()
    return {itm.ingredient_name.capitalize(): {"quantity": itm.quantity, "unit": itm.unit} for itm in items}

# --- INTERFACE GRÁFICA ---
class PlanningApp(ctk.CTk):
    def __init__(self):
        super().__init__(); self.title("MyGeli - Planejamento"); ctk.set_appearance_mode("light")
        w, h = 400, 650; self.geometry(f"{w}x{h}+{(self.winfo_screenwidth() - w) // 2}+{(self.winfo_screenheight() - h) // 2}"); self.minsize(w, h)
        self.create_widgets()
    def go_to_gui1(self):
        self.destroy(); subprocess.Popen([sys.executable, str(OUTPUT_PATH / "gui1.py")])
    def create_widgets(self):
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0084FF"); header.grid(row=0, column=0, sticky="new")
        ctk.CTkButton(header, text="<", command=self.go_to_gui1, width=40, font=ctk.CTkFont("Arial", 22, "bold"), fg_color="transparent", hover_color="#0066CC").grid(row=0, column=0, padx=10)
        ctk.CTkLabel(header, text="Planejamento", font=ctk.CTkFont("Arial", 22, "bold"), text_color="white").grid(row=0, column=1, sticky="ew")
        main = ctk.CTkFrame(self, fg_color="transparent"); main.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        header.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(1, weight=1); self.grid_columnconfigure(0, weight=1)
        plan_frame = ctk.CTkFrame(main, corner_radius=10); plan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(plan_frame, text="ADICIONAR RECEITA AO PLANO", font=ctk.CTkFont("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        self.user_id_entry = ctk.CTkEntry(plan_frame, placeholder_text="ID Usuário (Ex: 1 para Marvin)"); self.user_id_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.recipe_id_entry = ctk.CTkEntry(plan_frame, placeholder_text="ID Receita (Ex: 1)"); self.recipe_id_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.date_entry = ctk.CTkEntry(plan_frame, placeholder_text="Data (AAAA-MM-DD)"); self.date_entry.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(plan_frame, text="Adicionar ao Plano", font=ctk.CTkFont("Arial", 16, "bold"), command=self.add_to_plan).grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        shop_frame = ctk.CTkFrame(main, corner_radius=10); shop_frame.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(1, weight=1); shop_frame.grid_rowconfigure(1, weight=1); shop_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(shop_frame, text="Gerar Lista de Compras para o Usuário", font=ctk.CTkFont("Arial", 16, "bold"), command=self.generate_list).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.shopping_list_display = ctk.CTkTextbox(shop_frame, state="disabled", corner_radius=8, font=ctk.CTkFont("Arial", 12)); self.shopping_list_display.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
    def add_to_plan(self):
        try:
            with get_db() as db: add_recipe_to_meal_plan(db, int(self.user_id_entry.get()), int(self.recipe_id_entry.get()), self.date_entry.get())
            messagebox.showinfo("Sucesso", f"Receita adicionada ao plano!")
        except Exception as e: messagebox.showerror("Erro", f"Não foi possível adicionar ao plano:\n{e}")
    def generate_list(self):
        try:
            with get_db() as db: shopping_list = generate_shopping_list(db, int(self.user_id_entry.get()))
            self.shopping_list_display.configure(state="normal"); self.shopping_list_display.delete("1.0", "end")
            text = "Sua lista de compras:\n\n" + "\n".join([f"- {i}: {d['quantity']} {d['unit'] or ''}" for i, d in shopping_list.items()]) if shopping_list else "Plano semanal vazio para este usuário."
            self.shopping_list_display.insert("1.0", text); self.shopping_list_display.configure(state="disabled")
        except Exception as e: messagebox.showerror("Erro", f"Não foi possível gerar a lista:\n{e}")

if __name__ == "__main__":
    PlanningApp().mainloop()