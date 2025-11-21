import pyaudio
import numpy as np

class AudioEnhancer:
    def __init__(self):
        self.sample_rate = 16000
        
    def apply_voice_filters(self, audio_data):
        """
        Aplica filtros para mejorar reconocimiento de canto
        """
        # Convertir a numpy array
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        
        # Normalizar volumen (útil para canto con variaciones)
        audio_np = self._normalize_audio(audio_np)
        
        # Suavizar variaciones bruscas (transiciones de tono)
        audio_np = self._smooth_transitions(audio_np)
        
        return audio_np.tobytes()
    
    def _normalize_audio(self, audio_data):
        """Normaliza el volumen del audio"""
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            return (audio_data / max_val * 32767).astype(np.int16)
        return audio_data
    
    def _smooth_transitions(self, audio_data, window_size=5):
        """Suaviza transiciones bruscas en el audio"""
        window = np.ones(window_size) / window_size
        return np.convolve(audio_data, window, mode='same').astype(np.int16)