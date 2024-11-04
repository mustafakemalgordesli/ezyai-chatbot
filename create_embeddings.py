from langchain_core.documents import Document
from dotenv import load_dotenv
from langchain_chroma import Chroma
import boto3
from langchain_aws import BedrockEmbeddings
import os
import sqlite3

load_dotenv(override=True)

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
embeddings = BedrockEmbeddings(model_id="cohere.embed-multilingual-v3", client=bedrock_client)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory=os.path.join(".", "chroma_langchain_db"), 
)


conn = sqlite3.connect(os.path.join(".", "assets", "products.db"))
cur = conn.cursor()
cur.execute('select * from products')
rows = cur.fetchall()
conn.close()

ids = []
documents = []

def price_to_float(price):
    clean_price = price.replace('TL', '').strip() 
    clean_price = clean_price.replace('.', '')
    clean_price = clean_price.replace(',', '.')
    return float(clean_price)

for row in rows:
    print(row[0], row[1], row[6], row[10])
    ids.append(str(row[0]))
    content = "Ürün başlığı: " + row[1] + ",\t " + row[8]
    documents.append(Document(metadata={"id": str(row[0]), "vote": row[10], "price": price_to_float(row[3])},page_content=content.replace("\n", " "), id=row[0],))

vector_store.add_documents(documents=documents, ids=ids)
