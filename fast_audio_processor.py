import pyaudio
import vosk
import json
import threading
import time
from lyric_tracker import LyricTracker, load_lyrics_data
import pyautogui

class FastAudioProcessor:
    def __init__(self, model_path, lyrics_data):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.tracker = LyricTracker(lyrics_data)
        
        # Configuración optimizada
        self.sample_rate = 16000
        self.chunk_size = 2000  # Chunks más pequeños para menor latencia
        self.is_listening = False
        
        print("⚡ Procesador de Audio RÁPIDO Inicializado")
    
    def start_listening(self):
        """Inicia escucha optimizada - versión compatible"""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_listening = True
            print("🎤 Escuchando... (Modo RÁPIDO - Ctrl+C para detener)")
            
            # Hilo de procesamiento optimizado
            self.process_thread = threading.Thread(target=self._fast_process_audio)
            self.process_thread.daemon = True
            self.process_thread.start()
            
        except Exception as e:
            print(f"❌ Error al iniciar audio: {e}")
    
    def _fast_process_audio(self):
        """Procesamiento de audio optimizado para velocidad"""
        while self.is_listening:
            try:
                # Leer audio del stream directamente
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                # PROCESAMIENTO RÁPIDO: Enfocarse en resultados parciales para respuesta inmediata
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        self._handle_recognized_text(text)
                
                # RESULTADO PARCIAL FRECUENTE (para respuesta rápida)
                partial_result = json.loads(self.recognizer.PartialResult())
                partial_text = partial_result.get('partial', '').strip()
                
                if partial_text and len(partial_text.split()) >= 2:
                    print(f"🎤 {partial_text}")
                    # Procesar parcial inmediatamente para mejor respuesta
                    self._handle_partial_text(partial_text)
                
                # Pausa mínima para no saturar CPU
                time.sleep(0.03)  # Solo 30ms entre procesamientos
                    
            except Exception as e:
                if self.is_listening:  # Solo mostrar error si todavía está escuchando
                    print(f"❌ Error procesando audio: {e}")
    
    def _handle_partial_text(self, partial_text):
        """Procesa texto parcial para respuesta más rápida"""
        words = partial_text.lower().split()
        if len(words) >= 2:  # Mínimo 2 palabras para evitar falsos positivos
            result = self.tracker.process_recognized_text(words)
            if result == "CHANGE_SLIDE":
                print("🚨 ¡CAMBIO RÁPIDO DE SLIDE!")
                self._fast_change_slide()
    
    def _handle_recognized_text(self, text):
        """Maneja texto reconocido completo"""
        print(f"📝 {text}")
        result = self.tracker.process_recognized_text(text)
        if result == "CHANGE_SLIDE":
            print("🚨 ¡CAMBIO DE SLIDE!")
            self._fast_change_slide()
    
    def _fast_change_slide(self):
        """Cambio de slide optimizado"""
        try:
            # Cambio inmediato sin esperas
            pyautogui.press('pagedown')
            print("✅ Slide cambiado (RÁPIDO)")
            
            # Avanzar tracker
            if not self.tracker.next_slide():
                print("🎉 **COMPLETADO** - Listo para repeticiones...")
                self.tracker.reset_tracking(2)  # Reiniciar automáticamente al slide 2
                
        except Exception as e:
            print(f"❌ Error cambiando slide: {e}")
    
    def stop_listening(self):
        """Detiene la escucha"""
        self.is_listening = False
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'audio'):
            self.audio.terminate()
        print("🛑 Escucha detenida")