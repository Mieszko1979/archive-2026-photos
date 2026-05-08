import os
import json
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS, GPSTAGS

MAX_SIZE = 1600

def get_decimal_from_dms(dms, ref):
    if dms is None or ref is None: return None
    try:
        parts = [float(x[0])/float(x[1]) if isinstance(x, tuple) else float(x) for x in dms]
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
            # Исправляем ориентацию (чтобы фото не ложились на бок)
            img = ImageOps.exif_transpose(img)
            if img.width > MAX_SIZE or img.height > MAX_SIZE:
                print(f"Сжимаем {image_path}...")
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
                img.save(image_path, "JPEG", quality=85, optimize=True)
                return True
            else:
                # Даже если размер ок, пересохраняем для оптимизации веса
                img.save(image_path, "JPEG", quality=85, optimize=True)
                return True
    except Exception as e:
        print(f"Ошибка при сжатии {image_path}: {e}")
        return False

# --- ГЛАВНАЯ ЛОГИКА ---

# 1. Читаем существующий photos.json
existing_photos = {}
if os.path.exists('photos.json'):
    try:
        with open('photos.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                existing_photos[item['url']] = {"lat": item['lat'], "lng": item['lng']}
    except Exception as e:
        print(f"Предупреждение: не удалось прочитать photos.json: {e}")

new_photos_list = []
# 2. Получаем список всех JPG файлов в папке
files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg'))]

for file in files:
    # --- ШАГ 1: СЖИМАЕМ ФОТО В ЛЮБОМ СЛУЧАЕ ---
    resize_image(file)

    # --- ШАГ 2: РАБОТАЕМ С КООРДИНАТАМИ ---
    if file in existing_photos:
        # Если фото уже было в базе, берем старые координаты (защита ручных правок)
        coords = existing_photos[file]
        print(f"Используем сохраненные координаты для: {file}")
    else:
        # Если фото новое, пытаемся вытащить GPS из EXIF
        coords = get_gps_from_file(file)
        if coords:
            print(f"Извлечен GPS для нового фото: {file}")
        else:
            print(f"!!! ВНИМАНИЕ: В фото {file} нет GPS. В photos.json оно не попадет, пока не пропишете координаты вручную.")

    # 3. Если координаты есть (новые или старые), добавляем в итоговый список
    if coords:
        new_photos_list.append({"url": file, "lat": coords["lat"], "lng": coords["lng"]})

# 4. Сохраняем итоговый список
new_photos_list.sort(key=lambda x: x['url'])
with open('photos.json', 'w', encoding='utf-8') as f:
    json.dump(new_photos_list, f, indent=4, ensure_ascii=False)

print(f"\nГотово! Обработано файлов: {len(files)}. В карте (photos.json) прописано: {len(new_photos_list)}.")
