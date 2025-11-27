import psycopg2
from psycopg2.extras import RealDictCursor
import os
import hashlib

def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        return conn
    except Exception as e:
        print(f"Error BD: {e}")
        return None

def validar_login(email, password):
    """
    Verifica credenciales y devuelve: id, nombre, email, saldo y ROL.
    """
    conn = get_db_connection()
    if not conn: return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Consulta optimizada: Trae el nombre del rol directamente
        sql = """
            SELECT 
                u.id_usuario, 
                u.email, 
                u.nombre, 
                s.saldo_actual, 
                r.nombre as nombre_rol
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE u.email = %s AND u.password_hash = %s AND u.activo = true
        """
        cursor.execute(sql, (email, pass_hash))
        usuario = cursor.fetchone() # Devuelve un diccionario o None
        
        cursor.close()
        conn.close()
        return usuario
        
    except Exception as e:
        print(f"Error en validación de login: {e}")
        if conn: conn.close()
        return None

# ... (Aquí irían tus funciones de registrar_usuario y get_user_balance que ya tienes)
