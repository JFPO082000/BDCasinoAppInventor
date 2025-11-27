from flask import Flask, session, jsonify, request
import os
# Importamos solo las funciones de gestión de usuarios y saldo
from db_config import registrar_usuario_nuevo, validar_login

# --- 1. INICIALIZACIÓN ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# --- 2. CONFIGURACIÓN DE COOKIES (CRÍTICO PARA APP INVENTOR) ---
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 # 1 hora

# ==========================================
# RUTAS API (APP INVENTOR)
# ==========================================

@app.route("/", methods=["GET"])
def index():
    return "Servidor Central del Casino Activo. Usa /api/login o /api/registrar."

@app.route("/api/registrar", methods=["POST"])
def api_registrar():
    print("--- INICIO DE REGISTRO ---")
    try:
        # Intentamos leer JSON (force=True ayuda si el header falla en App Inventor)
        datos = request.get_json(force=True, silent=True)
        
        if not datos:
            cuerpo = request.get_data(as_text=True)
            print(f"❌ ERROR: JSON vacío o inválido. Recibido: {cuerpo}")
            return jsonify({"exito": False, "mensaje": "JSON inválido"}), 400
            
        print(f"📥 Datos recibidos: {datos}")
        
        # Validar campos obligatorios
        campos = ['nombre', 'apellido', 'curp', 'email', 'password']
        faltantes = [campo for campo in campos if campo not in datos]
        
        if faltantes:
            return jsonify({"exito": False, "mensaje": f"Faltan datos: {faltantes}"}), 400

        # Guardar en Neon (llama a db_config.py)
        resultado = registrar_usuario_nuevo(datos)
        
        codigo = 200 if resultado['exito'] else 400
        return jsonify(resultado), codigo

    except Exception as e:
        print(f"🔥 ERROR INTERNO: {e}")
        return jsonify({"exito": False, "mensaje": f"Error del servidor: {str(e)}"}), 500

@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        datos = request.get_json(force=True)
        email = datos.get('email')
        password = datos.get('password')
        
        # Validar credenciales en Neon
        usuario = validar_login(email, password)
        
        if usuario:
            # Crear sesión segura
            session.clear()
            session.permanent = True
            session["user_id"] = usuario['email']
            session["rol"] = usuario['nombre_rol'] 
            
            # Respondemos con el ROL para que App Inventor sepa qué pantalla abrir
            return jsonify({
                "exito": True, 
                "mensaje": "Bienvenido",
                "user_id": usuario['email'],
                "saldo": float(usuario['saldo_actual']),
                "rol": usuario['nombre_rol'] # <--- CLAVE PARA TU REDIRECCIÓN
            })
        else:
            return jsonify({"exito": False, "mensaje": "Credenciales incorrectas"}), 401
            
    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400

# ==========================================
# ARRANQUE DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
