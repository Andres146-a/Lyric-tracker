# check_repetitions.py
import json

def check_repetitions():
    """Verifica si las repeticiones // se están procesando"""
    with open('lyrics_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("🔍 VERIFICANDO REPETICIONES //")
    print("=" * 50)
    
    for slide_id, slide_data in data.items():
        raw_text = " ".join(slide_data["raw_text"])
        processed_text = slide_data["processed_text"]
        
        print(f"\n{slide_id}:")
        print(f"  RAW: '{raw_text}'")
        print(f"  PROCESADO: {' '.join(processed_text)}")
        print(f"  ¿Tiene '//'? {'✅ SÍ' if '//' in raw_text else '❌ NO'}")
        
        # Contar palabras para ver si se duplicó
        if '//' in raw_text:
            expected_duplication = len(processed_text) > len(raw_text.split()) * 0.8
            print(f"  ¿Se duplicó? {'✅ SÍ' if expected_duplication else '❌ POSIBLE PROBLEMA'}")

if __name__ == "__main__":
    check_repetitions()