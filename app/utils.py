import os

# Crear carpeta "reportes" si no existe
REPORT_DIR = os.path.join(os.getcwd(), 'reportes')
os.makedirs(REPORT_DIR, exist_ok=True)



def get_monitoring_results():
    # Lógica para calcular métricas
    return {
        "total": 100,
        "buenos": 85,
        "malos": 15,
        "precision": 85.0,
        "promedio_tiempo": "0.2s"
    }


#--2-------monitoreo--------------

from fpdf import FPDF # type: ignore
import os

def generar_pdf(monitoreo):
    os.makedirs("app/static/reportes", exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Reporte de Monitoreo", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Fecha: {monitoreo.fecha}", ln=True)
    pdf.cell(200, 10, txt=f"Inicio: {monitoreo.hora_inicio}", ln=True)
    pdf.cell(200, 10, txt=f"Fin: {monitoreo.hora_fin}", ln=True)
    pdf.cell(200, 10, txt=f"Total: {monitoreo.total_ladrillos}", ln=True)
    pdf.cell(200, 10, txt=f"Buenos: {monitoreo.ladrillos_buenos}", ln=True)
    pdf.cell(200, 10, txt=f"Malos: {monitoreo.ladrillos_malos}", ln=True)
    pdf.cell(200, 10, txt=f"Precisión: {monitoreo.precision:.2f}%", ln=True)

    filename = f"reporte_{monitoreo.id}.pdf"
    path = os.path.join("app", "static", "reportes", filename)
    pdf.output(path)

    return f"reportes/{filename}"  # ✅ SIN el 'static/' inicial

