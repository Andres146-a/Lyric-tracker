import pyaudio
import vosk
import json
import time
from lyric_tracker import LyricTracker, load_lyrics_data
import pyautogui

class OptimizedAudioProcessor:
    def __init__(self, model_path, lyrics_data):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.tracker = LyricTracker(lyrics_data)
        self.is_listening = True
        
        # CONFIGURACIÓN OPTIMIZADA
        self.chunk_size = 1500  # Chunk más pequeño para menor latencia
        
        # Métricas
        self.performance_metrics = {
            'total_processing_time': 0,
            'audio_captures': 0,
            'slide_changes': 0,
            'last_slide_change_time': None,
            'slide_times': []
        }
        
        print("⚡ Procesador de Audio OPTIMIZADO Inicializado")
        print("💡 Máxima velocidad + Precisión equilibrada")
    
    def start_listening(self):
        """Versión optimizada de escucha"""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print("🎤 Escuchando... (Modo RÁPIDO - Ctrl+C para detener)")
            print("💡 Sistema optimizado para menor latencia")
            
            self._main_loop()
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self._print_performance_summary()
            self.stop_listening()
    
    def _main_loop(self):
        """Loop principal OPTIMIZADO"""
        last_processing_time = 0
        processing_interval = 0.08  # ← 80ms (más rápido)
        loop_start_time = time.time()
        
        while self.is_listening:
            try:
                current_time = time.time()
                self.performance_metrics['total_processing_time'] = current_time - loop_start_time
                
                # PROCESAR MÁS FRECUENTEMENTE
                if current_time - last_processing_time >= processing_interval:
                    process_start = time.time()
                    
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.performance_metrics['audio_captures'] += 1
                    
                    # PROCESAMIENTO RÁPIDO: Enfocarse en resultados parciales
                    partial_result = json.loads(self.recognizer.PartialResult())
                    partial_text = partial_result.get('partial', '').strip()
                    
                    if partial_text and len(partial_text.split()) >= 2:
                        print(f"🎤 {partial_text}")
                        
                        # Procesar parcial INMEDIATAMENTE para mejor respuesta
                        if self._check_special_commands(partial_text):
                            continue
                        
                        # Procesar seguimiento con texto parcial
                        result = self.tracker.process_recognized_text(partial_text)
                        if result == "CHANGE_SLIDE":
                            print("🚨 ¡CAMBIO RÁPIDO DE SLIDE!")
                            self._change_slide()
                    
                    # Procesar reconocimiento completo también
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '').strip()
                        
                        if text:
                            print(f"📝 {text}")
                            
                            if self._check_special_commands(text):
                                continue
                                
                            result = self.tracker.process_recognized_text(text)
                            if result == "CHANGE_SLIDE":
                                print("🚨 ¡CAMBIO DE SLIDE!")
                                self._change_slide()
                    
                    # Log de procesamiento lento
                    process_time = time.time() - process_start
                    if process_time > 0.05:  # Más estricto
                        print(f"⏱️  Procesamiento: {process_time:.3f}s")
                    
                    last_processing_time = current_time
                
                time.sleep(0.03)  # ← Pausa más corta
                
            except KeyboardInterrupt:
                print("\n🛑 Deteniendo por usuario...")
                break
            except Exception as e:
                print(f"❌ Error en loop: {e}")
    
    def _check_special_commands(self, text):
        """Comandos especiales"""
        text_lower = text.lower()
        
        if any(cmd in text_lower for cmd in ["repetir", "otra vez"]):
            self._go_back_slide()
            return True
            
        elif any(cmd in text_lower for cmd in ["atrás", "volver", "anterior"]):
            self._go_back_slide()
            return True
            
        elif any(cmd in text_lower for cmd in ["empezar", "inicio", "principio", "slide 1"]):
            self._go_to_slide(1)
            return True
            
        elif "slide" in text_lower:
            slide_num = self._extract_slide_number(text_lower)
            if slide_num and 1 <= slide_num <= 5:
                self._go_to_slide(slide_num)
                return True
        
        return False
    
    def _extract_slide_number(self, text):
        """Extrae número de slide del texto"""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else None
    
    def _go_back_slide(self):
        """Retrocede UN slide"""
        try:
            if self.tracker.current_slide > 1:
                pyautogui.press('left')
                self.tracker.current_slide -= 1
                self.tracker.current_word_index = 0
                print(f"🔙 Volviendo al Slide {self.tracker.current_slide}")
            else:
                print("⏹️ Ya estás en el primer slide")
        except Exception as e:
            print(f"❌ Error retrocediendo: {e}")
    
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
    
    def _change_slide(self):
        """Cambio de slide OPTIMIZADO"""
        try:
            change_start = time.time()
            
            pyautogui.press('pagedown')
            print("✅ Slide cambiado (RÁPIDO)")
            
            current_time = time.time()
            if self.performance_metrics['last_slide_change_time']:
                time_since_last = current_time - self.performance_metrics['last_slide_change_time']
                self.performance_metrics['slide_times'].append(time_since_last)
                print(f"🕒 Tiempo entre slides: {time_since_last:.2f}s")
                
                # FEEDBACK EN TIEMPO REAL
                if time_since_last < 15:
                    print("✅ Velocidad: ÓPTIMA")
                elif time_since_last < 20:
                    print("⚠️  Velocidad: ACEPTABLE") 
                else:
                    print("🔶 Velocidad: LENTA - Considera ajustar sensibilidad")
            
            self.performance_metrics['last_slide_change_time'] = current_time
            self.performance_metrics['slide_changes'] += 1
            
            change_time = time.time() - change_start
            print(f"⚡ Cambio completado en: {change_time:.3f}s")
            
            if not self.tracker.next_slide():
                print("🎉 **COMPLETADO** - Listo para repeticiones...")
                self.tracker.reset_tracking(2)
                
        except Exception as e:
            print(f"❌ Error cambiando slide: {e}")
    
    def _print_performance_summary(self):
        """Imprime resumen de rendimiento al final"""
        print("\n" + "="*50)
        print("📊 RESUMEN DE RENDIMIENTO OPTIMIZADO")
        print("="*50)
        
        metrics = self.performance_metrics
        total_time = metrics['total_processing_time']
        
        print(f"⏱️  Tiempo total de ejecución: {total_time:.2f}s")
        print(f"🎤 Capturas de audio procesadas: {metrics['audio_captures']}")
        print(f"🔄 Cambios de slide realizados: {metrics['slide_changes']}")
        
        if metrics['slide_times']:
            avg_slide_time = sum(metrics['slide_times']) / len(metrics['slide_times'])
            min_slide_time = min(metrics['slide_times'])
            max_slide_time = max(metrics['slide_times'])
            
            print(f"📈 Tiempo promedio entre slides: {avg_slide_time:.2f}s")
            print(f"🚀 Tiempo mínimo entre slides: {min_slide_time:.2f}s")
            print(f"🐌 Tiempo máximo entre slides: {max_slide_time:.2f}s")
            
            # Análisis de rendimiento MÁS ESTRICTO
            if avg_slide_time < 12:
                print("✅ Rendimiento: EXCELENTE - Transiciones muy fluidas")
            elif avg_slide_time < 18:
                print("⚠️  Rendimiento: BUENO - Algunas pausas breves")
            else:
                print("🔶 Rendimiento: REGULAR - Pausas notables entre slides")
                
            # Comparación con versión anterior
            previous_avg = 21.62  # Del log anterior
            improvement = ((previous_avg - avg_slide_time) / previous_avg) * 100
            print(f"📊 Mejora vs. versión anterior: {improvement:.1f}%")
        
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
    print("🚀 INICIANDO SISTEMA OPTIMIZADO PARA VELOCIDAD")
    
    lyrics_data = load_lyrics_data("lyrics_data.json")
    if not lyrics_data:
        return
    
    model_path = "models/vosk-model-small-es-0.42"
    
    processor = OptimizedAudioProcessor(model_path, lyrics_data)
    processor.start_listening()

if __name__ == "__main__":
    main()