import sounddevice as sd
import numpy as np
import time
from pyrnnoise import RNNoise

class AudioDenoiser:
    def __init__(self, sample_rate=48000):
        self.sample_rate = sample_rate
        self.denoiser = RNNoise(sample_rate=sample_rate)
        self.blocksize = 480  # 10ms a 48kHz
        
    def process_audio(self, audio_chunk):
        """Procesa un chunk de audio"""
        # Asegura que sea float32
        audio_float = audio_chunk.astype(np.float32).flatten()
        
        # Normaliza si es necesario
        if audio_float.max() > 1.0 or audio_float.min() < -1.0:
            audio_float = audio_float / 32768.0  # Para audio int16
            
        # Procesa con RNNoise
        cleaned = self.denoiser.process_frame(audio_float)
        
        # Convierte a int16 para salida
        return (cleaned * 32767).astype(np.int16)
    
    def start_stream(self):
        """Inicia el stream de audio"""
        def callback(indata, outdata, frames, time, status):
            if status:
                print(f"Error de audio: {status}")
                return
                
            try:
                # Procesa el audio
                cleaned_audio = self.process_audio(indata)
                outdata[:] = cleaned_audio.reshape(-1, 1)
            except Exception as e:
                print(f"Error procesando audio: {e}")
                outdata[:] = indata  # Pasa el audio sin procesar como fallback
        
        print(f"🎤 Iniciando denoiser a {self.sample_rate}Hz")
        print("Bloque de procesamiento: 480 muestras (10ms)")
        
        with sd.Stream(
            samplerate=self.sample_rate,
            blocksize=self.blocksize,
            channels=1,
            dtype='int16',
            callback=callback
        ):
            print("\n✅ Stream activo. Habla ahora...")
            print("Presiona Ctrl+C para detener")
            
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n⏹️  Stream detenido")

# Uso
if __name__ == "__main__":
    denoiser = AudioDenoiser(sample_rate=48000)
    denoiser.start_stream()