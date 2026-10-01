import os
import json
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS, GPSTAGS

MAX_SIZE = 1600

def get_decimal_from_dms(dms, ref):
    if dms is None or ref is None: return None
    try:
        # Обработка разных форматов Pillow (кортежи или числа)
        parts = []
        for x in dms:
            if isinstance(x, (tuple, list)):
                parts.append(float(x[0]) / float(x[1]))
            else:
                parts.append(float(x))
        
        val = parts[0] + parts[1]/60.0 + parts[2]/3600.0
        return -val if ref in ['S', 'W'] else val
    except: return None

def get_gps_from_file(image_path):
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if not exif: return None
            gps = {}
            for tag, val in exif.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    for t in val: gps[GPSTAGS.get(t, t)] = val[t]
            
            if "GPSLatitude" in gps:
                return {
                    "lat": get_decimal_from_dms(gps["GPSLatitude"], gps.get("GPSLatitudeRef")),
                    "lng": get_decimal_from_dms(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E"))
                }
    except: return None
    return None

def resize_image(image_path):
    try:
        with Image.open(image_path) as img:
            # Исправляем поворот фото
            img = ImageOps.exif_transpose(img)
            # Сжимаем, если фото больше лимита
            if img.width > MAX_SIZE or img.height > MAX_SIZE:
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
            
            # Сохраняем всегда (для оптимизации веса), качество 85
            img.save(image_path, "JPEG", quality=85, optimize=True)
            return True
    except: return False

# --- ГЛАВНАЯ ЛОГИКА ---

# 1. Читаем существующий photos.json (защита правок)
existing_photos = {}
if os.path.exists('photos.json'):
    try:
        with open('photos.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                existing_photos[item['url']] = {"lat": item['lat'], "lng": item['lng']}
    except Exception as e:
        print(f"Ошибка чтения photos.json: {e}")

new_photos_list = []
files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg'))]

for file in files:
    # ШАГ 1: Сначала получаем координаты (из JSON или из EXIF оригинала)
    coords = None
    
    if file in existing_photos:
        coords = existing_photos[file]
        print(f"[JSON] {file} - координаты взяты из ваших правок")
    else:
        coords = get_gps_from_file(file)
        if coords:
            print(f"[NEW] {file} - GPS извлечен из файла")
        else:
            print(f"[SKIP] {file} - в файле нет GPS")

    # ШАГ 2: Теперь сжимаем фото (после того как GPS считан!)
    if resize_image(file):
        print(f"      {file} оптимизирован/сжат")

    # ШАГ 3: Если координаты были найдены хоть где-то — добавляем в список
    if coords:
        new_photos_list.append({"url": file, "lat": coords["lat"], "lng": coords["lng"]})

# 4. Сохраняем результат
new_photos_list.sort(key=lambda x: x['url'])
with open('photos.json', 'w', encoding='utf-8') as f:
    json.dump(new_photos_list, f, indent=4, ensure_ascii=False)

print(f"\nГотово! Обработано: {len(files)}. В карте: {len(new_photos_list)}.")
