from ultralytics import YOLO
from picamera2 import Picamera2
import numpy as np
import cv2
import time

# 1. Configuración de Cámara
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

# 2. Cargar YOLO
model = YOLO('yolov8n.pt')

print("--- MODO DIAGNÓSTICO ACTIVO ---")

# --- PRUEBA DE SUPERVIVENCIA ---
# Captura una imagen de inmediato para ver qué está viendo la cámara
frame_test = picam2.capture_array()
test_bgr = cv2.cvtColor(frame_test, cv2.COLOR_RGB2BGR)
cv2.imwrite('VISTA_CAMARA.jpg', test_bgr)
print("✅ Se ha guardado 'VISTA_CAMARA.jpg'. Revísala para ver el enfoque.")
# -------------------------------

try:
    while True:
        frame = picam2.capture_array()
        # Bajamos la confianza a 0.25 para detectar más fácil durante las pruebas
        results = model(frame, conf=0.25, verbose=False)

        for result in results:
            for box in result.boxes:
                label = model.names[int(box.cls[0])]
                conf = box.conf[0]
                
                # Imprimimos TODO lo que vea para saber que está trabajando
                print(f"Detectado: {label} con {conf:.2f} de confianza")
                
                if label in ['car', 'truck', 'motorcycle', 'bus', 'person']:
                    bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    timestamp = time.strftime("%H%M%S")
                    cv2.imwrite(f'deteccion_{label}_{timestamp}.jpg', bgr_frame)
                    print(f"⭐ ¡{label} guardado exitosamente!")

except KeyboardInterrupt:
    print("\nDeteniendo...")
finally:
    picam2.stop()
