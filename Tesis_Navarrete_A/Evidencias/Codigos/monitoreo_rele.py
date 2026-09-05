from gpiozero import OutputDevice
from signal import pause

print("--- Iniciando prueba de Relé Permanente ---")
print("El relé se quedará encendido.")
print("Presiona Ctrl + C en tu teclado para detener la prueba y apagarlo.")

# Pin 13 físico = GPIO 27
foco = OutputDevice(27, active_high=False, initial_value=False)

# Encendemos el relé
foco.on()
print("¡Relé ENCENDIDO!")

try:
    # pause() congela el script aquí manteniendo el estado del hardware
    pause() 
except KeyboardInterrupt:
    print("\nDeteniendo prueba...")
finally:
    # Aseguramos que se apague al salir
    foco.off()
    print("Relé APAGADO. Prueba finalizada.")
