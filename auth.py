import hashlib
import json
import os

USER_DATA_DIR = "userdata"
USERS_FILE = os.path.join(USER_DATA_DIR, "users.json")

def ensure_userdata_dir():
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)

def load_users():
    ensure_userdata_dir()
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    ensure_userdata_dir()
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    users = load_users()
    if username in users:
        return False, "Usuário já existe"
    
    users[username] = {
        'password': hash_password(password),
        'created_at': str(os.path.getctime(USERS_FILE)) # Dummy timestamp logic
    }
    save_users(users)
    init_user_env(username)
    return True, "Usuário criado com sucesso!"

def authenticate(username, password):
    users = load_users()
    if username not in users:
        return False
    
    if users[username]['password'] == hash_password(password):
        return True
    return False

def init_user_env(username):
    """Cria pasta isolada para o usuário."""
    user_path = os.path.join(USER_DATA_DIR, username)
    if not os.path.exists(user_path):
        os.makedirs(user_path)
