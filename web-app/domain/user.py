# Cole este código em domain/user.py
import json
class User:
    def __init__(self, user_id, name, phone, email, password_hash, preferences_json=None):
        if not name or not email:
            raise ValueError("Nome e E-mail são campos obrigatórios.")
        
        self.user_id = user_id
        self.name = name
        self.phone = phone
        self.email = email
        self.password_hash = password_hash 

        if preferences_json:
            self.preferences = json.loads(preferences_json)
        else:
            self.preferences = {'allergies': '', 'dietary_restrictions': '', 'other': ''}