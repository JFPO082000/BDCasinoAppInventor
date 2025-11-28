import psycopg2
from psycopg2.extras import RealDictCursor
import os
# --- CAMBIO IMPORTANTE: Usamos passlib con Argon2 ---
from passlib.context import CryptContext

# Configuración idéntica a tu otro proyecto
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- CONEXIÓN ---
def get_db_connection():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: Falta DATABASE_URL")
            return None
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")
        return None

# --- REGISTRO (CON ARGON2) ---
def registrar_usuario_nuevo(datos):
    conn = get_db_connection()
    if not conn:
        return {"exito": False, "mensaje": "Error de conexión"}
    
    try:
        cursor = conn.cursor()
        
        # 1. Hashear con Argon2 (Compatible con tu otro sistema)
        pass_hash = pwd_context.hash(datos['password'])
        
        # 2. Insertar Usuario
        sql_usuario = """
            INSERT INTO Usuario (id_rol, nombre, apellido, curp, email, password_hash, fecha_registro, activo)
            VALUES (
                (SELECT id_rol FROM Rol WHERE nombre = 'Jugador'), 
                %s, %s, %s, %s, %s, NOW(), true
            )
            RETURNING id_usuario;
        """
        cursor.execute(sql_usuario, (
            datos['nombre'], 
            datos['apellido'], 
            datos['curp'], 
            datos['email'], 
            pass_hash
        ))
        id_nuevo = cursor.fetchone()[0]
        
        # 3. Saldo inicial
        sql_saldo = "INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion) VALUES (%s, 500.00, NOW());"
        cursor.execute(sql_saldo, (id_nuevo,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"exito": True, "mensaje": "Registro exitoso"}
        
    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        err = str(e)
        if "email" in err: return {"exito": False, "mensaje": "Correo ya registrado"}
        if "curp" in err: return {"exito": False, "mensaje": "CURP ya registrada"}
        return {"exito": False, "mensaje": "Error de duplicados"}
    except Exception as e:
        if conn: conn.rollback()
        return {"exito": False, "mensaje": str(e)}
        
def validar_login(email, password):
    conn = get_db_connection()
    if not conn: return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Buscamos al usuario SOLO por email (y traemos su hash)
        sql = """
            SELECT u.id_usuario, u.email, u.nombre, u.password_hash, 
                   s.saldo_actual, r.nombre as nombre_rol
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE u.email = %s AND u.activo = true
        """
        cursor.execute(sql, (email,))
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()

        # 2. Si el usuario existe, verificamos la contraseña con Argon2
        if usuario and pwd_context.verify(password, usuario['password_hash']):
            # ¡Contraseña Correcta!
            # Borramos el hash del diccionario para no enviarlo por la red (seguridad)
            del usuario['password_hash'] 
            return usuario
        else:
            # Usuario no existe O contraseña incorrecta
            return None
            
    except Exception as e:
        print(f"Error login: {e}")
        return None
    # --- EN db_config.py ---

def obtener_perfil(email):
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Traemos datos del usuario y su saldo
        sql = """
            SELECT u.nombre, u.apellido, u.email, s.saldo_actual 
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            WHERE u.email = %s
        """
        cursor.execute(sql, (email,))
        datos = cursor.fetchone()
        conn.close()
        return datos
    except Exception as e:
        print(f"Error obtener perfil: {e}")
        return None

def actualizar_datos_usuario(email, nombre, apellido, nueva_password=None):
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        
        # Si hay contraseña nueva, la encriptamos y actualizamos todo
        if nueva_password and len(nueva_password) > 0:
            pass_hash = pwd_context.hash(nueva_password)
            sql = """
                UPDATE Usuario SET nombre = %s, apellido = %s, password_hash = %s 
                WHERE email = %s
            """
            cursor.execute(sql, (nombre, apellido, pass_hash, email))
        else:
            # Si no hay contraseña nueva, solo actualizamos nombre y apellido
            sql = "UPDATE Usuario SET nombre = %s, apellido = %s WHERE email = %s"
            cursor.execute(sql, (nombre, apellido, email))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizar: {e}")
        return False

def realizar_transaccion_saldo(email, monto, tipo):
    """
    Maneja Depósitos (monto positivo) y Retiros (monto negativo)
    """
    conn = get_db_connection()
    if not conn: return {"exito": False, "mensaje": "Sin conexión"}
    
    try:
        cursor = conn.cursor()
        
        # 1. Verificar saldo actual primero (para retiros)
        cursor.execute("SELECT saldo_actual FROM Saldo s JOIN Usuario u ON s.id_usuario = u.id_usuario WHERE u.email = %s", (email,))
        res = cursor.fetchone()
        if not res: return {"exito": False, "mensaje": "Usuario no encontrado"}
        saldo_actual = float(res[0])
        
        # Validar si es retiro
        if tipo == "retiro":
            if saldo_actual < monto:
                return {"exito": False, "mensaje": "Fondos insuficientes"}
            monto_final = -monto # Convertimos a negativo para restar
        else:
            monto_final = monto # Depósito positivo

        # 2. Actualizar Saldo
        sql = """
            UPDATE Saldo 
            SET saldo_actual = saldo_actual + %s, ultima_actualizacion = NOW()
            WHERE id_usuario = (SELECT id_usuario FROM Usuario WHERE email = %s)
            RETURNING saldo_actual;
        """
        cursor.execute(sql, (monto_final, email))
        nuevo_saldo = cursor.fetchone()[0]
        
        # (Opcional) Aquí podrías insertar en tu tabla 'Transaccion' para historial
        
        conn.commit()
        conn.close()
        return {"exito": True, "mensaje": "Transacción exitosa", "nuevo_saldo": float(nuevo_saldo)}
        
    except Exception as e:
        if conn: conn.rollback()
        return {"exito": False, "mensaje": str(e)}
# ... (Las funciones de get_user_balance y update pueden quedar igual o agregarlas si las necesitas)
