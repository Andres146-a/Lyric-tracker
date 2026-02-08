import sounddevice as sd
import numpy as np
import queue
import threading
from pyrnnoise import RNNoise

# Cola para pasar el audio limpio a tu sistema actual de Vosk
audio_queue = queue.Queue()

# Cargar el denoiser (es instantáneo)
denoiser = RNNoise()

print("🔥 Reducción de ruido ACTIVA - Habla o canta, aunque suene la batería 🔥")

def audio_callback(indata, frames, time, status):
    # indata es int16 → lo pasamos a float32 que espera rnnoise
    audio = indata.copy().astype(np.float32)
    
    # ¡Magia! Aquí se elimina todo el ruido de fondo
    cleaned = denoiser.process_frame(audio.flatten())
    
    # Volvemos a formato int16 para que Vosk lo entienda perfectamente
    cleaned_int16 = (cleaned * 32767).astype(np.int16)
    
    # Enviamos el audio limpio a tu sistema actual (donde tengas Vosk)
    audio_queue.put(cleaned_int16.tobytes())

# Configuración del micrófono (48kHz es lo que rnnoise espera)
stream = sd.RawInputStream(
    samplerate=48000,
    blocksize=480,        # 10 ms exactly (importante para rnnoise)
    dtype='int16',
    channels=1,
    callback=audio_callback
)

# Iniciar captura
stream.start()
print("🎤 Escuchando... (presiona Ctrl+C para salir)")

try:
    while True:
        # Aquí pones tu bucle actual de Vosk
        if not audio_queue.empty():
            clean_audio_data = audio_queue.get()
            # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
            # PEGA AQUÍ TU CÓDIGO ACTUAL DE VOSK
            # En vez de leer del micrófono directo, ahora lee de clean_audio_data
            # Ejemplo rápido si usas el Recognizer normal de Vosk:
            # if recognizer.AcceptWaveform(clean_audio_data):
            #     result = recognizer.Result()
            #     print(result)
            # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
            pass
except KeyboardInterrupt:
    print("\n🛑 Deteniendo...")
finally:
    stream.stop()
    stream.close()