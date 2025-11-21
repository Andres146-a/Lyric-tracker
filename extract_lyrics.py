from pptx import Presentation
import json
import os

def extract_text_from_pptx(pptx_path):
    """Extrae texto de cada slide del PowerPoint"""
    try:
        prs = Presentation(pptx_path)
        slides_data = {}
        
        for i, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            
            if slide_text:
                slides_data[f"slide_{i+1}"] = {
                    "raw_text": slide_text,
                    "processed_text": process_slide_text(slide_text)
                }
        
        return slides_data
    except Exception as e:
        print(f"Error al procesar el PowerPoint: {e}")
        return {}

def process_slide_text(slide_text):
    """Procesa el texto del slide - VERSIÓN CORREGIDA"""
    full_text = " ".join(slide_text)
    
    print(f"🔍 Procesando: '{full_text}'")
    
    # MANEJAR REPETICIONES CON //texto//
    if full_text.startswith("//") and full_text.endswith("//"):
        print("🔄 Detectado //texto// (repetir completo)")
        # Remover los // del inicio y final
        text_content = full_text[2:-2].strip()  # Quita "//" del inicio y final
        # Duplicar el contenido completo
        full_text = text_content + " " + text_content
        print(f"🎵 Texto duplicado: {full_text}")
    
    # MANEJAR // en medio del texto  
    elif "//" in full_text:
        print("🔄 Detectado // en medio del texto")
        # Buscar el primer //
        first_split = full_text.find("//")
        # Buscar el último //
        last_split = full_text.rfind("//")
        
        if first_split != last_split:  # Hay dos // diferentes
            before_first = full_text[:first_split].strip()
            between = full_text[first_split+2:last_split].strip()  # Entre los //
            after_last = full_text[last_split+2:].strip()
            
            full_text = before_first + " " + between + " " + between + " " + after_last
            print(f"🎵 Sección repetida: {full_text}")
        else:
            # Solo un //, duplicar lo anterior
            parts = full_text.split("//", 1)
            if len(parts) == 2:
                section_to_repeat = parts[0].strip()
                remaining = parts[1].strip()
                full_text = section_to_repeat + " " + section_to_repeat + " " + remaining
                print(f"🎵 Mitad repetida: {full_text}")
    
    words = clean_and_tokenize(full_text)
    print(f"📝 {len(words)} palabras finales: {words}")
    return words

def clean_and_tokenize(text):
    """Limpia el texto y lo divide en palabras"""
    # Convertir a minúsculas y remover caracteres especiales
    import re
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    
    # Dividir en palabras y filtrar vacías
    words = text.split()
    # (Opcional) filtrar palabras muy comunes)
    
    return words

def save_to_json(data, output_path):
    """Guarda los datos en formato JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    # Configuración
    pptx_file = "test_files/Creo_en _ti_Letra.pptx"  # Cambia por tu archivo
    output_file = "lyrics_data.json"
    
    if not os.path.exists(pptx_file):
        print(f"❌ No se encuentra el archivo: {pptx_file}")
        print("Por favor, coloca tu PowerPoint en la carpeta test_files/")
        return
    
    print("📊 Extrayendo texto del PowerPoint...")
    slides_data = extract_text_from_pptx(pptx_file)
    
    if slides_data:
        save_to_json(slides_data, output_file)
        print(f"✅ Extracción completada! Guardado en: {output_file}")
        print(f"📝 Slides procesados: {len(slides_data)}")
        
        # Mostrar preview
        for slide_id, data in list(slides_data.items())[:3]:
            print(f"\n{slide_id}:")
            print(f"  Texto: {' '.join(data['processed_text'][:5])}...")
    else:
        print("❌ No se pudo extraer texto del PowerPoint")

if __name__ == "__main__":
    main()