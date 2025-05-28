import uuid
from flask import Blueprint, render_template, redirect, session, url_for, request, jsonify, send_file # type: ignore
from flask_login import current_user, login_required # type: ignore
from datetime import datetime
from math import ceil
import os
from mongoengine.errors import DoesNotExist # type: ignore
from threading import Thread

from .extensions import db, bcrypt
from .models import Monitoreo
from app.utils import generar_pdf, procesar_imagen
from datetime import datetime  # ya tienes esto, asegúrate de que esté
from app.detector import procesar_frame_yolo, reset_monitoreo, cliente_monitoreo  # ya tienes esto
from app.models import Monitoreo  # asegúrate que este es el modelo correcto

routes = Blueprint('routes', __name__)

# -- INDEX --
@routes.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('routes.panel'))
    return render_template('login.html')

# -- MONITOREO --
@routes.route('/monitoreo', methods=['GET'])
def monitoreo():
    datos = Monitoreo.objects.order_by('-id').first()
    
    # En este caso, ya no usas camera.running porque la cámara es del navegador (cliente)
    monitoring_active = True  # o cualquier lógica si decides manejar estados

    return render_template('monitoreo.html', datos=datos, monitoring_active=monitoring_active)


# -- PANEL --
@routes.route('/panel')
@login_required
def panel():
    total_ladrillos = sum(m.total_ladrillos for m in Monitoreo.objects)
    total_buenos = sum(m.ladrillos_buenos for m in Monitoreo.objects)
    total_malos = sum(m.ladrillos_malos for m in Monitoreo.objects)
    precision_promedio = sum(m.precision for m in Monitoreo.objects) / Monitoreo.objects.count() if Monitoreo.objects else 0.0
    tiempo_promedio_fisura = sum(m.tiempo_promedio_fisura or 0 for m in Monitoreo.objects) / Monitoreo.objects.count() if Monitoreo.objects else 0.0

    return render_template('panel.html',
        total_ladrillos=total_ladrillos,
        total_buenos=total_buenos,
        total_malos=total_malos,
        precision_promedio=round(precision_promedio, 2),
        tiempo_promedio_fisura=round(tiempo_promedio_fisura, 2)
    )

# -- RESULTADOS --
@routes.route('/resultados')
@login_required
def resultados():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    query = Monitoreo.objects
    if fecha_inicio:
        query = query.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        query = query.filter(fecha__lte=fecha_fin)

    query = query.order_by('-fecha')
    total = query.count()
    total_pages = ceil(total / per_page)
    items = query.skip((page - 1) * per_page).limit(per_page)

    class Pagination:
        def __init__(self, items, page, total_pages):
            self.items = items
            self.page = page
            self.pages = total_pages
            self.has_prev = page > 1
            self.has_next = page < total_pages
            self.prev_num = page - 1
            self.next_num = page + 1

    monitoreos = Pagination(items, page, total_pages)

    return render_template("resultados.html", monitoreos=monitoreos,
                           fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

# -- DESCARGAR PDF --
@routes.route('/descargar_reporte/<monitoreo_id>')
@login_required
def descargar_reporte(monitoreo_id):
    try:
        monitoreo = Monitoreo.objects.get(id=monitoreo_id)
    except DoesNotExist:
        return "❌ Monitoreo no encontrado", 404

    pdf_path = os.path.join(os.path.dirname(__file__), 'static', monitoreo.pdf_path)
    if not os.path.exists(pdf_path):
        return f"No se encontró el archivo: {pdf_path}", 404

    return send_file(pdf_path, as_attachment=True)

# -- ELIMINAR MONITOREO --
@routes.route('/eliminar_monitoreo/<monitoreo_id>', methods=['POST'])
@login_required
def eliminar_monitoreo(monitoreo_id):
    try:
        monitoreo = Monitoreo.objects.get(id=monitoreo_id)
    except DoesNotExist:
        return "❌ Monitoreo no encontrado", 404

    if monitoreo.pdf_path:
        pdf_path = os.path.join(os.getcwd(), 'app', 'static', monitoreo.pdf_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    monitoreo.delete()
    return redirect(url_for('routes.resultados'))


@routes.route("/procesar_frame", methods=["POST"])
@login_required
def procesar_frame():
    if 'frame' not in request.files:
        return jsonify({"error": "No se recibió frame"}), 400

    frame_file = request.files['frame']
    usuario_id = str(current_user.id)

    resultados = procesar_frame_yolo(frame_file, usuario_id)
    return jsonify(resultados)


# -- PROCESAR FRAME (desde el navegador) --
# Diccionario en memoria para acumular conteos por usuario
#conteos_usuarios = {}
#
#@routes.route('/procesar_frame', methods=['POST'])#
#@login_required#
#def procesar_frame():#
#    frame = request.files.get('frame'#)#
#    if not frame:#
#        return jsonify({"error": "No #se r#ecibió el frame"}), 400#
#
#    usuario_id = str(current_user.id)#
#
#    # Obtener clases detectadas con tu mo#delo
#    predicciones = procesar_imagen(frame)#
#
#    # Contar por clase#
#    conteo = {"fisura": 0, "ro#tura": 0, "bueno": 0}
#    for clase in predicciones:#
#        if clase in conteo:#
#            conteo[clase] += 1#
#
#    # Inicializar el conteo del usuario si no existe#
#    if usuario_id not in conteos_usuarios:#
#        conteos_usuarios[usuario_id] = {"fisura": 0, "rotura":# 0, "bueno": 0, "total": 0}#
#
#    # Acumular detecciones#
#    for clave in conteo:#
#        conteos_usuarios[usuario_id][clave] += conteo[clave]#
#    conteos_usuarios[usuario_id]["total"] += len(prediccione#s)#
#
#    # Calcular precisión#
#    buenos = conteos_usuarios[usuario_id]["bueno"]#
#    total = conteos_usuarios[usuario_id]["total"]#
#    precision = (buenos / total) * 100 if total > 0 else 0.0#
#
#    return jsonify({
#        "total": total,
#        "buenos": buenos,
#        "fisura": conteos_usuarios[usuario_id]["fisura"],
#        "rotura": conteos_usuarios[usuario_id]["rotura"],
#        "precision": round(precision, 2)
#    })


# Ruta para iniciar monitoreo
@routes.route('/iniciar_monitoreo', methods=['POST'])
def iniciar_monitoreo():
    def ejecutar_monitoreo():
        cliente.iniciar()

    # Ejecuta en segundo plano
    thread = Thread(target=ejecutar_monitoreo)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'Monitoreo iniciado'}), 200

# -- FINALIZAR MONITOREO --
@routes.route('/finalizar_monitoreo', methods=['POST'])
@login_required
def finalizar_monitoreo():
    usuario_id = str(current_user.id)
    
    try:
        datos = cliente_monitoreo.obtener_métricas_finales(usuario_id)
    except Exception as e:
        return jsonify({"error": f"Error obteniendo métricas: {str(e)}"}), 500

    # ✅ Obtener fechas y horas de inicio y fin
    fecha_inicio = datetime.fromtimestamp(cliente_monitoreo.data[usuario_id]["start_time"])
    fecha_fin = datetime.now()

    # ✅ Crear y guardar monitoreo en MongoDB
    monitoreo = Monitoreo(
        usuario=current_user.email,
        fecha=fecha_fin,
        hora_inicio=fecha_inicio.strftime('%H:%M:%S'),
        hora_fin=fecha_fin.strftime('%H:%M:%S'),
        total_ladrillos=datos["total"],
        ladrillos_buenos=datos["buenos"],
        ladrillos_malos = datos.get("fisura", 0) + datos.get("rotura", 0),
        precision=datos["precision"],
        tiempo_promedio_fisura=datos["tiempo_promedio_fisura"]
    )
    monitoreo.save()

    # ✅ Generar y guardar ruta del PDF
    ruta_pdf = generar_pdf(monitoreo)
    monitoreo.pdf_path = ruta_pdf
    monitoreo.save()

    # ✅ Limpiar datos de sesión y estado del cliente
    cliente_monitoreo.resetear(usuario_id)
    session.pop('usuario_id', None)

    return jsonify({"status": "ok", "reporte_id": str(monitoreo.id)})
