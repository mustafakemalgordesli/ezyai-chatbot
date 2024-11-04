import hashlib


# Verilen metni Türkçe büyük harflerden küçük kharflere çevirir
def turkish_to_lower(text):
    translation_table = str.maketrans("IİÇĞÖŞÜ", "iıçğöşü")
    lowered_text = text.casefold()
    return lowered_text.translate(translation_table)

# Verilen değerlendirme puanını kullanarak yıldız şeklinde bir gösterim oluşturur.
def display_stars(rating):
    if rating == 0:
        return f"""
                <span style="font-size: 16px; color: gold;">
                    Değerlendirme bulunamadı.
                </span>
                """
    # HTML ve CSS ile yıldız göstergesi oluştur
    stars_html = f"""
    <span style="font-size: 24px; color: gold;">
        {'★' * int(rating)}{'☆' * (5 - int(rating))}
    </span>
    <span style="font-size: 20px; color: #808080;">
        ({rating}/5)
    </span>
    """
    return stars_html   

# Verilen şifreyi gizleyerek yıldız karakterleri ile değiştirir.
def mask_password(password):
    return "*" * len(password)



# Dosyanın hash değerini hesaplar.
def calculate_file_hash(file):
    file.seek(0)  # Dosya imlecini başa al
    file_bytes = file.read()  # Dosyanın baytlarını oku
    return hashlib.md5(file_bytes).hexdigest()