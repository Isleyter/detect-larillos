import cv2  # type: ignore
import torch # type: ignore
from pathlib import Path
import sys
#from ultralytics import YOLO
import torch # type: ignore
from datetime import datetime
from app import routes
#from flask import jsonify # type: ignore

camera = None

def descargar_modelo():
    url = "https://drive.google.com/uc?id=174Td9kRd10iImunxIwrXZsKn9PduBDTX"
    output = "yolov5_model/best.pt"
    if not os.path.exists(output):
        os.makedirs("yolov5_model", exist_ok=True)
        print("Descargando modelo YOLO...")
        gdown.download(url, output, quiet=False) # type: ignore

descargar_modelo()

#--DETECTAR CAMARAS DISPONIBLES---
def listar_camaras_disponibles(max_camaras=5):
    disponibles = []
    for i in range(max_camaras):
        cap = cv2.VideoCapture(i)
        if cap is not None and cap.read()[0]:
            disponibles.append(i)
            cap.release()
    return disponibles

class VideoCamera:
    def __init__(self, camara_index=0):
        descargar_modelo()
        self.camera_index = camara_index
        self.video =  None
        self.running = False  # iniciar como False
        self.total_counts = {'fisura': 0, 'rotura': 0, 'bueno': 0}  
        # Asegúrate de abrir la cámara en el inicio
        try:
            self.video = cv2.VideoCapture(camara_index)  # Usa el índice de la cámara (0 para la primera)
            if not self.video.isOpened():
                raise ValueError(f"No se pudo abrir la cámara con índice {camara_index}")
        except Exception as e:
            print(f"❌ Error al inicializar la cámara: {e}")
            self.video = None

        self.start_time = datetime.now()
        self.end_time = None
        #.................................
        self.tiempos_fisura = []  # lista de tiempos de detección
        # Compatibilidad pathlib en Windows
        #sys.modules['pathlib'].PosixPath = Path
        # Cargar modelo YOLOv5
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='best50e1.pt')  # force_reload=True
        self.model.conf = 0.5
        self.model.iou = 0.45
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)

    def start(self):
        if self.video is None:
            self.__init__()  # Vuelve a inicializar si la cámara no estaba abierta.
        self.running = True

    def stop(self):
        self.running = False
        if self.video is not None:
            self.video.release()
    
    #detectar fisura
    def detectar_fisura(self, frame):
        inicio = datetime.now()
        # ----- LÓGICA DE DETECCIÓN DE FISURA -----
        resultado = self.mi_modelo.detect(frame)  # Asegúrate de tener esto definido
        fin = datetime.now()
        duracion = (fin - inicio).total_seconds()
        # Guardar tiempo si se detectó una fisura
        if any(det['label'] == 'fisura' for det in resultado):  # ajusta si tu resultado es distinto
            self.tiempos_fisura.append(duracion)
        return resultado
    
    def get_counts(self):
        total = sum(self.total_counts.values())
        buenos = self.total_counts['bueno']
        malos = self.total_counts['fisura'] - self.total_counts['rotura']
        precision = self.get_precision()
        return {
            "total": total,
            "buenos": buenos,
            "malos": malos,
            "precision": precision
        }

    #def get_precision(self):
    #    total_detectados = sum(self.total_counts.values())
    #    if total_detectados == 0:
    #        return 0.0
    #
    #    defectuosos = self.total_counts.get('fisura', 0) + self.total_counts.get('rotura', 0)
    #    return round((defectuosos / total_detectados) * 100, 2)

    #--METODO PARA CALCULAR % DE LADRILLOS FRACTURADOS----
    def get_precision(self):
        total_fisura = self.total_counts.get('fisura', 0)
        total_rotura = self.total_counts.get('rotura', 0)
        total_bueno = self.total_counts.get('bueno', 0)
        total_defectuosos = total_fisura + total_rotura
        total_detectados = total_defectuosos + total_bueno
        if total_detectados == 0:
            return 0.0  # Para evitar división por cero
        precision = (total_defectuosos / total_detectados) * 100
        return round(precision, 2)

    #------restaurar contador--------
    def reset_counts(self):
        self.total = 0
        self.buenos = 0
        self.malos = 0
        self.precision = 0.0
        self.total_counts = {'fisura': 0, 'rotura': 0, 'bueno': 0}
        self.tiempos_fisura = []
        self.start_time = datetime.now()
        self.end_time = None

    def get_frame(self):
        if self.video is None or not self.video.isOpened():
            return None
        success, frame = self.video.read()
        if not success:
            return None  # Si no se pudo obtener el frame, retorna None
        self.counts = {'fisura': 0, 'rotura': 0, 'bueno': 0}
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.model(img, size=640)
        detections = results.xyxy[0]

        for *box, conf, cls in detections:
            label = self.model.names[int(cls)]
            if label in self.counts:
                self.counts[label] += 1
                self.total_counts[label] += 1

                # Medir tiempo si es una fisura
                if label == 'fisura':
                    inicio = datetime.now()
                    duracion = (inicio - self.start_time).total_seconds()
                    self.tiempos_fisura.append(duracion)

            x1, y1, x2, y2 = map(int, box)
            color = (0, 255, 0) if label == 'bueno' else (0, 0, 255)
            text = f"{label} {float(conf):.1f}%"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        conteo_texto = f"Fisuras: {self.counts['fisura']}  Roturas: {self.counts['rotura']}  Buenos: {self.counts['bueno']}"
        cv2.putText(frame, conteo_texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        ret, jpeg = cv2.imencode('.jpg', frame)
        self.precision = self.get_precision()  # Actualizamos la precisión
        return jpeg.tobytes()

    def release(self):
        """Libera recursos y guarda resultados."""
        if self.video.isOpened():
            self.video.release()
        self.end_time = datetime.now()
        try:
            self.save_results()
        except Exception as e:
            print(f"[Error al guardar resultados]: {e}")
    
    #metodo para calcular el tiempo promedio
    def obtener_tiempo_promedio_fisura(self):
        if not self.tiempos_fisura:
            return 0.0
        return round(sum(self.tiempos_fisura) / len(self.tiempos_fisura), 2)

    def save_results(self):
        from fpdf import FPDF # type: ignore
        import os

        total = sum(self.total_counts.values())
        malos = self.total_counts['fisura'] + self.total_counts['rotura']
        buenos = self.total_counts['bueno']
        precision = 0
        if malos + buenos > 0:
            precision = (self.total_counts['fisura'] / (malos + buenos)) * 100
        
        #-------------------------------------
        tiempo_promedio_fisura = self.obtener_tiempo_promedio_fisura()
        #-----------------------------------
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Reporte de Monitoreo", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Inicio: {self.start_time}", ln=True)
        pdf.cell(200, 10, txt=f"Fin: {self.end_time}", ln=True)
        pdf.cell(200, 10, txt=f"Total ladrillos: {total}", ln=True)
        pdf.cell(200, 10, txt=f"Buenos: {buenos}", ln=True)
        pdf.cell(200, 10, txt=f"Malos: {malos}", ln=True)
        pdf.cell(200, 10, txt=f"Precisión de fisura: {precision:.2f}%", ln=True)

        #--------------
         # ➕ Agrega el tiempo promedio al PDF
        pdf.cell(200, 10, txt=f"Tiempo promedio de detección de fisura: {tiempo_promedio_fisura:.2f} seg", ln=True)
        #-------------

        os.makedirs("reportes", exist_ok=True)
        filename = f"reporte_{self.start_time.strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(f"reportes/{filename}")

#------------conteo actualizado
def generate_frames():
    global camera
    while True:
        if camera:
            frame = camera.get_frame()
            if frame is None:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            break  # o puedes hacer time.sleep() hasta que se inicie

