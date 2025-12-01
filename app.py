# 1. GUARDAR DATOS
@app.route("/api/guardar_checklist", methods=["POST"])
def api_guardar_checklist():
    try:
        data = request.get_json(force=True)
        email = data.get("email")
        resumen = data.get("resumen")  # Ej: "Revisión diaria Máquinas"
        checklist = data.get(
            "checklist"
        )  # Diccionario Ej: {"luces": "OK", "limpieza": "FALLO"}

        # Convertimos el diccionario a texto JSON para la base de datos
        checklist_json = json.dumps(checklist)

        id_audit = guardar_auditoria(email, resumen, checklist_json)

        if id_audit:
            # Devolvemos la URL directa para descargar el PDF
            pdf_url = f"/api/pdf_auditoria/{id_audit}"
            return jsonify({"exito": True, "mensaje": "Guardado", "pdf_url": pdf_url})
        else:
            return jsonify({"exito": False, "mensaje": "Error al guardar en BD"}), 500

    except Exception as e:
        return jsonify({"exito": False, "mensaje": str(e)}), 400


# 2. GENERAR Y DESCARGAR PDF
@app.route("/api/pdf_auditoria/<int:id_auditoria>", methods=["GET"])
def generar_pdf(id_auditoria):
    # 1. Obtener datos de la BD
    datos = obtener_datos_auditoria(id_auditoria)
    if not datos:
        return "Auditoría no encontrada", 404

    # 2. Crear PDF en memoria (RAM)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # 3. Dibujar contenido
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"REPORTE DE AUDITORÍA #{id_auditoria}")

    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Auditor: {datos['nombre']} {datos['apellido']}")
    c.drawString(100, 705, f"Fecha: {datos['fecha_auditoria']}")
    c.drawString(100, 690, f"Resumen: {datos['resumen']}")

    c.line(100, 680, 500, 680)  # Línea separadora

    # Dibujar el Checklist
    y = 650
    items = datos["datos_auditoria"]  # PostgreSQL ya lo devuelve como diccionario

    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "DETALLE DE REVISIÓN:")
    y -= 20

    c.setFont("Helvetica", 11)
    for key, value in items.items():
        # Ejemplo: "Luces: OK"
        estado = "✅ APROBADO" if value else "❌ FALLO"
        c.drawString(120, y, f"- {key}: {estado}")
        y -= 20

    c.showPage()
    c.save()

    # 4. Enviar archivo al navegador/celular
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"auditoria_{id_auditoria}.pdf",
        mimetype="application/pdf",
    )
