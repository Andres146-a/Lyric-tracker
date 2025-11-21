import pyautogui
import time

print("🔍 Probando control de PowerPoint...")
print("Abre PowerPoint en modo presentación y ejecuta este test")

input("Presiona Enter cuando estés listo...")

print("Enviando tecla RIGHT en 3 segundos...")
time.sleep(3)

pyautogui.press('right')
print("✅ Tecla RIGHT enviada")

print("¿Cambió el slide?")