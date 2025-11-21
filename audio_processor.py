import pyaudio
import vosk
import json
import threading
from lyric_tracker import LyricTracker, load_lyrics_data
import pyautogui

class AudioProcessor:
    def __init__(self, model_path, lyrics_data):
        """
        Inicializa el procesador de audio
        
        Args:
            model_path: Ruta al modelo de Vosk
            lyrics_data: Datos de letras cargados
        """
        # Configurar modelo Vosk
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        
        # Configurar tracker de letras
        self.tracker = LyricTracker(lyrics_data)
        
        # Configurar audio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_listening = False
        
        print("🎤 Procesador de Audio Inicializado")
    
    def start_listening(self):
        """Inicia la escucha del micrófono"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            
            self.is_listening = True
            print("🎤 Escuchando... (Presiona Ctrl+C para detener)")
            
            # Iniciar hilo de procesamiento
            self.process_thread = threading.Thread(target=self._process_audio)
            self.process_thread.start()
            
        except Exception as e:
            print(f"❌ Error al iniciar audio: {e}")
    
    def _process_audio(self):
        """Procesa el audio en tiempo real"""
        while self.is_listening:
            try:
                data = self.stream.read(4000, exception_on_overflow=False)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        self._handle_recognized_text(text)
                
                # Procesar resultado parcial para mejor respuesta en tiempo real
                partial_result = json.loads(self.recognizer.PartialResult())
                partial_text = partial_result.get('partial', '').strip()
                
                if partial_text:
                    print(f"🎤 Reconociendo: {partial_text}")
                    
            except Exception as e:
                print(f"❌ Error procesando audio: {e}")
    
    def _handle_recognized_text(self, text):
            print(f"📝 Reconocido: {text}")
    
            # PRIMERO: Verificar comandos especiales
            command_result = self._check_special_commands(text)
            if command_result:
                return
            
            # LUEGO: Procesar seguimiento normal de letras
            result = self.tracker.process_recognized_text(text)
            
            if result == "CHANGE_SLIDE":
                print("🚨 ¡CAMBIO DE SLIDE DETECTADO!")
                self._change_slide()
    
    
    def _check_special_commands(self, text):
        """Comandos mejorados"""
        text_lower = text.lower()
        
        if "repetir" in text_lower or "otra vez" in text_lower:
            self._go_back_slide()
            return True
            
        elif "atrás" in text_lower or "volver" in text_lower or "anterior" in text_lower:
            self._go_back_slide()
            return True
            
        elif "ir al principio" in text_lower or "empezar" in text_lower:
            self._go_to_slide(2)  # Ir al primer slide con letras
            return True
            
        elif "slide" in text_lower and any(word in text_lower for word in ["ir", "ve", "cambia"]):
            slide_num = self._extract_slide_number(text_lower)
            if slide_num:
                self._go_to_slide(slide_num)
                return True
        
        return False

    def _go_back_slide(self):
        """Retrocede SOLO UN slide"""
        try:
            if self.tracker.current_slide > 2:  # No retroceder antes del slide 2
                pyautogui.press('left')
                print("🔙 Retrocediendo al slide anterior")
                
                self.tracker.current_slide -= 1
                self.tracker.current_word_index = 0
                print(f"🔄 Volviendo al Slide {self.tracker.current_slide}")
            else:
                print("⏹️ Ya estás en el primer slide con letras")
                
        except Exception as e:
            print(f"❌ Error retrocediendo: {e}")
    def _go_to_slide(self, slide_number):
        """Va a un slide específico"""
        try:
            current_slide = self.tracker.current_slide
            if slide_number != current_slide:
                # Simular teclas LEFT/RIGHT según la dirección
                if slide_number < current_slide:
                    for _ in range(current_slide - slide_number):
                        pyautogui.press('left')
                else:
                    for _ in range(slide_number - current_slide):
                        pyautogui.press('right')
                
                # Actualizar tracker
                self.tracker.current_slide = slide_number
                self.tracker.current_word_index = 0
                print(f"🎯 Yendo al Slide {slide_number}")
                
        except Exception as e:
            print(f"❌ Error yendo al slide {slide_number}: {e}")

    def _extract_slide_number(self, text):
        """Extrae número de slide del comando de voz"""
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        return None
    
    def _change_slide(self):
        """Cambia slide sin terminar el programa"""
        try:
            pyautogui.press('pagedown')
            print("✅ Slide cambiado")
            
            # AVANZAR siempre, pero no detener el programa al final
            if not self.tracker.next_slide():
                print("🎉 **PRESENTACIÓN COMPLETADA** - Esperando repeticiones...")
                # NO llamar a stop_listening() - seguir escuchando
                # En lugar de terminar, resetear al primer slide con letras
                self.tracker.reset_tracking(2)  # Volver al slide 2 (primer slide con letras)
                print("🔄 Sistema reiniciado para repeticiones")
                
        except Exception as e:
            print(f"❌ Error cambiando slide: {e}")

# También modifica el LyricTracker para mejor reset:
    def reset_tracking(self, slide_number=None):
        """Reinicia el seguimiento a un slide específico"""
        if slide_number is None:
            slide_number = self._find_first_slide_with_content()
        
        self.current_slide = slide_number
        self.current_word_index = 0
        print(f"🔄 Seguimiento reiniciado al Slide {self.current_slide}")
        
        # AVANZAR siempre, pero no detener el programa al final
    def stop_listening(self):
        """Detiene la escucha"""
        self.is_listening = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        print("🛑 Escucha detenida")

def main():
    # Cargar datos de letras
    lyrics_data = load_lyrics_data("lyrics_data.json")
    if not lyrics_data:
        print("❌ No se pudieron cargar los datos de letras")
        return
    
    # Ruta al modelo de Vosk
    model_path = "models/vosk-model-small-es-0.42"
    
    try:
        # Inicializar procesador
        processor = AudioProcessor(model_path, lyrics_data)
        
        # Iniciar escucha
        processor.start_listening()
        
        # Mantener el programa corriendo
        try:
            while processor.is_listening:
                pass
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo por usuario...")
            processor.stop_listening()
            
    except Exception as e:
        print(f"❌ Error inicializando: {e}")

if __name__ == "__main__":
    main()