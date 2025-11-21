from fast_audio_processor import FastAudioProcessor
from lyric_tracker import load_lyrics_data

def main():
    print("🚀 INICIANDO SISTEMA RÁPIDO DE SEGUIMIENTO")
    
    # Cargar datos
    lyrics_data = load_lyrics_data("lyrics_data.json")
    if not lyrics_data:
        return
    
    # Ruta al modelo
    model_path = "models/vosk-model-small-es-0.42"
    
    try:
        # Inicializar procesador RÁPIDO
        processor = FastAudioProcessor(model_path, lyrics_data)
        processor.start_listening()
        
        # Mantener programa corriendo INDEFINIDAMENTE
        print("💡 El sistema ahora continúa después del último slide")
        print("💡 Para detener: Presiona Ctrl+C")
        
        try:
            while processor.is_listening:
                # Programa principal sigue corriendo para repeticiones
                pass
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo por usuario...")
            processor.stop_listening()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()