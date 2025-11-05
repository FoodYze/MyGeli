import mysql.connector
from mysql.connector import errorcode

# Movido de data/db_connection.py para cá, pois é um detalhe de infraestrutura
class MySQLConnection:
    def __init__(self, host, user, password, database):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'raise_on_warnings': True,
            'autocommit': False  # Importante para controle de transação (commit/rollback)
        }

    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                raise RuntimeError("Erro de autenticação no banco de dados.")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                raise RuntimeError("Banco de dados não existe.")
            else:
                raise RuntimeError(f"Erro inesperado de banco: {err}")

class AuthRepository:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_user_by_email(self, email):
        cnx = self.db.get_connection()
        # dictionary=True é útil para acessar colunas pelo nome (ex: user['senha'])
        cursor = cnx.cursor(dictionary=True)
        try:
            query = "SELECT id, email, senha FROM usuarios WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            return user
        finally:
            cursor.close()
            cnx.close()
    
    def insert_new_user(self, name, phone, email, password_hash):
        cnx = self.db.get_connection()
        cursor = cnx.cursor()
        try:
            query = "INSERT INTO usuarios (nome, telefone, email, senha) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (name, phone, email, password_hash))
            cnx.commit()  # Efetiva a transação
            return cursor.lastrowid
        except mysql.connector.Error as e:
            cnx.rollback() # Desfaz a transação em caso de erro
            raise e
        finally:
            cursor.close()
            cnx.close()

class UserProfileRepository:
    def __init__(self, db_connection):
        self.db = db_connection

    def get_user_details_by_id(self, user_id):
        cnx = self.db.get_connection()
        cursor = cnx.cursor(dictionary=True)
        try:
            query = "SELECT nome, email, preferencias FROM usuarios WHERE id = %s"
            cursor.execute(query, (user_id,))
            user_data = cursor.fetchone()
            return user_data
        finally:
            cursor.close()
            cnx.close()

    def update_user_preferences(self, user_id, preferences_json):
        cnx = self.db.get_connection()
        cursor = cnx.cursor()
        try:
            query = "UPDATE usuarios SET preferencias = %s WHERE id = %s"
            cursor.execute(query, (preferences_json, user_id))
            cnx.commit()
        except mysql.connector.Error as e:
            cnx.rollback()
            raise RuntimeError(f"Erro ao atualizar preferências: {e}")
        finally:
            cursor.close()
            cnx.close()