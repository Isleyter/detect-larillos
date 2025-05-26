import gdown # type: ignore
import os
import cv2  # type: ignore
import torch # type: ignore
from pathlib import Path
import sys
from datetime import datetime
from app import routes

def descargar_modelo():
    url = "https://drive.google.com/uc?id=174Td9kRd10iImunxIwrXZsKn9PduBDTX"
    output = "yolov5_model/best.pt"
    if not os.path.exists(output):
        os.makedirs("yolov5_model", exist_ok=True)
        print("Descargando modelo YOLO...")
        gdown.download(url, output, quiet=False)

descargar_modelo()

def detectar_fuente_video():
    import platform
    en_render = os.environ.get("RENDER", "false").lower() == "true"
    if en_render:
        print("⚠️ Ejecutando en Render (sin acceso a cámara física).")
        return None

    sistema = platform.system()
    print(f"🖥️ Sistema operativo detectado: {sistema}")
    
    for index in range(3):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            print(f"✅ Cámara encontrada en índice {index}")
            return cap
    print("❌ No se encontró cámara disponible.")
    return None

class VideoCamera:
    def __init__(self):
        descargar_modelo()
        self.video = detectar_fuente_video()
        self.running = False
        self.total_counts = {'fisura': 0, 'rotura': 0, 'bueno': 0}  
        self.start_time = datetime.now()
        self.end_time = None
        self.tiempos_fisura = []
        #sys.modules['pathlib'].PosixPath = Path

        try:
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='best50e1.pt')
            self.model.conf = 0.5
            self.model.iou = 0.45
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(device)
        except Exception as e:
            print(f"❌ Error al cargar el modelo: {e}")
            self.model = None

    def start(self):
        if self.video is None:
            self.video = detectar_fuente_video()
        self.running = True

    def stop(self):
        self.running = False
        if self.video:
            self.video.release()

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

    def get_precision(self):
        total_fisura = self.total_counts.get('fisura', 0)
        total_rotura = self.total_counts.get('rotura', 0)
        total_bueno = self.total_counts.get('bueno', 0)
        total_defectuosos = total_fisura + total_rotura
        total_detectados = total_defectuosos + total_bueno
        if total_detectados == 0:
            return 0.0
        precision = (total_defectuosos / total_detectados) * 100
        return round(precision, 2)

    def reset_counts(self):
        self.total_counts = {'fisura': 0, 'rotura': 0, 'bueno': 0}
        self.tiempos_fisura = []
        self.start_time = datetime.now()
        self.end_time = None

    def get_frame(self):
        if self.video is None or not self.video.isOpened():
            return None
        success, frame = self.video.read()
        if not success or frame is None:
            return None
        self.counts = {'fisura': 0, 'rotura': 0, 'bueno': 0}
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.model(img, size=640)
        detections = results.xyxy[0]

        for *box, conf, cls in detections:
            label = self.model.names[int(cls)]
            if label in self.counts:
                self.counts[label] += 1
                self.total_counts[label] += 1

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
        self.precision = self.get_precision()
        return jpeg.tobytes()

    def release(self):
        if self.video and self.video.isOpened():
            self.video.release()
        self.video = None
        self.end_time = datetime.now()
        try:
            self.save_results()
        except Exception as e:
            print(f"[Error al guardar resultados]: {e}")
    
    def obtener_tiempo_promedio_fisura(self):
        if not self.tiempos_fisura:
            return 0.0
        return round(sum(self.tiempos_fisura) / len(self.tiempos_fisura), 2)

    def save_results(self):
        from fpdf import FPDF # type: ignore
        total = sum(self.total_counts.values())
        malos = self.total_counts['fisura'] + self.total_counts['rotura']
        buenos = self.total_counts['bueno']
        precision = (self.total_counts['fisura'] / (malos + buenos)) * 100 if malos + buenos > 0 else 0
        tiempo_promedio_fisura = self.obtener_tiempo_promedio_fisura()

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
        pdf.cell(200, 10, txt=f"Tiempo promedio detección fisura: {tiempo_promedio_fisura:.2f} seg", ln=True)

        os.makedirs("reportes", exist_ok=True)
        filename = f"reporte_{self.start_time.strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(f"reportes/{filename}")

def generate_frames():
    while True:
        frame = video_camera.get_frame() # type: ignore
        if frame is None:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
