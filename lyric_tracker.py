import json
import time
import re
from difflib import SequenceMatcher

class LyricTracker:
    def __init__(self, lyrics_data):
        self.lyrics_data = lyrics_data
        self.current_slide = 2
        self.current_word_index = 0
        self.is_tracking = False
        
        # CARGAR CONFIGURACIÓN
        self.config = self._load_config()
        
        # Cache de palabras y DETECCIÓN DE ESTRUCTURA
        self.slide_words_cache = {}
        self.common_patterns = self._build_common_patterns()
        self.slide_structures = self._analyze_slide_structures()
        self._build_words_cache()

        print("🎵 Motor con detección de estructura duplicada")
    def _build_common_patterns(self):
        """Patrones comunes de reconocimiento erróneo"""
        return {
            r'enero': 'quiero',
            r'hielo': 'lo', 
            r've\s*to\s*da': 'toda',
            r'sus': 'jesús',
            r'misma': 'mis',
            r'nos': 'manos',
            r'hará': 'harás',
            r'precio': 'precioso',
            r'glory': 'gloria'
        }

    def _analyze_slide_structures(self):
        """Analiza la estructura de cada slide para detectar duplicaciones"""
        structures = {}
        
        for slide_key, data in self.lyrics_data.items():
            words = data.get("processed_text", [])
            total_words = len(words)
            
            # Buscar patrones de repetición dentro del slide
            if total_words > 10:
                # Dividir en mitades para comparar
                mid_point = total_words // 2
                first_half = words[:mid_point]
                second_half = words[mid_point:]
                
                # Calcular similitud entre mitades
                similarity = self._calculate_similarity(first_half, second_half)
                
                if similarity > 0.7:  # Si son más del 70% similares
                    structures[slide_key] = {
                        'type': 'duplicated',
                        'half_point': mid_point,
                        'similarity': similarity,
                        'total_words': total_words
                    }
                    print(f"🔄 Slide duplicado detectado: {slide_key} ({similarity:.0%} similitud)")
                    
        return structures

    def _calculate_similarity(self, list1, list2):
        """Calcula similitud entre dos listas de palabras"""
        if len(list1) != len(list2):
            return 0
            
        matches = sum(1 for a, b in zip(list1, list2) if a == b)
        return matches / len(list1)




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
                    "remaining_words_long": 3
                }
            }

    def _build_words_cache(self):
        """Pre-cache de palabras"""
        for slide_key in self.lyrics_data:
            self.slide_words_cache[slide_key] = self.lyrics_data[slide_key]["processed_text"]
        print(f"📦 Cache construido: {len(self.slide_words_cache)} slides")

    def get_current_slide_text(self):
        slide_key = f"slide_{self.current_slide}"
        return self.slide_words_cache.get(slide_key, [])

    def _preprocess_recognized_text(self, text):
        """CORRECCIÓN DE PALABRAS COMUNMENTE MAL RECONOCIDAS"""
        if isinstance(text, list):
            text = ' '.join(text)
            
        text_lower = text.lower()
        
        # Aplicar correcciones de patrones
        for pattern, correction in self.common_patterns.items():
            text_lower = re.sub(pattern, correction, text_lower)
            
        return text_lower.split()

    def process_recognized_text(self, recognized_text):
        words = self._preprocess_recognized_text(recognized_text)
        
        current_slide_words = self.get_current_slide_text()
        if not current_slide_words or self.current_word_index >= len(current_slide_words):
            return "CONTINUE"

        # DETECTAR TIPO DE SLIDE
        slide_key = f"slide_{self.current_slide}"
        slide_structure = self.slide_structures.get(slide_key, {})
        is_duplicated_slide = slide_structure.get('type') == 'duplicated'
        half_point = slide_structure.get('half_point', 0)
        
        # NUEVO: Detectar si estamos atascados
        current_stuck_position = self.current_word_index
        
        if len(words) > 0:
            expected_preview = current_slide_words[self.current_word_index:min(self.current_word_index+3, len(current_slide_words))]
            current_progress = f"{self.current_word_index}/{len(current_slide_words)}"
            
            structure_flag = ""
            if is_duplicated_slide:
                if self.current_word_index < half_point:
                    structure_flag = " 🔄(1ª mitad)"
                else:
                    structure_flag = " 🔄(2ª mitad)"
                    
            print(f"🔍 '{' '.join(words[:3])}...' → [{current_progress}]{structure_flag} {expected_preview}...")

        words_processed = 0
        used_words = set()

        for word in words:
            if self.current_word_index >= len(current_slide_words):
                break

            if word in used_words:
                continue
            used_words.add(word)

            expected_word = current_slide_words[self.current_word_index]

            # ESTRATEGIA 1: Coincidencia exacta
            if word == expected_word:
                print(f"✅ '{word}' → pos {self.current_word_index}")
                self.current_word_index += 1
                words_processed += 1
                continue

            # ESTRATEGIA 2: Coincidencia por similitud (MEJORADA)
            elif self._words_similar_optimized(word, expected_word):
                print(f"⚠️ '{word}' ≈ '{expected_word}' → pos {self.current_word_index}")
                self.current_word_index += 1
                words_processed += 1
                continue

            # ESTRATEGIA 3: Búsqueda adelantada CONTROLADA
            if is_duplicated_slide:
                if self.current_word_index < half_point:
                    max_lookahead = half_point - self.current_word_index - 1
                    look_ahead = min(4, max_lookahead)
                else:
                    look_ahead = 6
            else:
                look_ahead = 10
                
            if self._look_ahead_match_optimized(word, current_slide_words, look_ahead):
                words_processed += 1
                continue

        # NUEVO: LÓGICA MEJORADA DE BLOQUEO Y CAMBIO
        if words_processed == 0 and self.current_word_index == current_stuck_position:
            print(f"🔒 Posible bloqueo en posición {self.current_word_index}")
            
            # Forzar avance si estamos muy cerca del final de la mitad
            if is_duplicated_slide and self.current_word_index < half_point:
                first_half_progress = self.current_word_index / half_point
                if first_half_progress >= 0.95:  # 95% de la primera mitad
                    print(f"🎯 Forzando avance por bloqueo al 95% de primera mitad")
                    self.current_word_index = half_point  # Saltar a segunda mitad
                    # NUEVO: Cambiar slide inmediatamente si saltamos a la segunda mitad
                    return "CHANGE_SLIDE"

        # 🎯 LÓGICA DE CAMBIO MEJORADA - MÁS FLEXIBLE
        if words_processed > 0 or self.current_word_index > current_stuck_position:
            current_progress_ratio = self.current_word_index / len(current_slide_words)
            
            if is_duplicated_slide:
                if self.current_word_index < half_point:
                    first_half_progress = self.current_word_index / half_point
                    # MÁS FLEXIBLE: 85% + 2 palabras o 90% automático
                    should_change = (first_half_progress >= 0.85 and words_processed >= 2) or (first_half_progress >= 0.90)
                    change_type = f"PRIMERA MITAD: {first_half_progress:.0%}"
                    
                    print(f"📊 Progreso 1ª mitad: {self.current_word_index}/{half_point} = {first_half_progress:.0%}")
                    
                else:
                    second_half_length = len(current_slide_words) - half_point
                    second_half_progress = (self.current_word_index - half_point) / second_half_length
                    # MÁS FLEXIBLE: 70% + 1 palabra o 75% automático
                    should_change = (second_half_progress >= 0.70 and words_processed >= 1) or (second_half_progress >= 0.75)
                    change_type = f"SEGUNDA MITAD: {second_half_progress:.0%}"
                    
                    print(f"📊 Progreso 2ª mitad: {self.current_word_index - half_point}/{second_half_length} = {second_half_progress:.0%}")
                    
                if should_change:
                    print(f"🎯 Cambio {change_type} + {words_processed} palabras")
                    return "CHANGE_SLIDE"
                    
            else:
                # SLIDES NORMALES: COMPORTAMIENTO ORIGINAL
                change_threshold = self.config["tracking"].get("early_change_ratio", 0.70)
                if current_progress_ratio >= change_threshold and words_processed >= 2 and self.should_change_slide_optimized():
                    print(f"🎯 Cambio NORMAL: {current_progress_ratio:.0%} + {words_processed} palabras")
                    return "CHANGE_SLIDE"

        return "CONTINUE" if words_processed == 0 else "PROGRESS"
    def _check_second_half_completion(self):
        """Verifica si la segunda mitad está suficientemente avanzada - CORREGIDO"""
        slide_key = f"slide_{self.current_slide}"
        slide_structure = self.slide_structures.get(slide_key, {})
        half_point = slide_structure.get('half_point', 0)
        
        current_slide_words = self.get_current_slide_text()
        
        # Si ya estamos en la segunda mitad, verificar progreso
        if self.current_word_index >= half_point:
            second_half_length = len(current_slide_words) - half_point
            second_half_progress = (self.current_word_index - half_point) / second_half_length
            
            print(f"📊 Verificación 2ª mitad: {self.current_word_index - half_point}/{second_half_length} = {second_half_progress:.0%}")
            
            # Si el progreso es suficiente, cambiar slide
            if second_half_progress >= 0.70:
                return True
        
        return False

    def _words_similar_optimized(self, word1, word2):
            """Usar min_word_length de configuración - MEJORADO PARA ACENTOS"""
            min_length = self.config["tracking"].get("min_word_length", 2)
            
            if len(word1) < min_length or len(word2) < min_length:
                return False

            # NUEVO: Normalizar palabras (quitar acentos para comparación)
            def normalize_word(word):
                replacements = {
                    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
                    'ü': 'u', 'ñ': 'n'
                }
                normalized = ''.join(replacements.get(c, c) for c in word)
                return normalized

            word1_norm = normalize_word(word1)
            word2_norm = normalize_word(word2)

            # PRIMERO: Comparación con normalización
            if word1_norm == word2_norm:
                return True

            common_confusions = {
                'has': 'haz', 'haz': 'has',
                'mis': 'misma', 'misma': 'mis', 'mi': 'mis',
                'llene': 'llena', 'llena': 'llene',
                'nos': 'manos', 'manos': 'nos', 'no': 'manos',
                'es': 'jesús', 'jesús': 'es', 'sus': 'jesús',
                # NUEVAS: Confusiones con/sin acento
                'mi': 'mí', 'mí': 'mi',
                'tu': 'tú', 'tú': 'tu', 
                'el': 'él', 'él': 'el',
                'se': 'sé', 'sé': 'se',
                'te': 'té', 'té': 'te'
            }

            if word1 in common_confusions and common_confusions[word1] == word2:
                return True

            # Coincidencia con normalización
            if word1_norm[:2] == word2_norm[:2]:
                return True
            if word1_norm[-2:] == word2_norm[-2:]:
                return True

            if word1_norm in word2_norm or word2_norm in word1_norm:
                return True

            return False

    def _look_ahead_match_optimized(self, word, expected_words, look_ahead=10):
        """Búsqueda con límite configurable y protección contra saltos grandes"""
        start_index = self.current_word_index + 1
        end_index = min(start_index + look_ahead, len(expected_words))

        for i in range(start_index, end_index):
            expected = expected_words[i]
            
            # PROTECCIÓN: No permitir saltos muy grandes (más de 8 palabras)
            max_jump = 8
            if (i - self.current_word_index) > max_jump:
                continue
                
            if word == expected:
                jump = i - self.current_word_index
                print(f"🎯 '{word}' = '{expected}' → SALTO +{jump}")
                self.current_word_index = i + 1
                return True
            elif self._words_similar_optimized(word, expected):
                jump = i - self.current_word_index
                print(f"🎯 '{word}' ≈ '{expected}' → SALTO +{jump}")
                self.current_word_index = i + 1
                return True

        return False
    
    def should_change_slide_optimized(self):
        """UMBRALES PARA SLIDES NORMALES (no duplicados)"""
        current_slide_words = self.get_current_slide_text()
        if not current_slide_words:
            return False

        # Solo aplicar para slides no duplicados
        slide_key = f"slide_{self.current_slide}"
        if slide_key in self.slide_structures:
            return False  # Los slides duplicados usan su propia lógica

        words_remaining = len(current_slide_words) - self.current_word_index
        progress_ratio = self.current_word_index / len(current_slide_words)

        # CONFIGURACIÓN ORIGINAL PARA SLIDES NORMALES
        long_threshold = self.config["slide_change"].get("long_slide_threshold", 12)
        progress_short = self.config["slide_change"].get("progress_threshold_short", 0.70)
        progress_long = self.config["slide_change"].get("progress_threshold_long", 0.65)
        remaining_short = self.config["slide_change"].get("remaining_words_short", 1)
        remaining_long = self.config["slide_change"].get("remaining_words_long", 2)

        if len(current_slide_words) > long_threshold:
            should_change = progress_ratio >= progress_long or words_remaining <= remaining_long
        else:
            should_change = progress_ratio >= progress_short or words_remaining <= remaining_short

        if should_change:
            print(f"🎯 Umbral NORMAL: {progress_ratio:.0%} progreso, {words_remaining} palabras restantes")
        return should_change
     
    def _force_slide_change_check(self):
        """Usar threshold de configuración"""
        current_slide_words = self.get_current_slide_text()
        if not current_slide_words:
            return False

        force_threshold = self.config["tracking"].get("force_change_threshold", 4)
        words_remaining = len(current_slide_words) - self.current_word_index
        
        if words_remaining <= force_threshold:
            print(f"🎯 Forzando cambio por {words_remaining} palabras restantes")
            return True

        return False
    def next_slide(self):
        """Avanza al siguiente slide OPTIMIZADO"""
        self.current_slide += 1
        self.current_word_index = 0

        slide_key = f"slide_{self.current_slide}"
        if slide_key in self.slide_words_cache:
            print(f"🔄 Cambiando a Slide {self.current_slide} (OPTIMIZADO)")
            # OPTIMIZACIÓN: Preview más corto
            next_words = self.get_current_slide_text()
            preview = ' '.join(next_words[:3]) + '...'  # ← REDUCIDO de 5 a 3
            print(f"📝 Siguiente: {preview}")
            return True
        else:
            print("🎉 ¡Presentación completada!")
            return False
    def reset_tracking(self, slide_number=2):
        """Reinicia el seguimiento OPTIMIZADO"""
        self.current_slide = slide_number
        self.current_word_index = 0
        print(f"🔄 Seguimiento reiniciado al Slide {slide_number} (OPTIMIZADO)")

    # Los métodos next_slide, reset_tracking se mantienen igual

def load_lyrics_data(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Datos cargados desde: {json_file}")
        return data
    except Exception as e:
        print(f"❌ Error cargando {json_file}: {e}")
        return {}

# ... (el resto del código de prueba se mantiene igual)

# El resto del código de prueba se mantiene igual...
def simulate_audio_input():
    """
    Simula entrada de audio para pruebas
    Ahora incluye las palabras FINALES del slide
    """
    # Simulación COMPLETA del slide 2
    test_phrases = [
        ["quiero", "levantar"],
        ["quiero", "levantar", "a", "ti"],
        ["quiero", "levantar", "a", "ti", "mis", "manos"],
        ["quiero", "levantar", "a", "ti", "mis", "manos", "y", "alabarte"],
        ["al", "maravilloso", "jesús"],  # ¡Palabras finales!
        ["milagroso", "señor"]  # ¡Últimas palabras!
    ]
    return test_phrases

def main():
    # Cargar datos de letras
    lyrics_data = load_lyrics_data("lyrics_data.json")
    if not lyrics_data:
        return

    # Inicializar tracker
    tracker = LyricTracker(lyrics_data)

    # Mostrar información inicial
    print("\n" + "="*50)
    print("INICIANDO PRUEBA DE SEGUIMIENTO")
    print("="*50)

    # Simular reconocimiento de audio
    test_phrases = simulate_audio_input()

    for i, phrase in enumerate(test_phrases):
        print(f"\n--- Frase {i+1} ---")
        result = tracker.process_recognized_text(phrase)

        if result == "CHANGE_SLIDE":
            print("🚨 ¡SEÑAL PARA CAMBIAR SLIDE!")
            if tracker.next_slide():
                print("✅ Slide cambiado exitosamente")
            else:
                print("❌ No hay más slides")
                break

    print("\n" + "="*50)
    print("PRUEBA COMPLETADA")
    print("="*50)

if __name__ == "__main__":
    main()