# run.py
import os

# Descargar recursos desde Google Drive si no existen
from descargas_gdrive import descargar_modelo, descargar_imagenes
descargar_modelo()
descargar_imagenes()

# Luego importa e inicia tu aplicación Flask normalmente
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
