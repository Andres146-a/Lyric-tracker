import pyaudio
import vosk
import json
import time
from lyric_tracker import LyricTracker, load_lyrics_data
import pyautogui

class BalancedAudioProcessor:
    def __init__(self, model_path, lyrics_data):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(False)
        self.recognizer.SetPartialWords(False)
        
        self.tracker = LyricTracker(lyrics_data)
        self.is_listening = True

        # CARGAR CONFIGURACIÓN DESDE JSON
        self.config = self._load_config()
        
        # Usar configuración desde JSON
        self.chunk_size = self.config["audio"]["chunk_size"]
        self.processing_interval = self.config["audio"]["processing_interval"]
        self.sleep_time = self.config["audio"]["sleep_time"]

        # MÉTRICAS
        self.performance_metrics = {
            'total_processing_time': 0,
            'audio_captures': 0,
            'slide_changes': 0,
            'last_slide_change_time': None,
            'slide_times': [],
            'processing_times': []
        }

        print("⚡ Procesador de Audio OPTIMIZADO con config.json")
        print(f"🎯 Configuración: chunk_size={self.chunk_size}, interval={self.processing_interval}")

    def _load_config(self):
        """Carga la configuración desde config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("✅ Configuración cargada desde config.json")
            return config
        except Exception as e:
            print(f"❌ Error cargando config.json: {e}")
            # Configuración por defecto si hay error
            return {
                "audio": {
                    "chunk_size": 1024,
                    "processing_interval": 0.08,
                    "sleep_time": 0.02
                },
                "powerpoint": {
                    "advance_key": "pagedown",
                    "back_key": "pageup"
                }
            }

    def start_listening(self):
        """Versión que usa configuración JSON"""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.config["audio"]["channels"],
                rate=self.config["audio"]["sample_rate"],
                input=True,
                frames_per_buffer=self.chunk_size
            )

            print("🎤 Escuchando... (Configuración desde JSON)")
            self._main_loop_optimized()

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self._print_performance_summary()
            self.stop_listening()

    def _main_loop_optimized(self):
        """Loop principal usando configuración JSON"""
        last_processing_time = 0
        processing_interval = self.processing_interval
        
        audio_buffer = b""
        buffer_size = 3

        loop_start_time = time.time()

        while self.is_listening:
            try:
                current_time = time.time()
                self.performance_metrics['total_processing_time'] = current_time - loop_start_time

                # Leer audio
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_buffer += data
                self.performance_metrics['audio_captures'] += 1

                # Procesar según intervalos de configuración
                if (len(audio_buffer) >= self.chunk_size * buffer_size or 
                    current_time - last_processing_time >= processing_interval):
                    
                    process_start = time.time()
                    
                    if self.recognizer.AcceptWaveform(audio_buffer):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '').strip()

                        if text:
                            print(f"📝 {text}")

                            if not self._process_commands_and_tracking(text):
                                result = self.tracker.process_recognized_text(text)
                                if result == "CHANGE_SLIDE":
                                    print("🚨 ¡CAMBIO DE SLIDE!")
                                    self._change_slide()

                    # Procesar parciales rápidamente
                    partial_result = json.loads(self.recognizer.PartialResult())
                    partial_text = partial_result.get('partial', '').strip()
                    
                    if partial_text and len(partial_text.split()) >= 2:
                        self._process_commands_and_tracking(partial_text)

                    audio_buffer = b""
                    
                    process_time = time.time() - process_start
                    self.performance_metrics['processing_times'].append(process_time)
                    
                    if process_time > 0.05:
                        print(f"⏱️ Procesamiento: {process_time:.3f}s")

                    last_processing_time = current_time

                time.sleep(self.sleep_time)

            except KeyboardInterrupt:
                print("\n🛑 Deteniendo por usuario...")
                break
            except Exception as e:
                print(f"❌ Error en loop: {e}")

    def _change_slide(self):
        """Cambio de slide usando tecla configurada en JSON"""
        try:
            change_start = time.time()

            # USAR TECLA CONFIGURADA EN JSON
            advance_key = self.config["powerpoint"]["advance_key"]
            pyautogui.press(advance_key)
            print(f"✅ Slide cambiado con tecla: {advance_key}")

            # Calcular tiempo desde último cambio
            current_time = time.time()
            if self.performance_metrics['last_slide_change_time']:
                time_since_last = current_time - self.performance_metrics['last_slide_change_time']
                self.performance_metrics['slide_times'].append(time_since_last)
                print(f"🕒 Tiempo entre slides: {time_since_last:.2f}s")

            self.performance_metrics['last_slide_change_time'] = current_time
            self.performance_metrics['slide_changes'] += 1

            if not self.tracker.next_slide():
                print("🎉 **COMPLETADO** - Listo para repeticiones...")
                self.tracker.reset_tracking(2)

        except Exception as e:
            print(f"❌ Error cambiando slide: {e}")

    def _go_back_slide(self):
        """Retrocede usando tecla configurada en JSON"""
        try:
            if self.tracker.current_slide > 1:
                # USAR TECLA CONFIGURADA EN JSON
                back_key = self.config["powerpoint"]["back_key"]
                pyautogui.press(back_key)
                self.tracker.current_slide -= 1
                self.tracker.current_word_index = 0
                print(f"🔙 Volviendo al Slide {self.tracker.current_slide} con tecla: {back_key}")
            else:
                print("⏹️ Ya estás en el primer slide")
        except Exception as e:
            print(f"❌ Error retrocediendo: {e}")

    def _process_commands_and_tracking(self, text):
        """OPTIMIZACIÓN: Procesa comandos y tracking en una sola pasada"""
        if self._check_special_commands(text):
            return True
        
        # OPTIMIZACIÓN: Detección temprana de palabras finales
        if self._detect_early_transition(text):
            print("🎯 Detección temprana activada!")
            self._change_slide()
            return True
            
        return False
    def _detect_early_transition(self, text):
        """NUEVO: Detección temprana de final de slide"""
        current_slide_words = self.tracker.get_current_slide_text()
        if not current_slide_words:
            return False
            
        # OPTIMIZACIÓN: Si estamos en el 80% del slide y reconoce palabras finales
        progress_ratio = self.tracker.current_word_index / len(current_slide_words)
        if progress_ratio >= 0.75:  # ← Más agresivo que el 80% original
            text_words = text.lower().split()
            slide_final_words = current_slide_words[-4:]  # Últimas 4 palabras
            
            # Verificar si alguna palabra reconocida está en las finales
            for word in text_words:
                if word in slide_final_words:
                    print(f"🎯 Palabra final detectada: '{word}'")
                    return True
                    
        return False
    
    def _check_special_commands(self, text):
        """MEJORADO: Evita ejecución múltiple de comandos"""
        text_lower = text.lower()
        
        # FILTRAR PALABRAS CORTAS QUE PUEDEN SER FALSOS POSITIVOS
        short_words = ['atrás', 'no', 'si', 'ya', 'ok']
        if text_lower in short_words and len(text_lower) < 4:
            return False

        # COMANDOS CON MÁS CONTEXTO
        if any(cmd in text_lower for cmd in ["repetir", "otra vez", "repite"]):
            print("🔄 Comando: REPETIR")
            self._go_back_slide()
            return True

        elif any(cmd in text_lower for cmd in ["atrás", "volver", "anterior", "retrocede"]):
            print("🔙 Comando: VOLVER")
            self._go_back_slide()
            return True

        elif any(cmd in text_lower for cmd in ["empezar", "inicio", "principio", "slide 1", "primero"]):
            print("🏁 Comando: INICIO")
            self._go_to_slide(1)
            return True

        elif "slide" in text_lower:
            slide_num = self._extract_slide_number(text_lower)
            if slide_num and 1 <= slide_num <= 5:
                print(f"🎯 Comando: IR AL SLIDE {slide_num}")
                self._go_to_slide(slide_num)
                return True

        return False

    def _process_commands_and_tracking(self, text):
        """MEJORADO: Timer para evitar procesamiento duplicado"""
        if not hasattr(self, '_last_command_time'):
            self._last_command_time = 0
            
        current_time = time.time()
        
        # EVITAR PROCESAR EL MISMO COMANDO MUY SEGUIDO
        if current_time - self._last_command_time < 2.0:  # 2 segundos de espera
            return False
            
        if self._check_special_commands(text):
            self._last_command_time = current_time
            return True
        
        # DETECCIÓN TEMPRANA MÁS AGRESIVA
        if self._detect_early_transition(text):
            print("🎯 Detección temprana ACTIVADA!")
            self._change_slide()
            self._last_command_time = current_time
            return True
            
        return False
    def _extract_slide_number(self, text):
            """Extrae número de slide del texto"""
            import re
            numbers = re.findall(r'\d+', text)
            return int(numbers[0]) if numbers else None
    def _go_to_slide(self, slide_number):
            """Va a un slide específico"""
            try:
                current = self.tracker.current_slide
                if slide_number != current:
                    steps = abs(slide_number - current)
                    key = 'left' if slide_number < current else 'right'

                    for _ in range(steps):
                        pyautogui.press(key)
                        time.sleep(0.1)

                    self.tracker.current_slide = slide_number
                    self.tracker.current_word_index = 0
                    print(f"🎯 Yendo al Slide {slide_number}")

            except Exception as e:
                print(f"❌ Error yendo al slide: {e}")
    def _print_performance_summary(self):
        """Resumen MEJORADO con análisis de optimización"""
        print("\n" + "="*50)
        print("📊 RESUMEN DE OPTIMIZACIÓN FASE 1")
        print("="*50)

        metrics = self.performance_metrics
        total_time = metrics['total_processing_time']
        print(f"⏱️ Tiempo total: {total_time:.2f}s")
        print(f"🎤 Capturas de audio: {metrics['audio_captures']}")
        print(f"🔄 Cambios de slide: {metrics['slide_changes']}")

        if metrics['slide_times']:
            avg_slide_time = sum(metrics['slide_times']) / len(metrics['slide_times'])
            min_slide_time = min(metrics['slide_times'])
            max_slide_time = max(metrics['slide_times'])

            print(f"📈 Tiempo promedio entre slides: {avg_slide_time:.2f}s")
            print(f"🚀 Tiempo mínimo: {min_slide_time:.2f}s")
            print(f"🐌 Tiempo máximo: {max_slide_time:.2f}s")

            # ANÁLISIS DE OPTIMIZACIÓN
            print("\n🎯 ANÁLISIS DE OPTIMIZACIÓN:")
            if avg_slide_time <= 15:
                print("✅ ✅ EXCELENTE - Meta alcanzada!")
            elif avg_slide_time <= 18:
                print("✅ BUENO - Mejora significativa")
            elif avg_slide_time <= 21:
                print("📈 REGULAR - Ligera mejora")
            else:
                print("🔶 PENDIENTE - Requiere más optimización")

        if metrics['processing_times']:
            avg_process = sum(metrics['processing_times']) / len(metrics['processing_times'])
            print(f"⚡ Procesamiento promedio: {avg_process:.3f}s")

        print("="*50)

        
    def stop_listening(self):
            """Limpia recursos"""
            self.is_listening = False
            if hasattr(self, 'stream'):
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, 'audio'):
                self.audio.terminate()
            print("🛑 Sistema detenido")



def main():
    print("🚀 INICIANDO SISTEMA CON config.json")
    lyrics_data = load_lyrics_data("lyrics_data.json")
    if not lyrics_data:
        return

    model_path = "models/vosk-model-small-es-0.42"
    processor = BalancedAudioProcessor(model_path, lyrics_data)
    processor.start_listening()

if __name__ == "__main__":
    main()