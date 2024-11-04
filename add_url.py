products = [
    "/falcon-hasir-buyuk-boy-yavrulu-kadin-omuz-cantasi-bp-4811o-bej-o-4101969",
    "/kalin-topuklu-fermuarli-suet-strec-diz-ustu-okceli-uzun-kadin-cizme-003-9300-23-siyah-o-4479753",
    "/fermuarli-suet-strec-diz-ustu-okceli-uzun-cizme-003-9300-23-siyah-o-3385863"
]

import os
import sqlite3

conn = sqlite3.connect(os.path.join(".", "assets", "products.db"))
c = conn.cursor()

# for url in products:
#     cur = conn.cursor()
#     cur.execute("INSERT INTO product_url (url, category_id) VALUES (?, ?)", (url, 48))
#     conn.commit()


ids_to_delete = [2158]

# Prepare the DELETE statement with the IN clause
query = "DELETE FROM products WHERE id IN ({})".format(",".join("?" for _ in ids_to_delete))

# Execute the DELETE statement
c.execute(query, ids_to_delete)
conn.commit()
conn.close()               