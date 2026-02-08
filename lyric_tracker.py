import json
import time
import re
import jellyfish 
class LyricTracker:
    def __init__(self, lyrics_data, start_slide=None):
        self.stuck_position = 0
        self.coro_fase = 0          # 0=normal | 1=primera rep | 2=segunda rep
        self.coro_crossed = False  # evita repetir el cruce del //

        self.last_strong_word_time = time.time()
        self.start_time = time.time()
        
        # ✅ CONVERTIR AUTOMÁTICAMENTE a formato compatible
        self.lyrics_data = self._convert_to_universal_format(lyrics_data)
        
        # ✅ DETECTAR PRIMER SLIDE DISPONIBLE
        available_slides = []
        for key in self.lyrics_data.keys():
            if key.startswith("slide_"):
                try:
                    num = int(key.replace("slide_", ""))
                    available_slides.append(num)
                except ValueError:
                    continue
        
        if available_slides:
            first_slide = min(available_slides)
        else:
            first_slide = 1
        
        # ✅ USAR start_slide SI SE PROVEE, SINO EL PRIMERO DISPONIBLE
        if start_slide is not None:
            self.current_slide = start_slide
        else:
            self.current_slide = first_slide
            
        print(f"🎯 Slide inicial configurado: {self.current_slide} (slides disponibles: {sorted(available_slides)})")
        
        self.current_word_index = 0
        self.is_tracking = False
        self.preloaded_slides = {}
        self.start_time = time.time()
        self.last_progress_time = time.time()
        self.stuck_start_time = None
        self.stuck_position = 0
        self.coro_repetido_detectado = False
        self.aplausos_detectados = 0
        self.last_slide_change_time = time.time()
        self.recent_progress = 0.0
        self.song_data = {}  # ← Esto también falta, lo necesitas para _is_problematic_song()

        # CARGAR CONFIGURACIÓN
        self.config = self._load_config()
        
        # Cache de palabras y DETECCIÓN DE ESTRUCTURA MEJORADA
        self.slide_words_cache = {}
        self.slide_metadata = {}
        self.slide_structures = self._analyze_slide_structures()
        self._build_words_cache()
        self.current_slide_metadata = None
        self._preload_slides_ahead(3)
        
        print("🎵 Motor FASE 1.5 - Formato Universal (Nuevo + Viejo)")

    def _convert_to_universal_format(self, lyrics_data):
        """
        Convierte CUALQUIER formato al formato que LyricTracker entiende:
        { "slide_1": ["palabra1", "palabra2", ...] }
        """
        universal_format = {}
        
        print("🔄 Analizando estructura de datos...")
        
        # CASO 1: Es una LISTA (formato muy viejo)
        if isinstance(lyrics_data, list):
            print("📋 Convertiendo LISTA → DICCIONARIO")
            for i, item in enumerate(lyrics_data, 1):
                key = f"slide_{i}"
                if isinstance(item, dict) and "processed_text" in item:
                    universal_format[key] = item["processed_text"]
                elif isinstance(item, list):
                    universal_format[key] = item
                else:
                    universal_format[key] = []
        
        # CASO 2: Es un DICCIONARIO (formato nuevo o viejo)
        elif isinstance(lyrics_data, dict):
            print("✅ USANDO DICCIONARIO EXISTENTE...")
            for key, value in lyrics_data.items():
                # ✅ PRESERVAR EL NOMBRE ORIGINAL DEL SLIDE
                if isinstance(value, dict):
                    if "processed_text" in value:
                        universal_format[key] = value["processed_text"]
                    else:
                        universal_format[key] = value
                else:
                    universal_format[key] = value
        
        print(f"✅ Conversión completada: {len(universal_format)} slides")
        print(f"📋 Slides resultantes: {list(universal_format.keys())}")
        return universal_format



    def _preload_slides_ahead(self, slides_ahead=3):
        """Pre-carga múltiples slides hacia adelante"""
        for i in range(1, slides_ahead + 1):
            slide_num = self.current_slide + i
            slide_key = f"slide_{slide_num}"
            
            if slide_key in self.slide_words_cache:
                self.preloaded_slides[slide_num] = {
                    'words': self.slide_words_cache[slide_key],
                    'metadata': self.slide_metadata.get(slide_key, [])
                }
        print(f"🔮 Pre-cargados {slides_ahead} slides adelante")

    def previous_slide(self):
        """Para cuando presiones tecla de retroceder"""
        if self.current_slide > 1:
            self.force_reload_current_slide(reset_progress=True)
            self.current_slide -= 1
            self.current_word_index = 0
            self.force_reload_current_slide()
            print(f"← RETROCESO MANUAL → Slide {self.current_slide} recargado 100% limpio")
            self._preload_slides_ahead(3)
            return True
        else:
            print("Ya estás en el primer slide")
            return False

    def next_slide(self):
        """Cambio de slide (automático o manual)"""
        self.current_slide += 1
        self.current_word_index = 0
        self.last_slide_change_time = time.time()

        # ← CLAVE: reset_progress=True para inicializar correctamente el estado del coro
        self.force_reload_current_slide(reset_progress=True)

        slide_key = f"slide_{self.current_slide}"
        self.current_slide_metadata = self.slide_metadata.get(slide_key, [])
        print(f"→ Slide {self.current_slide} cargado LIMPIO y listo para cantar desde aquí")

        self._preload_slides_ahead(3)
        return True


    def force_reload_current_slide(self, reset_progress=False):
        """
        Fuerza recarga completa del slide actual.
        reset_progress = True SOLO cuando hay cambio real de slide.
        """
        slide_key = f"slide_{self.current_slide}"

        # Limpiar caché viejo
        self.slide_words_cache.pop(slide_key, None)
        self.slide_metadata.pop(slide_key, None)
        self.preloaded_slides.pop(self.current_slide, None)

        # Reconstruir desde cero con normalización completa
        words = self.lyrics_data.get(slide_key, [])
        metadata_words = []
        content_words = []

        for word in words:
            if isinstance(word, str) and (
                word.startswith("DUPLICADO") or
                word.startswith("MITAD") or
                "MITAD1" in word
            ):
                metadata_words.append(word)
            else:
                cleaned = word.lower()
                cleaned = cleaned.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                cleaned = re.sub(r'[^a-z]', '', cleaned)
                if cleaned:
                    content_words.append(cleaned)

        self.slide_words_cache[slide_key] = content_words
        self.slide_metadata[slide_key] = metadata_words
        self.current_slide_metadata = metadata_words

        print(
            f"RECARGA FORZADA slide {self.current_slide} → "
            f"{len(content_words)} palabras listas (normalizadas)"
        )

        # 🔑 GESTIÓN CORRECTA DEL ESTADO
        if reset_progress:
            self.current_word_index = 0
            self.last_progress_time = time.time()

            if self.is_current_slide_duplicated():
                self.coro_fase = 1
                self.coro_crossed = False
                print("🎵 CORO DETECTADO → Fase 1 iniciada")
            else:
                self.coro_fase = 0
                self.coro_crossed = False




    def _analyze_slide_structures(self):
        """Analiza duplicados - COMPATIBLE CON AMBOS FORMATOS"""
        structures = {}
        
        for slide_key, words in self.lyrics_data.items():
            # ✅ words ya es una lista limpia gracias a _convert_to_universal_format
            
            total_words = len(words)
            if total_words < 8:
                continue

            # Buscar marcador de duplicado en metadatos (si existen en formato original)
            has_duplication_marker = any(
                isinstance(w, str) and ("MITAD1" in w or "DUPLICADO" in w)
                for w in words
            )
            
            if has_duplication_marker:
                split_point = self._extract_split_point_from_metadata(words)
                structures[slide_key] = {
                    'type': 'duplicated',
                    'half_point': split_point,
                    'similarity': 1.0,
                    'total_words': total_words,
                    'source': 'metadata'
                }
                print(f"Slide duplicado por metadatos: {slide_key} (split en {split_point})")
                continue

            # Detección automática por similitud
            if total_words > 10:
                mid_point = total_words // 2
                first_half = [w.lower() if isinstance(w, str) else str(w) for w in words[:mid_point]]
                second_half = [w.lower() if isinstance(w, str) else str(w) for w in words[mid_point:]]
                
                similarity = self._calculate_similarity(first_half, second_half)
                if similarity > 0.75:
                    structures[slide_key] = {
                        'type': 'duplicated',
                        'half_point': mid_point,
                        'similarity': similarity,
                        'total_words': total_words,
                        'source': 'auto_detected'
                    }
                    print(f"Slide duplicado detectado: {slide_key} ({similarity:.0%} similitud)")
                    
        return structures
    def _extract_split_point_from_metadata(self, words):
        """Extrae el punto de división desde metadatos existentes"""
        for word in words:
            if isinstance(word, str) and word.startswith("🔄MITAD1:"):
                try:
                    return int(word.split(":")[1])
                except:
                    pass
        return len(words) // 2

    def _build_words_cache(self):
        """Cache con normalización COMPLETA de acentos"""
        for slide_key, words in self.lyrics_data.items():
            metadata_words = []
            content_words = []
            
            for word in words:
                if isinstance(word, str) and (
                    word.startswith("DUPLICADO") or 
                    word.startswith("MITAD") or 
                    "MITAD1" in word
                ):
                    metadata_words.append(word)
                else:
                    cleaned = word.lower()
                    cleaned = cleaned.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                    cleaned = re.sub(r'[^a-z]', '', cleaned)
                    if cleaned:
                        content_words.append(cleaned)
            
            self.slide_words_cache[slide_key] = content_words
            self.slide_metadata[slide_key] = metadata_words

   
    def get_current_slide_text(self):
        """Obtiene solo el contenido (sin metadatos) - 100% compatible"""
        slide_key = f"slide_{self.current_slide}"
        return self.slide_words_cache.get(slide_key, [])

    def get_current_slide_metadata(self):
        """Obtiene metadatos del slide actual"""
        slide_key = f"slide_{self.current_slide}"
        return self.slide_metadata.get(slide_key, [])

    def is_current_slide_duplicated(self):
        """Detecta si el slide actual tiene contenido duplicado"""
        slide_key = f"slide_{self.current_slide}"
        return slide_key in self.slide_structures

    def get_duplication_split_point(self):
        """Obtiene el punto de división para slides duplicados"""
        slide_key = f"slide_{self.current_slide}"
        if slide_key in self.slide_structures:
            return self.slide_structures[slide_key]['half_point']
        return len(self.get_current_slide_text()) // 2

    def _load_config(self):
        """Carga configuración desde JSON"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"❌ Error cargando config.json: {e}")
            return {
                "tracking": {
                    "change_threshold": 2,
                    "look_ahead_distance": 8,
                    "min_word_length": 2,
                    "force_change_threshold": 4
                },
                "slide_change": {
                    "long_slide_threshold": 15,
                    "progress_threshold_short": 0.80,
                    "progress_threshold_long": 0.75,
                    "remaining_words_short": 2,
                    "remaining_words_long": 3,
                    "duplicated_second_half_threshold": 0.70
                }
            }

    def _preprocess_recognized_text(self, text):
        """Preprocesamiento mínimo y escalable"""
        if isinstance(text, list):
            text = ' '.join(text)
        
        # ✅ SOLO normalización básica, NO correcciones específicas
        text_lower = text.lower().strip()
        
        # Solo aplicar normalizaciones fonéticas universales
        basic_normalizations = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ü': 'u'
        }
        
        for old, new in basic_normalizations.items():
            text_lower = text_lower.replace(old, new)
                
        return text_lower.split()

    def _detectar_repeticion_frase(self):
        metadata = self.get_current_slide_metadata()
        for m in metadata:
            if m.startswith("REPITE_ULTIMA_FRASE:"):
                return int(m.split(":")[1])
            if m.startswith("FRASE_REPETIDA:"):
                self.frase_a_repetir = m.split(":",1)[1].strip().split()
        return 0
    
    def _calculate_levenshtein(self, s1, s2):
        """Calcula distancia de Levenshtein optimizada"""
        if len(s1) < len(s2):
            return self._calculate_levenshtein(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def _phonetic_similarity(self, word1, word2):
        """Similaridad fonética basada en reglas del español"""
        
        # Reglas fonéticas del español
        phonetic_rules = [
            # Confusiones comunes de consonantes
            (['b', 'v'], 'b'),
            (['s', 'c', 'z'], 's'), 
            (['j', 'g'], 'h'),
            (['y', 'll'], 'y'),
            (['r', 'rr'], 'r'),
        ]
        
        def apply_phonetic_rules(word):
            result = word.lower()
            for group, replacement in phonetic_rules:
                for sound in group:
                    result = result.replace(sound, replacement)
            return result
        
        phonetic1 = apply_phonetic_rules(word1)
        phonetic2 = apply_phonetic_rules(word2)
        
        return phonetic1 == phonetic2


    

   


    def _context_aware_matching(self, recognized_words, current_slide_words, current_position):
        """Matching contextual CONSERVADOR - solo salta si hay buena coincidencia"""
        if current_position >= len(current_slide_words):
            return None, current_position
            
        max_search_distance = 5  # máximo 5 palabras adelante
        
        for rec_word in recognized_words:
            for offset in range(1, max_search_distance + 1):
                ctx_pos = current_position + offset
                if ctx_pos >= len(current_slide_words):
                    break
                    
                ctx_word = current_slide_words[ctx_pos]
                
                # Matching estricto: solo salta si es muy buena coincidencia
                if (jellyfish.soundex(rec_word) == jellyfish.soundex(ctx_word) and
                    jellyfish.levenshtein_distance(rec_word, ctx_word) <= 1):
                    
                    print(f"CONTEXTUAL SALTO SEGURO +{offset}: '{rec_word}' → '{ctx_word}'")
                    return ctx_word, ctx_pos + 1
        
        return None, current_position
    


    
    def _sync_from_anywhere(self, recognized_words, current_slide_words):
        """Busca palabras clave fuertes del slide y sincroniza desde cualquier parte"""
        # Palabras clave fuertes del slide actual (las que más se repiten o son únicas)
        key_words = []
        for i, word in enumerate(current_slide_words):
            if word in ["jesus", "senor", "creo", "poder", "gloria", "recibe", "manos", "levanta", "presencia", "aqui"]:
                key_words.append((word, i))
        
        for rec_word in recognized_words:
            for key, pos in key_words:
                if (jellyfish.soundex(rec_word) == jellyfish.soundex(key) or
                    jellyfish.levenshtein_distance(rec_word, key) <= 1):
                    if pos > self.current_word_index:
                        print(f"SINCRONIZACIÓN SEGURA: '{rec_word}' → '{key}' en posición {pos}")
                        self.current_word_index = pos + 1
                        return True
        return False

    

    def process_recognized_text(self, recognized_text):
        # Normalización
        text = recognized_text.lower().strip()
        text = text.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        text = re.sub(r'[^a-z\s]', ' ', text)
        if len(text) < 3:
            return "CONTINUE"

        words = [w for w in text.split() if len(w) > 1]
        if not words:
            return "CONTINUE"

        current_slide_words = [
            w.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
            for w in self.get_current_slide_text()
        ]

        old_index = self.current_word_index

        # Matching normal
        for word in words:
            if self.current_word_index >= len(current_slide_words):
                break
            expected = current_slide_words[self.current_word_index]
            if (
                jellyfish.soundex(word) == jellyfish.soundex(expected) or
                jellyfish.levenshtein_distance(word, expected) <= 2 or
                expected in word or
                word in expected or
                word[:3] == expected[:3]
            ):
                self.current_word_index += 1

        # Sincronización segura
        if (
            not self.is_current_slide_duplicated() and
            self.current_word_index < len(current_slide_words) * 0.4
        ):
            self._sync_from_anywhere(words, current_slide_words)


        # === Anti-stuck por tiempo (DESACTIVADO EN COROS) ===
        tiempo_sin_avance = time.time() - self.last_progress_time
        if (
            not self.is_current_slide_duplicated() and
            len(current_slide_words) > 10 and
            self.current_word_index > 3 and
            self.current_word_index == old_index and
            tiempo_sin_avance > 12.0
        ):
            print(f"ANTI-STUCK GLOBAL: {tiempo_sin_avance:.1f}s sin avance → Forzando cambio")
            return "CHANGE_SLIDE"

        # Actualiza tiempo si hubo progreso
        if self.current_word_index > old_index:
            self.last_progress_time = time.time()
            if self.is_current_slide_duplicated():
                progreso_coro = self.current_word_index / len(current_slide_words)
                print(f"PROGRESO CORO: {self.current_word_index}/{len(current_slide_words)} ({progreso_coro:.0%}) - Fase {self.coro_fase}")

                # === Gestión de coros duplicados (UNIVERSAL + ANTICIPACIÓN INTELIGENTE) ===
        if self.is_current_slide_duplicated():
            half_point = self.get_duplication_split_point()  # ya lo tienes como get_duplication_split_point
            total_words = len(current_slide_words)

            # Cruce tolerante (65% primera mitad)
            cross_threshold = int(half_point * 0.65)

            if self.coro_fase == 1 and not self.coro_crossed and self.current_word_index >= cross_threshold:
                print(f"CRUCE DE CORO → Segunda repetición iniciada (índice {self.current_word_index}/{half_point})")
                self.coro_fase = 2
                self.coro_crossed = True
                self.current_word_index = half_point
                self.last_progress_time = time.time()

                        # === ANTICIPACIÓN EN FASE 2 (AJUSTADO PARA DEMORARSE UN POQUITO MÁS) ===
            if self.coro_fase == 2:
                # Avance principal: ahora con 70% del slide total (más conservador que 60%)
                if self.current_word_index >= int(total_words * 0.70):  # ~15-16 palabras en 22
                    print("CORO CASI COMPLETO (70% segunda vuelta) → Cambiando con fluidez")
                    self.coro_fase = 0
                    self.coro_crossed = False
                    return "CHANGE_SLIDE"

                # Anti-stuck rápido: 8 segundos (en vez de 6) para dar más margen
                if tiempo_sin_avance > 8.0 and self.current_word_index > half_point:
                    print("ANTI-STUCK EN CORO → Avanzando tras pausa moderada")
                    self.coro_fase = 0
                    self.coro_crossed = False
                    return "CHANGE_SLIDE"
        # =====================================================================

        # === AVANCE NATURAL POR PROGRESO DE LETRA (fuera de coros) ===
        if not self.is_current_slide_duplicated():
            total = len(current_slide_words)
            if total > 0:
                progreso = self.current_word_index / total
                umbral = 0.75 if total <= 10 else 0.85
                if progreso >= umbral:
                    print(
                        f"🎶 Fin de slide detectado por progreso "
                        f"({progreso:.0%}, umbral {umbral:.0%}) → Avanzando"
                    )
                    return "CHANGE_SLIDE"

        return "PROGRESS" if self.current_word_index > old_index else "CONTINUE"

    def _calculate_optimal_lookahead(self, is_duplicated, half_point):
        """Lookahead óptimo"""
        if not is_duplicated:
            return 8
            
        if self.current_word_index < half_point:
            remaining_in_first_half = half_point - self.current_word_index - 1
            return min(3, remaining_in_first_half)
        else:
            return 6

    def _should_change_slide_advanced(self, **kwargs):
    # Ya no se usa → todo el control está ahora en process_recognized_text con el 78%
        return False


    def _is_problematic_song(self):
        """Detecta SOLO la canción que siempre falla: Ya No Soy Esclavo Del Temor"""
        # Detectar por contenido del slide actual (más confiable)
        current_words = " ".join(self.get_current_slide_text()).lower()
        return any(indicator in current_words for indicator in [
            "ya no soy esclavo", "esclavo del temor", "envuelves", "melodía", "vientre", "rescataste"
        ])
                
    def _detect_problematic_song(self, current_slide_words):
        problematic_keywords = [
            'envuelves', 'melodía', 'esclavo', 'temor', 'vientre',
            'rescataste', 'rodeado', 'abriste', 'liberados', 'melodia', 'cancion'
        ]
        matches = sum(1 for word in current_slide_words if any(k in word.lower() for k in problematic_keywords))
        return matches >= 2
        
    def _simple_look_ahead(self, word, word_list, max_jump=5):
        """Look-ahead pequeño y seguro solo en la segunda mitad del slide"""
        start = self.current_word_index + 1
        end = min(start + max_jump, len(word_list))
        for i in range(start, end):
            expected = word_list[i]
            if (word == expected or 
                word == expected.replace('í','i').replace('ó','o').replace('á','a').replace('é','e').replace('ú','u')):
                jump = i - self.current_word_index
                self.current_word_index = i + 1
                print(f"Look-ahead +{jump}: '{word}' → posición {i+1}")
                return True
        return False
   

    def _calculate_similarity(self, list1, list2):
        """Calcula similitud entre dos listas de palabras"""
        if len(list1) != len(list2):
            return 0
            
        matches = sum(1 for a, b in zip(list1, list2) if a == b)
        return matches / len(list1)

    def _get_current_recognized_words(self):
        """Método auxiliar para obtener palabras reconocidas actuales"""
        # Por ahora retornar lista vacía - es solo para logging
        return []

    def reset_tracking(self, slide_number=2):
        """Reinicia el seguimiento"""
        self.current_slide = slide_number
        self.current_word_index = 0
        print(f"🔄 Seguimiento reiniciado al Slide {slide_number}")

    def _detectar_aplausos_o_gritos(self, text):
            """Detecta gritos de alabanza típicos"""
            triggers = [
                "gloria", "aleluya", "jesús", "amen", "santo", "poderoso",
                "victoria", "libertad", "fuego", "¡gloria!", "¡aleluya!"
            ]
            text_lower = text.lower()
            count = sum(1 for t in triggers if t in text_lower)
            if count >= 2:
                self.aplausos_detectados += count
                if self.aplausos_detectados >= 3:
                    print("¡APLAUSOS/GRITOS DETECTADOS! → Forzando cambio")
                    return True
            return False

    def _ignicion_rapida(self):
        """
        Ignición inteligente y escalable:
        - Solo activa en los primeros 4 slides
        - El tiempo de tolerancia crece según el slide actual (más paciencia al avanzar)
        - Solo dispara si NO ha habido progreso real en mucho tiempo
        """
        if self.current_slide > 4:
            return None  # Ya estamos en el cuerpo de la canción → no forzar nunca

        if self.current_word_index > 5:
            return None  # Ya avanzó un poco → todo bien

        tiempo_desde_ultimo_progreso = time.time() - self.last_progress_time

        # Tolerancia dinámica: cuanto más avanzado el slide, más paciencia
        tolerancia = {
            2: 35,   # Slide intro: máximo 35 segundos sin cantar
            3: 50,   # Puente lento: hasta 50 segundos
            4: 65,   # Primer coro: hasta 65 segundos (mucha gente ora aquí)
        }.get(self.current_slide, 60)

        if tiempo_desde_ultimo_progreso > tolerancia:
            print(f"IGNICIÓN INTELIGENTE: {tiempo_desde_ultimo_progreso:.1f}s sin progreso → Cambio forzado (slide {self.current_slide} → {self.current_slide + 1})")
            return "CHANGE_SLIDE"

        return None


    def forzar_siguiente_slide(self):
        """FUNCIÓN PÚBLICA para tecla de emergencia (F8, pedal, etc.)"""
        print("🚨 BOTÓN DE EMERGENCIA PRESIONADO → Cambio inmediato")
        self.ultimo_cambio_slide = time.time()
        self.aplausos_detectados = 0
        self.coro_repetido_detectado = False
        return "CHANGE_SLIDE"

    def resetear_a_inicio(self):
        """Detecta frases como "Vamos a cantar", "Esta canción dice", etc."""
        print("RESETEO AUTOMÁTICO → Volviendo al slide 2")
        self.current_slide = 2
        self.current_word_index = 0
        self.start_time = time.time()
        self.aplausos_detectados = 0
        self.coro_repetido_detectado = False
        self._preload_slides_ahead(3)



def load_lyrics_data(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Datos cargados desde: {json_file}")
        return data
    except Exception as e:
        print(f"❌ Error cargando {json_file}: {e}")
        return {}


