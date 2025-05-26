from flask import Flask, flash, jsonify, Blueprint, render_template, redirect, session, url_for, Response, send_file, request # type: ignore
from flask_login import current_user, login_required # type: ignore
from datetime import date, datetime

from .extensions import db, bcrypt

from app.camera import VideoCamera, camera, listar_camaras_disponibles, generate_frames
from .models import Monitoreo
from app.utils import generar_pdf, get_monitoring_results
from math import ceil
from mongoengine.errors import DoesNotExist # type: ignore
#from app.camera import camera, listar_camaras_disponibles
import cv2
import os

routes = Blueprint('routes', __name__)

# Variable global para almacenar la hora de inicio

start_time = None
camera = None
# -- INDEX --
@routes.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('routes.panel'))  # o la página principal para usuarios logueados
    else:
        return render_template('login.html')

# -- PANEL --
@routes.route('/panel')
@login_required
def panel():
    # Consulta los datos agregados
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

#def panel():
#    results = get_monitoring_results()
#    return render_template('panel.html', results=results)

# -- MONITOREO --
@routes.route('/monitoreo', methods=['GET'])
def monitoreo():
    from app.camera import listar_camaras_disponibles
    monitoring_active = camera is not None and camera.running
    datos = Monitoreo.objects.order_by('-id').first()
    camaras_disponibles = listar_camaras_disponibles()
    
    return render_template('monitoreo.html',
                           datos=datos,
                           camaras=camaras_disponibles,
                           monitoring_active=monitoring_active)

#@routes.route('/monitoreo', methods=['GET'])
#def monitoreo():
#    monitoring_active = camera is not None and camera.running
#    datos = Monitoreo.objects.order_by('-id').first()
#    return render_template('monitoreo.html', datos=datos, monitoring_active=monitoring_active)

#-- IICIAR Y FINALIZAR MONITOREO
@routes.route('/iniciar_monitoreo', methods=['POST'])
def iniciar_monitoreo():
    global camera
    try:
        # Obtener el índice de cámara desde el formulario
        camara_index = int(request.form.get('camara', 0))

        # Liberar cámara previa si existe
        if camera:
            camera.release()
            camera = None

        # Crear nueva instancia con el índice seleccionado
        camera = VideoCamera(camara_index)
        camera.start()
        flash(f"✅ Monitoreo iniciado con cámara {camara_index}")
        print("✅ Cámara inicializada correctamente.")
    except Exception as e:
        flash("❌ Error al iniciar la cámara.")
        print("❌ Error al iniciar la cámara:", e)

    # Guardar la hora de inicio en sesión
    session['hora_inicio'] = datetime.now().strftime('%H:%M:%S')
    print("✅ Hora guardada en sesión:", session['hora_inicio'])

    return redirect(url_for('routes.monitoreo'))

#@routes.route('/iniciar_monitoreo', methods=['POST'])
#def iniciar_monitoreo():
#    global camera
#    try:
#        if camera is None:
#            camera = VideoCamera()
#        camera.start()  # Activar monitoreo (marca running = True)
#        print("✅ Cámara inicializada correctamente.")
#    except Exception as e:
#        print("❌ Error al iniciar la cámara:", e)
#    
#    session['hora_inicio'] = datetime.now().strftime('%H:%M:%S')
#    print("✅ Hora guardada en sesión:", session['hora_inicio'])
#    return redirect(url_for('routes.monitoreo'))
    
@routes.route('/start_monitoring')
def start_monitoring():
    from app.camera import VideoCamera
    global camera

    camara_index = int(request.args.get('camara', 0))  # valor por defecto 0

    if camera:
        camera.release()
        camera = None

    camera = VideoCamera(camara_index)
    camera.start()
    return '', 204

@routes.route('/finalizar_monitoreo', methods=['POST'])
@login_required
def finalizar_monitoreo():
    global camera, start_time
    if not camera:
        return 'Error: Cámara no iniciada', 400
    # Guardar hora de inicio
    hora_inicio_str = session.get("hora_inicio")
    if not hora_inicio_str:
        return 'Error: Monitoreo no iniciado', 400

    # Obtener hora fin
    hora_fin = datetime.now()
    hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M:%S').time()
    hora_fin_time = hora_fin.time()

    # Obtener resultados en vivo
    resultados = camera.get_counts()
    precision = float(resultados["precision"])

    # Obtener tiempo promedio para fisura
    tiempo_promedio_fisura = camera.obtener_tiempo_promedio_fisura()  # <-- Asegúrate que exista

    # Calcular el número de monitoreo secuencial
    ultimo = Monitoreo.objects.order_by('-monitoreo_id').first()
    nuevo_id = 1 if not ultimo else ultimo.monitoreo_id + 1

    #Guardar monitorep
    monitoreo = Monitoreo(
        monitoreo_id = nuevo_id,
        fecha=datetime.now(),
        hora_inicio=hora_inicio.strftime('%H:%M:%S'),
        hora_fin=hora_fin_time.strftime('%H:%M:%S'),
        total_ladrillos=resultados["total"],
        ladrillos_buenos=resultados["buenos"],
        ladrillos_malos=resultados["malos"],
        precision=precision,
        tiempo_promedio_fisura=tiempo_promedio_fisura
    )
    
    monitoreo.save()
    
    # Generar PDF
    pdf_path = generar_pdf(monitoreo)
    monitoreo.pdf_path = pdf_path
    monitoreo.save()

    # Finalizar monitoreo
    camera.stop()            # Marcar como inactivo
    camera.release()
    camera.reset_counts()
    camera = None
    session.pop("hora_inicio", None)

    #datos = Monitoreo.objects.order_by('-id').first()
    camaras_disponibles = listar_camaras_disponibles()
    monitoring_active = False

    return render_template("monitoreo.html",
                           monitoring_finished=True,
                           datos={
                               "total": resultados["total"],
                               "buenos": resultados["buenos"],
                               "malos": resultados["malos"],
                               "precision": precision,
                               "tiempo_promedio_fisura": round(tiempo_promedio_fisura, 2)
                           },
                           camaras=camaras_disponibles,
                           monitoring_active=monitoring_active)

    ## Pasar los datos a monitoreo.html
    #return render_template("monitoreo.html", monitoring_finished=True, 
    #                        datos={
    #                            "total": resultados["total"],
    #                            "buenos": resultados["buenos"],
    #                            "malos": resultados["malos"],
    #                            "precision": precision,
    #                            "tiempo_promedio_fisura": round(tiempo_promedio_fisura, 2)  #lo pasamos a la plantilla
    #                        }
    #)


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

    # Subconjunto paginado
    items = query.skip((page - 1) * per_page).limit(per_page)

    # Crear objeto simulado para paginación
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

    return render_template(
        "resultados.html",
        monitoreos=monitoreos,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )

# -- PDF DE RESULTADOS --
@routes.route('/descargar_reporte/<monitoreo_id>')
@login_required
def descargar_reporte(monitoreo_id):
    try:
        monitoreo = Monitoreo.objects.get(id=monitoreo_id)
    except DoesNotExist:
        return "❌ Monitoreo no encontrado", 404
    
    # Solo una vez 'app/static'
    pdf_path = os.path.join(os.path.dirname(__file__), 'static', monitoreo.pdf_path)

    if not os.path.exists(pdf_path):
        return f"No se encontró el archivo: {pdf_path}", 404

    return send_file(pdf_path, as_attachment=True)


# -- VIDEO FEED --
@routes.route('/video_feed')
@login_required
def video_feed():
    global camera
    if not camera:
        return "Cámara no iniciada", 500
    
    def gen(camera):
        while True:
            frame = camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    return Response(gen(camera), mimetype='multipart/x-mixed-replace; boundary=frame')

#--------------conteo total monitoreo-----------
from flask import jsonify # type: ignore

@routes.route('/conteo')
def conteo():
    global camera
    if camera:
        data = camera.get_counts()
        return jsonify(data)
    return jsonify({'total': 0, 'buenos': 0, 'malos': 0, 'precision': 0.0})


#-----eliminar registro de monitoreo-------------
@routes.route('/eliminar_monitoreo/<monitoreo_id>', methods=['POST'])
@login_required
def eliminar_monitoreo(monitoreo_id):
    try:
        monitoreo = Monitoreo.objects.get(id=monitoreo_id)
    except DoesNotExist:
        return "❌ Monitoreo no encontrado", 404
    
    # Eliminar el archivo PDF si existe
    if monitoreo.pdf_path:
        pdf_path = os.path.join(os.getcwd(), 'app', 'static', monitoreo.pdf_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    monitoreo.delete()
    
    return redirect(url_for('routes.resultados'))


#--DETECTAR CAMARAS----
@routes.route('/listar_camaras')
def listar_camaras():
    disponibles = []
    for i in range(5):  # escanea los primeros 5 dispositivos
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            disponibles.append({'id': i, 'nombre': f'Cámara {i}'})
            cap.release()
    return jsonify(disponibles)


