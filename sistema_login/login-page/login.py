from flask import Flask, request, redirect, session, make_response, abort, render_template, send_from_directory
from werkzeug.security import check_password_hash
import mysql.connector import errorcode
import os
import hashlib
from datetime import datetime, timedelta

# Configurando banco de dados
DB_CONFIG = {
  'host': 'localhost',
  'user': 'foodyzeadm',
  'password': 'supfood0017admx',
  'database': 'mygeli',
  'raise_on_warnings': True,
  'autocommit': False
}

REMEMBER_DAYS = 30

class UserLoginService:
  def __init__(self, db_config):
    self.db_config = db_config

  def get_db_connection(self):
    # Estabelecer e retornar a conexão com o banco de dados
    try:
      return mysql.connector.connect(**self.db_config)
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        raise RunTimeError("Erro de autenticação no banco de dados.")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        raise RunTimeError("Banco de dados não existe.")
      else:
        raise RunTimeError(f"Erro inesperado de banco: {err}")

  def _create_remember_token(self):
    # Gerar um token persistente para "Lembrar de mim"
    try:
      selector = os.urandom(16).hex()
      authenticator = os.urandom(32).hex()
      hashed_authenticator = hashlib.sha256(authenticator.encode()).hexdigest()
      return selector, authenticator, hashed_authenticator
    except Exception as e:
      raise RunTimeError(f"Erro ao criar token: {e}")

  def _save_remember_token(self, user_id, selector, hashed_authenticator):
    # Salvar o token de Login persistente no banco de dados
    expires_dt = datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
    expires_str = expires_dt.strftime('%Y-%m-%d %H:%M:%S')

    cnx = self.get_db_connection()
    cursor = cnx.cursor()
    try:
      cursor.execute(
        "INSERT INTO login_tokens (user_id, selector, hashed_token, expires) VALUES (%s, $s, $s, $s)",
        (user_id, selector, hashed_authenticator, expires_str)
      )
      cnx.commit()
      return selector, hashed_authenticator, expires_dt
    except mysql.connector.Error as e:
      cnx.rollback()
      raise RunTimeError(f"Erro ao salvar token de login: {e}")
    finally:
      cursor.close()
      cnx.close()

  def authenticate_user(self, email, senha, lembrar=False):
    # Autenticar o usuário com email e senha. Se 'lembrar' for True, gera e salva um token de login persistente
    cnx = self.get_db_connection()
    cursor = cnx.cursor(dictionary=True) # Retornar resultados como dicionário

    try:
      # Buscar o usuário pelo e-mail
      query = "SELECT id, email, senha FROM usuarios WHERE email = %s"
      cursor.execute(query, (email,))
      user = cursor.fetchone()

      if not user or not check_password_hash(user['senha'], senha):
        raise ValueError("E-mail ou senha inválidos.")

      # Se a autenticação for be-sucedida
      user_id = user['id']
      result = {"user_id": user_id}

      # Tratar o login persistente (lembrar de mim)
      if lembrar:
        # Token gerado aqui é temporário e deve ser salvo
        selector, authenticator, hashed_authenticator = self._create_remember_token()
        # A função ._save_remember_token retornará o 'authenticator'
        self._save_remember_token(user_id, selector, hashed_authenticator)
        result.update({
          "remember_selector": selector,
          "remember_authenticator": authenticator,
          "remember_expires": datetime.utcnow() + timedelta(days=REMEMBER_DAYS)
        })

      return result

    except ValueError as ve:
      raise ve
    except mysql.connector.Error as e:
      raise RunTimeError(f"Erro ao autenticar usuário: {e}")
    finally:
      cursor.close()
      cnx.close()
