import os
from supabase import create_client, Client
from dotenv import load_dotenv
import bcrypt

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def verificar_login(usuario, senha):
    response = supabase.table('usuarios').select('*').eq('usuario', usuario).execute()
    data = response.data
    if data and bcrypt.checkpw(senha.encode(), data[0]['senha'].encode()):
        return True
    return False

def cadastrar_usuario(usuario, senha):
    hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    try:
        response = supabase.table("usuarios").insert({
            "usuario": usuario,
            "senha": hashed
        }).execute()
        return True
    except Exception as e:
        print("Erro ao cadastrar usuário:", e)
        return False
