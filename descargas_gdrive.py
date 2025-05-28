import gdown # type: ignore
import zipfile
import os

def descargar_modelo():
    modelo_url = "https://drive.google.com/uc?id=174Td9kRd10iImunxIwrXZsKn9PduBDTX"
    output_path = "best50e1.pt"

    if not os.path.exists(output_path):
        print("Descargando modelo YOLOv5...")
        gdown.download(modelo_url, output_path, quiet=False)
    else:
        print("✅ Modelo ya existe.")

def descargar_imagenes():
    zip_url = "https://drive.google.com/uc?id=1m0JB-TNkKKXsh4HiGR8o8Y14tAoe-t5D"
    output_zip = "imagenes.zip"
    carpeta_destino = "imagenes"

    if not os.path.exists(carpeta_destino):
        print("Descargando carpeta de imágenes...")
        gdown.download(zip_url, output_zip, quiet=False)

        with zipfile.ZipFile(output_zip, 'r') as zip_ref:
            zip_ref.extractall(carpeta_destino)

        os.remove(output_zip)
        print("✅ Imágenes extraídas.")
    else:
        print("✅ Carpeta de imágenes ya existe.")

if __name__ == "__main__":
    descargar_modelo()
    descargar_imagenes()
