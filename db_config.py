import psycopg2
from psycopg2.extras import RealDictCursor
import os
import hashlib

# --- CONEXIÓN A LA BASE DE DATOS ---
def get_db_connection():
    try:
        # Render busca la variable de entorno DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ ERROR CRÍTICO: No existe la variable DATABASE_URL en Render")
            return None
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")
        return None

# --- REGISTRO DE USUARIO (LA FUNCIÓN QUE TE FALTABA) ---
def registrar_usuario_nuevo(datos):
    """
    Inserta un usuario nuevo asignándole el rol de 'Jugador' automáticamente.
    Crea también su registro en la tabla Saldo.
    """
    conn = get_db_connection()
    if not conn:
        return {"exito": False, "mensaje": "Error de conexión a BD"}
    
    try:
        cursor = conn.cursor()
        
        # 1. Encriptar contraseña (SHA256)
        pass_hash = hashlib.sha256(datos['password'].encode()).hexdigest()
        
        # 2. Insertar Usuario
        # Buscamos el ID del rol 'Jugador' al vuelo usando una subconsulta
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
        
        # Obtenemos el ID que Neon acaba de crear
        id_nuevo = cursor.fetchone()[0]
        
        # 3. Crear Saldo Inicial ($500 de regalo de bienvenida)
        sql_saldo = """
            INSERT INTO Saldo (id_usuario, saldo_actual, ultima_actualizacion)
            VALUES (%s, 500.00, NOW());
        """
        cursor.execute(sql_saldo, (id_nuevo,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Usuario registrado con éxito: {datos['email']} (ID: {id_nuevo})")
        return {"exito": True, "mensaje": "Registro exitoso"}
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        error_msg = str(e)
        if "email" in error_msg:
            return {"exito": False, "mensaje": "Este correo ya está registrado."}
        if "curp" in error_msg:
            return {"exito": False, "mensaje": "Esta CURP ya está registrada."}
        if "rol" in error_msg:
             return {"exito": False, "mensaje": "Error interno: El rol 'Jugador' no existe en la BD."}
        return {"exito": False, "mensaje": "Error de duplicidad en base de datos."}
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error desconocido en registro: {e}")
        return {"exito": False, "mensaje": str(e)}

# --- VALIDAR LOGIN ---
def validar_login(email, password):
    conn = get_db_connection()
    if not conn: return None
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Unimos Usuario, Saldo y Rol para tener toda la info
        sql = """
            SELECT u.id_usuario, u.email, u.nombre, s.saldo_actual, r.nombre as nombre_rol
            FROM Usuario u
            JOIN Saldo s ON u.id_usuario = s.id_usuario
            JOIN Rol r ON u.id_rol = r.id_rol
            WHERE u.email = %s AND u.password_hash = %s AND u.activo = true
        """
        cursor.execute(sql, (email, pass_hash))
        usuario = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return usuario # Retorna diccionario con datos o None
    except Exception as e:
        print(f"Error login: {e}")
        return None
