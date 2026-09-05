from gpiozero import MotionSensor
import time

print("--- Iniciando calibración avanzada de Sensor PIR ---")
print("Recuerda: Ajusta el potenciómetro de sensibilidad (Sx) al máximo para los 6 metros.")

# Pin 11 físico = GPIO 17
pir = MotionSensor(17)

# Variables para medir el tiempo que tarda el carro en pasar
tiempo_inicio = 0

def movimiento_detectado():
    global tiempo_inicio
    tiempo_inicio = time.time()
    hora = time.strftime('%H:%M:%S')
    print(f"\n[{hora}] 🚨 ¡Movimiento detectado! (Inicio de lectura)")

def movimiento_finalizado():
    duracion = time.time() - tiempo_inicio
    hora = time.strftime('%H:%M:%S')
    print(f"\n[{hora}] 🟢 Movimiento cesó. Duración del evento: {duracion:.2f} segundos.")

# Asignar los eventos para que se disparen solos en segundo plano
pir.when_motion = movimiento_detectado
pir.when_no_motion = movimiento_finalizado

print("\nSistema activo. Monitoreando en tiempo real... (Presiona Ctrl+C para salir)")

try:
    while True:
        # Imprime el estado en la misma línea para que veas que el sistema está vivo
        estado = "Detectando (HIGH)" if pir.motion_detected else "Despejado (LOW)  "
        print(f"Estado del pin 17: {estado}", end="\r")
        time.sleep(0.2)
        
except KeyboardInterrupt:
    print("\nPrueba finalizada. Limpiando pines...")
