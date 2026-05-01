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
            img = ImageOps.exif_transpose(img)
            if img.width > MAX_SIZE or img.height > MAX_SIZE:
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
                img.save(image_path, "JPEG", quality=85, optimize=True)
                return True
    except: return False
    return False

# --- ГЛАВНАЯ ЛОГИКА ЗАЩИТЫ ВАШИХ ПРАВОК ---

# 1. Читаем существующий photos.json
existing_photos = {}
if os.path.exists('photos.json'):
    try:
        with open('photos.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                # Запоминаем координаты, которые вы ввели вручную
                existing_photos[item['url']] = {"lat": item['lat'], "lng": item['lng']}
    except Exception as e:
        print(f"Предупреждение: не удалось прочитать photos.json: {e}")

new_photos_list = []
# 2. Получаем список всех JPG файлов в папке
files = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg'))]

for file in files:
    # 3. Если фото уже есть в JSON — БЕРЕМ ВАШИ КООРДИНАТЫ ИЗ ФАЙЛА
    if file in existing_photos:
        coords = existing_photos[file]
        print(f"Сохраняем ваши правки для: {file}")
    else:
        # 4. Если фото абсолютно новое — вытаскиваем GPS и сжимаем
        coords = get_gps_from_file(file)
        if coords:
            print(f"Новое фото найдено: {file}. Извлекаем GPS...")
            resize_image(file)
        else:
            print(f"В новом фото {file} нет GPS-данных!")

    if coords:
        new_photos_list.append({"url": file, "lat": coords["lat"], "lng": coords["lng"]})

# 5. Сохраняем итоговый список
new_photos_list.sort(key=lambda x: x['url'])
with open('photos.json', 'w', encoding='utf-8') as f:
    json.dump(new_photos_list, f, indent=4, ensure_ascii=False)

print(f"Готово! В списке: {len(new_photos_list)} фото. Ваши правки защищены.")
