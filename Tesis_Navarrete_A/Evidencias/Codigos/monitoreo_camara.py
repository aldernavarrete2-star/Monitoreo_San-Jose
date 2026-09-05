   # Capturar con app sola mandar esto : rpicam-hello -t 0
from picamera2 import Picamera2
import cv2

print("--- Iniciando vista en vivo para ajustar lente ---")
print("Cargando módulo Picamera2...")

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

print("Abriendo ventana de video...")
print("⚠️ IMPORTANTE: Selecciona la ventana de video con el mouse y presiona la tecla 'q' para salir.")

try:
    while True:
        # Capturar el frame actual
        img_rgb = picam2.capture_array()
        
        # Convertir a BGR para que OpenCV muestre los colores correctos
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        
        # Mostrar la imagen en una ventana en vivo
        cv2.imshow("Ajuste de Lente (Presiona 'q' para salir)", img_bgr)
        
        # Esperar 1 milisegundo y comprobar si se presionó la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Cerrando vista en vivo...")
            break
            
except KeyboardInterrupt:
    print("\nInterrupción forzada detectada.")
finally:
    # Cerrar cámara y destruir todas las ventanas de OpenCV
    picam2.stop()
    cv2.destroyAllWindows()
    print("Prueba finalizada.")
