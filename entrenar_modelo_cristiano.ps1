# entrenar_modelo_cristiano.ps1
# Ejecuta este archivo desde la raíz del proyecto

Write-Host "INICIANDO ENTRENAMIENTO DEL MODELO CRISTIANO..." -ForegroundColor Green

# 1. Crear carpeta temporal
if (Test-Path "modelo_cristiano_temp") { Remove-Item "modelo_cristiano_temp" -Recurse -Force }
mkdir modelo_cristiano_temp
cd modelo_cristiano_temp

# 2. Copiar modelo base pequeño
Copy-Item -Recurse "../models/vosk-model-small-es-0.42" "./vosk-model-small-es-0.42"

# 3. Entrenar el LM personalizado (2-3 horas)
Write-Host "Entrenando... esto tomará 2-3 horas (puedes dejarlo corriendo)" -ForegroundColor Yellow
python -c "
from vosk import LmTrain
LmTrain(
    corpus='../corpus_cristiano.txt',
    dict='../extra_words.txt',
    old_lm_dir='./vosk-model-small-es-0.42/graph',
    new_lm_dir='nuevo_lm',
    order=4
)
print('ENTRENAMIENTO TERMINADO!')
"

# 4. Reemplazar archivos en el modelo
Copy-Item "nuevo_lm/lm.arpa" "vosk-model-small-es-0.42/graph/lm.arpa" -Force
Copy-Item "nuevo_lm/words.txt" "vosk-model-small-es-0.42/graph/words.txt" -Force

# 5. Renombrar como modelo final
Rename-Item "vosk-model-small-es-0.42" "modelo_cristiano_final"

# 6. Mover al directorio models
Move-Item "modelo_cristiano_final" "../models/modelo_cristiano_final" -Force

# 7. Limpiar
cd ..
Remove-Item "modelo_cristiano_temp" -Recurse -Force

Write-Host "¡MODELO CRISTIANO FINAL CREADO Y GUARDADO EN models/modelo_cristiano_final!" -ForegroundColor Cyan
Write-Host "Ahora cambia en balanced_main.py la línea:" -ForegroundColor White
Write-Host 'model_path = "models/modelo_cristiano_final"' -ForegroundColor Green