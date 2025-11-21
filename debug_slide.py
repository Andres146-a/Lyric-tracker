# debug_slide4.py
import json

def debug_slide_structure():
    with open('lyrics_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("🔍 ESTRUCTURA DEL SLIDE 4:")
    slide4 = data.get('slide_4', {})
    processed = slide4.get('processed_text', [])
    raw = slide4.get('raw_text', [])
    
    print(f"📝 Texto crudo: {raw}")
    print(f"🔧 Texto procesado ({len(processed)} palabras):")
    print(' '.join(processed))
    
    # Mostrar con índices
    print("\n📋 Palabras con índices:")
    for i, word in enumerate(processed):
        print(f"  [{i:2d}] {word}")

if __name__ == "__main__":
    debug_slide_structure()