from supabase import create_client
from hashlib import sha256
import os

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Função para verificar se o usuário já existe
def verificar_usuario_existe(usuario):
    response = supabase.table('usuarios').select('id').eq('usuario', usuario).execute()
    return len(response.data) > 0

# Função para cadastrar usuário
def cadastrar_usuario(usuario, senha):
    try:
        hash_senha = sha256(senha.encode()).hexdigest()
        response = supabase.table("usuarios").insert({
            "usuario": usuario,
            "senha": hash_senha
        }).execute()
        return True
    except Exception as e:
        print("Erro ao cadastrar usuário:", e)
        return False

# Função de login
def verificar_login(usuario, senha):
    response = supabase.table('usuarios').select('id').eq('usuario', usuario).eq('senha', senha).execute()
    return len(response.data) > 0
