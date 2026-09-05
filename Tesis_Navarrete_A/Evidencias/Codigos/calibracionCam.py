import time
import requests
import cv2
from picamera2 import Picamera2

# --- TUS CREDENCIALES ---
TOKEN = "8626887025:AAFdYomeBzMKQyYkmnFVxpKtaXqVtfajP0g"
CHAT_ID = "5682386608"

def enviar_telegram(ruta_imagen):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(ruta_imagen, 'rb') as f:
            requests.post(url, data={'chat_id': CHAT_ID}, files={'photo': f})
        print("✅ Foto enviada al celular.")
    except Exception as e:
        print(f"❌ Error de envío: {e}")

print("Iniciando cámara con Picamera2...")
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

print("--- Sistema de Calibración Activo ---")
print("Enviando una foto cada 10 segundos. Presiona Ctrl+C para detener.")

try:
    contador = 1
    while True:
        # Captura y conversión de color
        img_rgb = picam2.capture_array()
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        
        archivo_temp = "calibracion_temp.jpg"
        cv2.imwrite(archivo_temp, img_bgr)
        
        print(f"Tomando foto {contador}...")
        enviar_telegram(archivo_temp)
        
        contador += 1
        time.sleep(10)

except KeyboardInterrupt:
    print("\nCalibración finalizada. Apagando script.")
finally:
    picam2.stop()
