import sqlite3
import os

conn = sqlite3.connect(os.path.join(".", "assets", "campaign.db")) 
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        gender TEXT,
        age INTEGER,
        preferences TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS campaigns (
        campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        discount_rate REAL,
        valid_until DATE
    )
''')


cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_campaigns (
        user_campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        campaign_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
    )
''')


cursor.executemany('''
    INSERT INTO users (name, email, gender, age, preferences)
    VALUES (?, ?, ?, ?, ?)
''', [
    ('Ali Yılmaz', 'ali@example.com', 'male', 30, 'shoes,jeans'),
    ('Ayşe Demir', 'ayse@example.com', 'female', 25, 'dresses,accessories'),
    ('Ahmet Kaya', 'ahmet@example.com', 'male', 40, 'jackets,shirts'),
])

cursor.executemany('''
    INSERT INTO campaigns (name, description, discount_rate, valid_until)
    VALUES (?, ?, ?, ?)
''', [
    ('Yaz İndirimi', 'Tüm yazlık ürünlerde %20 indirim', 0.20, '2024-09-30'),
    ('Ayakkabı İndirimi', 'Seçili ayakkabılarda %30 indirim', 0.30, '2024-10-15'),
    ('Kışlık Mont İndirimi', 'Kışlık montlarda %40 indirim', 0.40, '2024-12-31'),
])

cursor.executemany('''
    INSERT INTO user_campaigns (user_id, campaign_id)
    VALUES (?, ?)
''', [
    (1, 1),  # Ali Yılmaz için Yaz İndirimi
    (1, 2),  # Ali Yılmaz için Ayakkabı İndirimi
    (2, 1),  # Ayşe Demir için Yaz İndirimi
    (3, 3),  # Ahmet Kaya için Kışlık Mont İndirimi
])

conn.commit()
conn.close()