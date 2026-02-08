import pyaudio
import vosk
import json
import argparse
import win32com.client
import pythoncom
import time
import os
import glob
import signal
import sys
from lyric_tracker import LyricTracker, load_lyrics_data
import pyautogui
import tkinter as tk
from threading import Thread
import keyboard 
from scipy.signal import resample_poly
from pedalboard import Pedalboard, Compressor, NoiseGate, Gain, PeakFilter, LowShelfFilter
from pedalboard.io import AudioStream
import numpy as np
_system_running = True

class PowerPointSync:
    def __init__(self, tracker):
        self.tracker = tracker
        self.app = None
        self.presentation = None
        self.last_known_slide = None
        self.is_connected = False
        self._connect()
        self.coro_repetitions = 0

    def _connect(self):
        try:
            pythoncom.CoInitialize()
            self.app = win32com.client.Dispatch("PowerPoint.Application")
            time.sleep(0.5)
            self.presentation = self.app.ActivePresentation
            self.is_connected = True
            
            try:
                current = self.presentation.SlideShowWindow.View.Slide.SlideIndex
                self.last_known_slide = current
                print(f"✅ PowerPoint en slide: {current}, Tracker en: {self.tracker.current_slide}")
            except:
                print("✅ Sincronización con PowerPoint activada (no en modo presentación)")
                
        except Exception as e:
            print(f"⚠️ No se pudo conectar a PowerPoint: {e}")
            self.is_connected = False

    def check_current_slide(self):
        if not self.is_connected:
            return
            
        try:
            try:
                current = self.presentation.SlideShowWindow.View.Slide.SlideIndex
            except:
                try:
                    current = self.app.ActiveWindow.Selection.SlideRange.SlideIndex
                except:
                    return

            if self.last_known_slide is None:
                self.last_known_slide = current
                return

            # NUEVO FIX PRINCIPAL: Si PowerPoint está en el mismo slide que el tracker, ignorar
            if current == self.tracker.current_slide:
                # Mismo slide → no hacemos nada, evitamos recargas infinitas
                self.last_known_slide = current  # Actualizamos para estar seguros
                return

            # Solo si es un slide diferente al del tracker, sincronizamos
            if time.time() - getattr(self, '_last_change_time', 0) < 0.6:
                return

            print(f"PowerPoint cambió → Slide {current}")

            slide_text = self.presentation.Slides(current).Shapes[0].TextFrame.TextRange.Text.strip()
            if not slide_text:
                print(f"⚠️ Slide {current} está vacío → Manteniendo tracker en último slide válido")

            slide_key = f"slide_{current}"
            if slide_key not in self.tracker.lyrics_data:
                print(f"⚠️ Slide {current} no existe en la canción → Manteniendo tracker en último slide válido")
                self.last_known_slide = current
                return

            # Sincronización real
            self.tracker.current_slide = current
            self.tracker.current_word_index = 0
            self.tracker.last_progress_time = time.time()
            self.tracker.last_strong_word_time = time.time()
            self.tracker.preloaded_slides.pop(current, None)

            self.tracker.force_reload_current_slide()  # recarga limpia
            self.tracker.preloaded_slides.pop(current, None)
            self.tracker._preload_slides_ahead(3)

            self.tracker.current_slide_metadata = self.tracker.get_current_slide_metadata()

            direccion = "Retroceso" if current < self.last_known_slide else "Avance"
            print(f"{direccion} detectado → Slide {current} recargado 100% limpio")

            self.last_known_slide = current
            self._last_change_time = time.time()
            print(f"Sincronizado → Slide {current}")

        except Exception as e:
            pass
def signal_handler(sig, frame):
    global _system_running
    print('\n🎯 RECIBIDA SEÑAL DE INTERRUPCIÓN - Cerrando limpiamente...')
    _system_running = False

class Overlay:
    def __init__(self, tracker):
        self.tracker = tracker
        self.root = tk.Tk()
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.geometry("400x100+50+50")
        self.root.configure(bg='black')
        self.label = tk.Label(self.root, fg="lime", bg="black", font=("Arial", 16, "bold"))
        self.label.pack(expand=True)
        self.update_overlay()

    def update_overlay(self):
        slide = self.tracker.current_slide
        total = len(self.tracker.lyrics_data)
        words = self.tracker.get_current_slide_text()
        progress = (self.tracker.current_word_index / len(words) * 100) if words else 0
        text = f"Slide {slide}/{total} | {self.tracker.current_word_index}/{len(words)} | {progress:.0f}%"
        self.label.config(text=text)
        self.root.after(200, self.update_overlay)

    def run(self):
        self.root.mainloop()

class BalancedAudioProcessor:
    def __init__(self, model_path, lyrics_data):
        global _system_running
        _system_running = True
        
        signal.signal(signal.SIGINT, signal_handler)
        self.overlay = None
        self.is_paused = False          # ← Inicializamos pausa
        self.pause_start_time = None
        
        keyboard.add_hotkey('f10', lambda: self.toggle_pause())
        print("🔘 Tecla F10 para PAUSAR/RESUMIR el seguimiento")
        
        self.overlay_thread = None
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(False)
        self.recognizer.SetPartialWords(False)
        
        print("🔄 Inicializando LyricTracker...")
        
        available_slides = []
        for key in lyrics_data.keys():
            if key.startswith("slide_"):
                try:
                    num = int(key.replace("slide_", ""))
                    available_slides.append(num)
                except ValueError:
                    continue
        
        if available_slides:
            first_available_slide = min(available_slides)
            print(f"📊 Slides disponibles en JSON: {sorted(available_slides)}")
            print(f"🎯 Configurando slide inicial del tracker: {first_available_slide}")
            self.tracker = LyricTracker(lyrics_data, start_slide=first_available_slide)
        else:
            print("⚠️ No se encontraron slides, usando slide 1 por defecto")
            self.tracker = LyricTracker(lyrics_data, start_slide=1)
        
        # ← AQUÍ SÍ: después de crear el tracker
        self.tracker.processor = self   # ← Ahora sí existe self.tracker
        
        print("🔄 Inicializando PowerPointSync...")
        self.ppt_sync = PowerPointSync(self.tracker)
        
        print(f"🎯 ESTADO FINAL - Tracker slide: {self.tracker.current_slide}, PowerPointSync slide: {self.ppt_sync.last_known_slide}")
        
        self.is_listening = True
        self.manual_control_active = False
        self.song_finished = False
        
        self.config = self._load_config()
        
        self.chunk_size = self.config["audio"]["chunk_size"]
        self.processing_interval = self.config["audio"]["processing_interval"]
        self.sleep_time = self.config["audio"]["sleep_time"]
        
        self.performance_metrics = {
            'total_processing_time': 0,
            'audio_captures': 0,
            'slide_changes': 0,
            'last_slide_change_time': None,
            'slide_times': [],
            'processing_times': []
        }
        
        print("⚡ Procesador de Audio OPTIMIZADO con controles manuales")
        print(f"🎯 Configuración: chunk_size={self.chunk_size}, interval={self.processing_interval}")
        
        print("F8 = Forzar siguiente slide | F9 = Reinicio total")
        keyboard.add_hotkey('f8', lambda: self.force_next_slide())
        keyboard.add_hotkey('f9', lambda: self.tracker.resetear_a_inicio())

    def _load_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("✅ Configuración cargada desde config.json")
            return config
        except Exception as e:
            print(f"❌ Error cargando config.json: {e}")
            return {
                "audio": {
                    "sample_rate": 16000,
                    "channels": 1,
                    #"chunk_size": 512,
                    #"processing_interval": 0.05,
                    #"sleep_time": 0.01
                    "chunk_size": 256,
                    "processing_interval": 0.2, 
                    "sleep_time": 0.005
                },
                "powerpoint": {
                    "advance_key": "pagedown",
                    "back_key": "pageup"
                }
            }
    
    #Funcioón para pausar el tracker:    
    def toggle_pause(self):
        # Toggleamos el estado PRIMERO
        self.is_paused = not self.is_paused
        
        print(f"⏸️ {'PAUSADO' if self.is_paused else 'REANUDADO'}")
        
        if self.is_paused:
            print("⏸️ PAUSA ACTIVADA - El seguimiento se detendrá hasta que se reanude")
            try:
                self.stream.stop()  # sounddevice usa .stop()
            except:
                pass
            self.pause_start_time = time.time()
            self.recognizer.Reset()  # Limpia contexto de Vosk
        else:
            print("▶️ REANUDANDO - El seguimiento continuará ahora")
            try:
                self.stream.start()  # sounddevice usa .start()
            except:
                pass
            
            # Ajustamos timers para que la pausa no cuente como "stuck"
            if self.pause_start_time is not None:
                pause_duration = time.time() - self.pause_start_time
                self.tracker.last_progress_time += pause_duration
                self.tracker.last_slide_change_time += pause_duration
                # Reseteamos stuck para evitar saltos inmediatos
                if hasattr(self.tracker, 'stuck_start_time'):
                    self.tracker.stuck_start_time = None
            
            self.pause_start_time = None  # Limpio para próxima pausa
            
            # Impulso inteligente después de pausa en coro
                     # Impulso suave después de pausa en coro
            if self.tracker.is_current_slide_duplicated() and self.tracker.coro_fase >= 1:
                half = self.tracker.get_duplication_split_point()
                if self.tracker.current_word_index < half and self.tracker.current_word_index > int(half * 0.4):
                    print("Impulso suave después de pausa → Ayudando a cruzar")
                    self.tracker.coro_fase = 2
                    self.tracker.coro_crossed = True
                    self.tracker.current_word_index = half
                
    def _main_loop_with_denoising(self):
        global _system_running
        last_processing_time = 0
        audio_buffer = b""
        buffer_size = 1


        while _system_running and self.is_listening:
            if getattr(getattr(self, 'processor', None), 'is_paused', False):
                time.slep(0.1)
                continue
            try:
                current_time = time.time()

                # Vaciar la cola lo más rápido posible
                try:
                    while not self.audio_queue.empty():
                        data = self.audio_queue.get_nowait()
                        audio_buffer += data
                        self.performance_metrics['audio_captures'] += 1
                except:
                    pass

                # Procesar cuando tengamos suficiente audio
                if (len(audio_buffer) >= self.chunk_size * buffer_size or
                    current_time - last_processing_time >= self.processing_interval):
                    process_start = time.time()
                    try:
                        if _system_running and self.recognizer.AcceptWaveform(audio_buffer):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '').strip()
                            if text:
                                print(f"{text}")
                                self._process_text_for_advance(text)
                        if _system_running:
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get('partial', '').strip()
                            if partial_text:
                                self._process_text_for_advance(partial_text, is_partial=True)
                    except Exception as e:
                        if "waveform" in str(e).lower():
                            pass  # Ignorar error de waveform vacío durante pausa
                        else:
                            print(f"Error Vosk: {e}")
                    audio_buffer = b""
                    last_processing_time = current_time

                    process_time = time.time() - process_start
                    self.performance_metrics['processing_times'].append(process_time)

                # Sincronización con PowerPoint
                if hasattr(self, 'ppt_sync'):
                    self.ppt_sync.check_current_slide()

                time.sleep(self.sleep_time)

            except KeyboardInterrupt:
                print("\nINTERRUPCIÓN - Cerrando...")
                _system_running = False
                break
            except Exception as e:
                if _system_running:
                    print(f"Error en loop: {e}")

        print("Loop principal terminado")






    def start_listening(self):
        import sounddevice as sd
        import webrtcvad
        import numpy as np
        import queue
        from scipy.signal import wiener, resample_poly

        print("🔥 Iniciando captura con REDUCCIÓN DE RUIDO WEBRTC + WIENER (¡Más estable que rnnoise!)")

        # Cola para audio limpio
        self.audio_queue = queue.Queue(maxsize=100)
        
        # Inicializar VAD (Voice Activity Detection) de WebRTC
        self.vad = webrtcvad.Vad(2)  # Nivel agresivo: 3 = detecta solo voz clara
        
        # Frame size para VAD (10ms a 48kHz = 480 samples)
        self.frame_duration = 10  # ms
        self.sample_rate = 48000
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)

        def resample_audio(audio_np, orig_sr=48000, target_sr=16000):
            if orig_sr == target_sr:
                return audio_np
            ratio = target_sr / orig_sr
            n_samples = int(len(audio_np) * ratio + 0.5)
            if n_samples == 0:
                return audio_np
            return resample_poly(audio_np.astype(float), n_samples, 1)

        def audio_callback(indata, frames, time_info, status):
            if status:
                return
            
            # 1. Audio crudo a float32
            audio_float = indata[:, 0].astype(np.float32) / 32768.0  # [-1, 1]
            
            # 2. Normalización de volumen (evita clipping cuando sube de tono)
            max_val = np.max(np.abs(audio_float))
            if max_val > 0.01:  # solo si hay señal
                audio_float = audio_float / max_val * 0.9  # gain suave
            
            # 3. Resample perfecto 48kHz → 16kHz con scipy (calidad profesional)
            audio_16k = resample_poly(audio_float, 16000, 48000)
            
            # 4. Convertir a int16 y bytes
            audio_int16 = (audio_16k * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            if hasattr(self, 'preprocess_audio'):  # Seguridad por si no está definida
                processed_bytes = self.preprocess_audio(audio_bytes, sample_rate=16000)
            else:
                processed_bytes = audio_bytes  # fallback
            try:
                self.audio_queue.put_nowait(audio_bytes)
            except queue.Full:
                pass

        # Stream a 48kHz (mejor para VAD/Wiener)
        self.stream = sd.InputStream(
            samplerate=48000,
            blocksize=960,  # 20ms chunks (múltiplo de 10ms para VAD)
            dtype='int16',
            channels=1,
            callback=audio_callback
        )
        self.stream.start()

        print("🎤 REDUCCIÓN DE RUIDO ACTIVA - ¡Solo voz clara, adiós batería y eco!")
        print("   (Prueba: pon música fuerte y habla → solo te oye a ti)")
        print("Presiona Ctrl+C para detener")

        self._main_loop_with_denoising()

    def _process_text_for_advance(self, text, is_partial=False):
        """Procesa texto (completo o parcial) y decide si avanzar slide"""
        if not _system_running:
            return

        # Comandos de voz primero
        if self._process_commands_and_tracking(text):
            return

        # Procesar con el tracker
        result = self.tracker.process_recognized_text(text)
        
        if result == "CHANGE_SLIDE":
            tag = " (PARCIAL)" if is_partial else ""
            print(f"🚨 ¡CAMBIO DE SLIDE!{tag}")
            self._change_slide()


    def stop_listening(self):
        global _system_running
        _system_running = False
        self.is_listening = False

        print("🛑 Cerrando recursos de audio...")
        try:
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            if hasattr(self, 'vad'):
                del self.vad  # Limpia VAD
        except:
            pass

        self._print_performance_summary()
        print("Sistema detenido correctamente")


    
    def preprocess_audio(self, chunk: bytes, sample_rate: int = 16000) -> bytes:
        """
        Procesa un chunk de audio crudo (bytes) con pedalboard.
        """
        audio_array = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        
        if len(audio_array.shape) == 1:
            audio_array = audio_array[:, np.newaxis]

        board = Pedalboard([
            NoiseGate(threshold_db=-42.0, ratio=10.0, attack_ms=2.0, release_ms=150.0),
            LowShelfFilter(cutoff_frequency_hz=120, gain_db=+2.0, q=1.0),
            PeakFilter(cutoff_frequency_hz=3500, gain_db=+5.0, q=1.4),
            PeakFilter(cutoff_frequency_hz=8000, gain_db=+4.0, q=2.0),
            Compressor(threshold_db=-25.0, ratio=3.0, attack_ms=10.0, release_ms=100.0),
            Compressor(threshold_db=-22.0, ratio=4.0, attack_ms=5.0, release_ms=80.0),
            Compressor(threshold_db=-20.0, ratio=5.0, attack_ms=3.0, release_ms=60.0),
            Gain(gain_db=0.0)
        ])

        processed_array = board(audio_array, sample_rate)
        processed_int16 = (processed_array * 32768.0).clip(-32768, 32767).astype(np.int16)
        return processed_int16.tobytes()
        
    def _process_commands_and_tracking(self, text):
        if not hasattr(self, '_last_command_time'):
            self._last_command_time = 0
            
        current_time = time.time()
        
        if current_time - self._last_command_time < 2.0:
            return False
            
        if self._check_special_commands(text):
            self._last_command_time = current_time
            return True
        
        if self._detect_early_transition(text):
            print("🎯 Detección temprana ACTIVADA!")
            self._change_slide()
            self._last_command_time = current_time
            return True
            
        return False

    def _check_special_commands(self, text):
        text_lower = text.lower()
        
        short_words = ['atrás', 'no', 'si', 'ya', 'ok']
        if text_lower in short_words and len(text_lower) < 4:
            return False
        """
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

        """
      

        
        return False

    def _detect_early_transition(self, text):
        if not self.tracker:
            return False

        # 🚫 Nunca usar detección temprana en slides duplicados (coros)
        if self.tracker.is_current_slide_duplicated():
            return False

        current_slide_words = self.tracker.get_current_slide_text()
        if not current_slide_words:
            return False
                
        progress_ratio = self.tracker.current_word_index / len(current_slide_words)
        if progress_ratio >= 0.75:
            text_words = text.lower().split()
            slide_final_words = current_slide_words[-2:]  # más estable que 4
                
            for word in text_words:
                if word in slide_final_words:
                    print(f"🎯 Palabra final detectada: '{word}'")
                    return True
                        
        return False


    def _extract_slide_number(self, text):
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else None

    def _change_slide(self):
        if self.manual_control_active:
            return
        try:
            self.manual_control_active = True
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("PowerPoint.Application")
            view = app.ActivePresentation.SlideShowWindow.View
            
            # NUEVO: Verificamos si realmente hay siguiente slide
            if not self.tracker.next_slide():
                # No hay más slides → marcamos terminada y no avanzamos PowerPoint
                if not self.song_finished:
                    print("¡CANCIÓN TERMINADA! Gracias Jesús")
                    self.song_finished = True
                    self._go_to_black_slide()
                return  # Salimos sin avanzar

            view.Next()
            print("SLIDE AVANZADO CON COM → 100% garantizado")

            # Actualizamos el tracker (esto recarga el slide limpio)
            self.tracker.next_slide()

            # ==================== LIMPIEZA CRÍTICA DEL BUFFER DE AUDIO ====================
            # 1. Vaciamos toda la cola de audio pendiente (elimina residual del slide anterior)
            cleared_chunks = 0
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    cleared_chunks += 1
                except queue.Empty:
                    break
            if cleared_chunks > 0:
                print(f"BUFFER AUDIO LIMPIADO → {cleared_chunks} chunks residuales descartados")

            # 2. Reiniciamos completamente el recognizer de Vosk para limpiar su estado interno
            #    (Vosk guarda contexto de ~0.5s para mejorar precisión, pero eso causa "mezcla")
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(False)
            self.recognizer.SetPartialWords(False)
            print("VOSK REINICIADO → Estado interno limpio, listo para nuevo slide")
            # ============================================================================

            self.performance_metrics['slide_changes'] += 1
            self.performance_metrics['last_slide_change_time'] = time.time()

        except Exception as e:
            # === Backup con tecla si COM falla ===
            try:
                next_slide_num = self.tracker.current_slide + 1
                next_key = f"slide_{next_slide_num}"
                if next_key in self.tracker.lyrics_data:
                    pyautogui.press('right')
                    pyautogui.press('right')
                    self.tracker.next_slide()
                    print("Backup: avanzado con tecla right")

                    # === APLICAMOS LA MISMA LIMPIEZA EN EL BACKUP ===
                    cleared_chunks = 0
                    while not self.audio_queue.empty():
                        try:
                            self.audio_queue.get_nowait()
                            cleared_chunks += 1
                        except queue.Empty:
                            break
                    if cleared_chunks > 0:
                        print(f"BUFFER AUDIO LIMPIADO (backup) → {cleared_chunks} chunks descartados")

                    self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
                    self.recognizer.SetWords(False)
                    self.recognizer.SetPartialWords(False)
                    print("VOSK REINICIADO (backup)")
                    # ===============================================

                else:
                    if not self.song_finished:
                        print("¡CANCIÓN TERMINADA! Gracias Jesús")
                        self.song_finished = True
                        self._go_to_black_slide()
            except Exception as backup_e:
                print(f"No se pudo avanzar (ni COM ni backup): {backup_e}")
        finally:
            self.manual_control_active = False

    def _go_to_black_slide(self):
        """Va al slide negro final (o crea uno si no existe)"""
        try:
            pythoncom.CoInitialize()
            app = win32com.client.Dispatch("PowerPoint.Application")
            pres = app.ActivePresentation
            total_slides = pres.Slides.Count
            
            # Si tienes un slide negro al final (ej. slide 10), ve ahí:
            black_slide_index = total_slides  # o pon 10, 20, etc.
            pres.SlideShowWindow.View.GotoSlide(black_slide_index)
            print("FONDO NEGRO activado")
        except:
            # Si no hay slide negro, al menos sale del último
            try:
                pyautogui.press('b')  # Tecla B = pantalla negra en PowerPoint
                print("Pantalla negra activada (tecla B)")
            except:
                pass
    def _go_back_slide(self):
        if self.manual_control_active or not self.tracker:
            return
        try:
            self.manual_control_active = True
            self.tracker.previous_slide()        # ← Usa el nuevo método
            pyautogui.press('left')              # o 'pageup' según tu config
            print(f"RETROCESO MANUAL → Slide {self.tracker.current_slide}")
        finally:
            self.manual_control_active = False

    def force_next_slide(self):
        """F8 → Avanza manualmente (tú controlas)"""
        if not self.tracker:
            return
        print("AVANCE MANUAL (F8) → Forzando siguiente slide")
        self.tracker.next_slide()         
        self._change_slide()               
    def _go_to_slide(self, slide_number):
        if not self.tracker:
            return
            
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
        print("\n" + "="*50)
        print("📊 RESUMEN DE RENDIMIENTO")
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

        if metrics['processing_times']:
            avg_process = sum(metrics['processing_times']) / len(metrics['processing_times'])
            print(f"⚡ Procesamiento promedio: {avg_process:.3f}s")

        print("="*50)

    def stop_listening(self):
        global _system_running
        _system_running = False
        self.is_listening = False

        print("Cerrando recursos de audio...")
        try:
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            if hasattr(self, 'denoiser'):
                # Forzar limpieza limpia para evitar el warning
                self.denoiser = None
        except:
            pass

        self._print_performance_summary()
        print("Sistema detenido correctamente")




def get_available_songs():
    json_files = glob.glob("*_lyrics.json")
    default_files = []
    if os.path.exists("lyrics_data.json"):
        default_files = ["lyrics_data.json"]
    
    all_files = default_files + json_files
    return sorted(list(set(all_files)))

def select_song_interactively():
    available_songs = get_available_songs()
    
    if not available_songs:
        print("❌ No se encontraron archivos de letras (.json)")
        print("   → Coloca archivos _lyrics.json en esta carpeta")
        return None
    
    print("\n🎵 CANCIONES DISPONIBLES:")
    for i, song_file in enumerate(available_songs, 1):
        if song_file == "lyrics_data.json":
            song_name = "Canción Actual"
        else:
            song_name = song_file.replace("_lyrics.json", "").replace("_", " ").title()
        print(f"   {i}. {song_name} ({song_file})")
    
    while True:
        try:
            selection = input(f"\n🎤 Selecciona canción (1-{len(available_songs)}): ").strip()
            
            if not selection:
                selected_file = available_songs[0]
                print(f"🎯 Usando canción por defecto: {selected_file}")
                return selected_file
            
            selection_idx = int(selection) - 1
            if 0 <= selection_idx < len(available_songs):
                selected_file = available_songs[selection_idx]
                print(f"🎯 Canción seleccionada: {selected_file}")
                return selected_file
            else:
                print(f"❌ Selección inválida. Usa 1-{len(available_songs)}")
                
        except ValueError:
            print("❌ Ingresa un número válido")
        except KeyboardInterrupt:
            print("\n👋 Saliendo...")
            return None

def main():
    print("INICIANDO SISTEMA CON CONTROLES MANUALES")
    
    parser = argparse.ArgumentParser(description='Sistema de Seguimiento de Letras para PowerPoint')
    parser.add_argument('--song', '-s', help='Archivo JSON de la canción a usar')
    args = parser.parse_args()
    
    # ✅ SELECCIÓN POR ARGUMENTO O INTERACTIVA
    if args.song:
        selected_song = args.song
        if not selected_song.endswith('.json'):
            selected_song += '_lyrics.json'
        print(f"🎯 Canción desde argumento: {selected_song}")
    else:
        selected_song = select_song_interactively()
        if not selected_song:
            return
    
    # Verificar que el archivo existe
    if not os.path.exists(selected_song):
        print(f"❌ El archivo {selected_song} no existe")
        available = get_available_songs()
        if available:
            print("🎵 Archivos disponibles:")
            for song in available:
                print(f"   - {song}")
        return
    
    # ✅ CARGAR LA CANCIÓN SELECCIONADA (SOLO UNA VEZ)
    lyrics_data = load_lyrics_data(selected_song)
    
    if not lyrics_data:
        print(f"ERROR: No se pudo cargar {selected_song}")
        input("\nPresiona Enter para salir...")
        return

    # ✅ MOSTRAR INFO DE LA CANCIÓN SELECCIONADA
    if selected_song == "lyrics_data.json":
        song_name = "Canción Actual"
    else:
        song_name = selected_song.replace("_lyrics.json", "").replace("_", " ").title()
    print(f"\n🎵 CANCIÓN: {song_name}")
    print(f"📁 Archivo: {selected_song}")

    # ✅ VERIFICAR SLIDES EXISTENTES EN DETALLE
    print("\n🔍 DETALLES DE SLIDES DISPONIBLES:")
    available_slides = []
    for key, value in lyrics_data.items():
        if key.startswith("slide_"):
            try:
                num = int(key.replace("slide_", ""))
                available_slides.append(num)
                
                if isinstance(value, dict) and "processed_text" in value:
                    words = value["processed_text"]
                    print(f"   {key}: {len(words)} palabras → {words[:3]}...")
                elif isinstance(value, list):
                    print(f"   {key}: {len(value)} palabras → {value[:3]}...")
                else:
                    print(f"   {key}: FORMATO INESPERADO")
                    
            except ValueError:
                print(f"   {key}: NOMBRE NO VÁLIDO")
    
    if not available_slides:
        print("❌ No se encontraron slides válidos en el archivo")
        input("\nPresiona Enter para salir...")
        return
    
    print(f"📊 Total de slides válidos: {len(available_slides)}")
    print(f"🎯 Rango de slides: {min(available_slides)} a {max(available_slides)}")
    
    # ✅ ADVERTENCIA SI POWERPOINT ESTÁ EN UN SLIDE QUE NO EXISTE
    try:
        import win32com.client
        pythoncom.CoInitialize()
        app = win32com.client.Dispatch("PowerPoint.Application")
        presentation = app.ActivePresentation
        ppt_slide = presentation.SlideShowWindow.View.Slide.SlideIndex
        
        if ppt_slide not in available_slides:
            print(f"\n⚠️ ADVERTENCIA: PowerPoint está en slide {ppt_slide}, pero este slide NO existe en el JSON")
            print(f"   → Los slides disponibles son: {sorted(available_slides)}")
            print(f"   → Por favor, coloca PowerPoint en el slide {min(available_slides)}")
            print(f"   → Presiona Enter para continuar (el sistema ajustará automáticamente) o Ctrl+C para salir")
            input()
            
            try:
                target_slide = min(available_slides)
                presentation.SlideShowWindow.View.GotoSlide(target_slide)
                print(f"✅ PowerPoint movido al slide {target_slide}")
            except Exception as e:
                print(f"⚠️ No se pudo mover PowerPoint: {e}")
                print(f"   → Por favor, mueve manualmente PowerPoint al slide {min(available_slides)}")
                
    except Exception as e:
        print(f"⚠️ No se pudo verificar el slide actual de PowerPoint: {e}")
        print("   → Asegúrate de que PowerPoint esté abierto en modo presentación")
    # version antigua pero buena.
    model_path = "models/vosk-model-es-0.42/vosk-model-es-0.42" 
    #model_path = "models/modelo_cristiano_final"

    
    try:
        processor = BalancedAudioProcessor(model_path, lyrics_data)
        processor.start_listening()
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        input("\nPresiona Enter para cerrar...")
    finally:
        print("PROGRAMA FINALIZADO")

if __name__ == "__main__":
    main()