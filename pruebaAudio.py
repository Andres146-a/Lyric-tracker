import pyaudio
import vosk
import json
import time

class MiDetectionTester:
    def __init__(self, model_path):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )
        
        print("🎤 PRUEBA ESPECÍFICA DE 'MÍ'")
        print("=" * 40)
        print("🎯 Objetivo: Que reconozca 'mí'")
        print("💡 Pronuncia: 'en MÍ' (acentuado)")
        print("   'harás en MÍ'")
        print("   'creo en MÍ'")
        print("=" * 40)

    def test_mi_recognition(self):
        try:
            while True:
                data = self.stream.read(2000, exception_on_overflow=False)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        print(f"📝 Reconocido: '{text}'")
                        
                        # Análisis específico para "mí"
                        if 'mí' in text.lower():
                            print("   ✅ ✅ ✅ ¡EXCELENTE! Reconoció 'mí'")
                        elif any(word in text.lower() for word in ['me', 'de', 'o', 'le']):
                            print("   ❌ Probablemente quiso decir 'mí'")
                            print("   💡 Consejo: Pronuncia 'MÍ' más acentuado")
                            
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get('partial', '').strip()
                    if partial_text:
                        print(f"🎤 Escuchando: '{partial_text}'", end='\r')
                        
        except KeyboardInterrupt:
            print("\n🔚 Prueba finalizada")

if __name__ == "__main__":
    tester = MiDetectionTester("models/vosk-model-small-es-0.42")
    tester.test_mi_recognition()