import pyaudio
import vosk
import json
import time
from lyric_tracker import LyricTracker, load_lyrics_data
import pyautogui

def main():
    print("🚀 INICIANDO SISTEMA RÁPIDO SIMPLIFICADO")
    
    # Cargar datos
    lyrics_data = load_lyrics_data("lyrics_data.json")
    if not lyrics_data:
        return
    
    # Inicializar componentes
    model_path = "models/vosk-model-small-es-0.42"
    model = vosk.Model(model_path)
    recognizer = vosk.KaldiRecognizer(model, 16000)
    tracker = LyricTracker(lyrics_data)
    
    # Configuración de audio
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=2000  # Chunk pequeño para velocidad
    )
    
    print("🎤 Escuchando... (Sistema RÁPIDO - Ctrl+C para detener)")
    print("💡 Después del último slide, se reinicia automáticamente")
    
    try:
        while True:
            # Leer audio
            data = stream.read(2000, exception_on_overflow=False)
            
            # Procesar reconocimiento
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').strip()
                if text:
                    print(f"📝 {text}")
                    result = tracker.process_recognized_text(text)
                    if result == "CHANGE_SLIDE":
                        print("🚨 ¡CAMBIO DE SLIDE!")
                        pyautogui.press('pagedown')
                        if not tracker.next_slide():
                            print("🎉 **COMPLETADO** - Reiniciando...")
                            tracker.reset_tracking(2)
            
            # Procesar resultado parcial para velocidad
            partial = json.loads(recognizer.PartialResult())
            partial_text = partial.get('partial', '').strip()
            if partial_text and len(partial_text.split()) >= 2:
                print(f"🎤 {partial_text}")
            
            # Pequeña pausa para controlar CPU
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo por usuario...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

if __name__ == "__main__":
    main()