
# 🎤 LyricTracker

### Sistema Automático de Sincronización de Letras con PowerPoint

Sistema inteligente que sincroniza automáticamente letras de canciones con presentaciones de **PowerPoint en tiempo real**, usando reconocimiento de voz offline.

Ideal para:

* Iglesias / servicios religiosos
* Conciertos y eventos musicales
* Proyección de letras en vivo

---

# ✨ Descripción

**LyricTracker** es una solución diseñada para eliminar la necesidad de cambiar manualmente las diapositivas durante canciones en vivo.

El sistema escucha el audio del micrófono, detecta las palabras cantadas y **avanza automáticamente las diapositivas de PowerPoint** en el momento correcto.

Incluye control manual, comandos de voz, detección de coros repetidos y optimización de audio para entornos reales con ruido y reverberación.

Este proyecto combina ingeniería de software + ingeniería de sonido para lograr sincronización confiable en tiempo real.

---

# 🎯 Objetivos del Proyecto

## 🔁 Sincronización automática

* Rastrea palabras cantadas en tiempo real
* Cambia slides al alcanzar umbral de progreso (≈65–80%)
* Evita cambios prematuros o tardíos

## 🎶 Detección de estructuras musicales

Soporta letras complejas:

* Coros repetidos
* Versos largos o duplicados
* Cambios dinámicos de estructura

Usa métricas fonéticas y matemáticas como:

* Distancia Levenshtein
* Soundex adaptado al español

## 🎛️ Control manual y de emergencia

Permite intervención humana cuando es necesario:

| Acción            | Control                       |
| ----------------- | ----------------------------- |
| Siguiente slide   | F8                            |
| Reiniciar canción | F9                            |
| Comandos de voz   | "atrás", "repetir", "slide 3" |

Perfecto para aplausos, pausas o repeticiones espontáneas.

## ⚡ Optimización de audio en tiempo real

* Procesamiento en chunks de baja latencia
* Métricas de rendimiento para depuración
* Diseñado para entornos ruidosos

## 📊 Interfaz y monitoreo

* Overlay flotante con progreso en vivo
* Logs detallados del rendimiento

---

# 🧠 Tecnologías Utilizadas

| Área                  | Tecnología           |
| --------------------- | -------------------- |
| Lenguaje principal    | Python 3.12+         |
| Reconocimiento de voz | **Vosk (offline)**   |
| Captura de audio      | PyAudio              |
| PowerPoint Automation | Win32com + PyAutoGUI |
| Similitud fonética    | Jellyfish            |
| Interfaz overlay      | Tkinter              |
| Hotkeys               | Keyboard             |
| Concurrencia          | Threading            |
| Gestión de datos      | JSON                 |

El sistema incluye normalización fonética específica del español para mejorar precisión en ambientes reales.

---

# 📦 Instalación

## 1️⃣ Clonar repositorio

```bash
git clone https://github.com/Andres146-a/Lyric-tracker.git
cd Lyric-tracker
```

## 2️⃣ Crear entorno virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4️⃣ Descargar modelo de voz (IMPORTANTE)

Descargar modelo español Vosk:
[https://alphacephei.com/vosk/models](https://alphacephei.com/vosk/models)

Colocar en:

```
/models/vosk-model-es-0.42
```

---

# ▶️ Uso

Ejecutar:

```bash
python balanced_main.py --song tu_cancion_lyrics.json
```

Si no se especifica canción, el sistema permite seleccionarla interactivamente.

### Flujo normal

1. Abrir PowerPoint en modo presentación
2. Ejecutar LyricTracker
3. El sistema escucha el micrófono
4. Las diapositivas avanzan automáticamente

---

# 🎮 Controles

| Control        | Acción                 |
| -------------- | ---------------------- |
| F8             | Forzar siguiente slide |
| F9             | Reiniciar canción      |
| Ctrl + C       | Detener sistema        |
| Voz: "atrás"   | Retroceder             |
| Voz: "repetir" | Repetir slide          |

---

# ⚙️ Configuración

Editar `config.json`:

```json
{
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 512,
    "processing_interval": 0.05
  },
  "powerpoint": {
    "advance_key": "pagedown",
    "back_key": "pageup"
  },
  "tracking": {
    "change_threshold": 2,
    "look_ahead_distance": 8
  }
}
```

---

# 📌 Requisitos importantes

* Windows (PowerPoint COM)
* Micrófono funcional
* PowerPoint en modo presentación
* Modelo Vosk descargado

---

# 🚀 Estado del proyecto

Proyecto funcional y optimizado para uso real en presentaciones en vivo.



## Ejecutar

python balanced_main.py
