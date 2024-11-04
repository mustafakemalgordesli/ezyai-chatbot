import streamlit as st
from langchain_chroma import Chroma
import boto3
from langchain_aws import ChatBedrock, BedrockEmbeddings
import os
from dotenv import load_dotenv
import sqlite3
from utils import turkish_to_lower, display_stars, calculate_file_hash
from langchain.agents import create_tool_calling_agent
from langchain_core.tools import tool
from PIL import Image
from single_agent import GlobalState
from image_info import get_product_info
import random
from datetime import datetime
from streamlit_float import *
import streamlit as st
import tempfile
import pyaudio
import wave
from openai import OpenAI
from pathlib import Path
import numpy as np

product_info_state = GlobalState()

load_dotenv(override=True)
float_init()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name='us-east-1', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

embeddings = BedrockEmbeddings(model_id="cohere.embed-multilingual-v3", client=bedrock_client)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory=os.path.join(".", "chroma_langchain_db"), 
)


llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    client=bedrock_client
)

if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "products" not in st.session_state:
    st.session_state.products = []





def get_product_card(product):
    with st.container(border=True):
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(product[5], width=100)
        with col2:
            st.write(product[1])
            st.write(product[3])
            st.markdown(display_stars(product[10]), unsafe_allow_html=True)
            st.link_button("Ürüne git", "https://www.lcw.com" + product[6])
            
uploaded_file = st.file_uploader("Bir resim yükleyin", type=["jpg", "jpeg", "png", "webp"])

if "productinfo" not in st.session_state:
    st.session_state.productinfo = ""
    
if 'file_hash' not in st.session_state:
    st.session_state['file_hash'] = None

# Kullanıcın resim yüklemesini sağlar, resmi kaydeder ve ürün bilgilerini almak için işlemler yapar.
if uploaded_file is not None:
    try:
        # Yeni dosyanın hash değerini hesapla
        new_file_hash = calculate_file_hash(uploaded_file)
        
        if new_file_hash != st.session_state['file_hash']:
            img = Image.open(uploaded_file)
            st.session_state['file_hash'] = new_file_hash
            path = "saved_image.jpg"
            img.save(path)
            st.session_state.messages.append({"role": "resim", "content": path})
            res = get_product_info(path)
            st.success(res)
            st.session_state.productinfo = res
            st.image(img, caption='Yüklenen Resim', width=100)
            st.success("Resim başarıyla yüklendi!")
    except Exception as e:
        st.error("Lütfen geçerli bir resim dosyası yükleyin.")     

for message in st.session_state.messages:
    if message["role"] == "resim":
        res = get_product_info(message["content"])
        st.success(res)
        # st.session_state.productinfo = res
        st.image(message["content"], caption='Yüklenen Resim', width=100)
        st.success("Resim başarıyla yüklendi!")
    if message["role"] == "product":
        get_product_card(message["content"])
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


@tool
def search_tool(query: str) -> str:
    """This tool finds similar products using a product's description information"""
    query = query.lower()
    results = vector_store.similarity_search_with_score(query, k=1)
    message = ""
    for res, score in results:
        print(f"*[SIM={score:3f}] {res.page_content}  {res.metadata}")
        print(res.metadata.get("id"))
        conn = sqlite3.connect(os.path.join(".", "assets", "products.db"))
        cur = conn.cursor()
        res = cur.execute(f'select * from products where id = {int(res.metadata.get("id"))}')
        item = res.fetchone()
        st.session_state.products.append(item)   
        message += "Bulduğum ürün: " + item[1] + " \nÜrün fiyatı: " + item[3]
    return turkish_to_lower(message)

@tool
def weather_forecast():
    """This tool get up-to-date weather information"""
    current_date = datetime.now()
    month = current_date.month
    day = current_date.day

    season = ""
    condition = ""
    average_temperature = 0

    if month in [12, 1, 2]: 
        season = "Kış"
        condition = "Soğuk ve kar yağışlı"
        average_temperature = random.randint(-5, 5)  
    elif month in [3, 4, 5]:  
        season = "İlkbahar"
        condition = "Parçalı bulutlu ve serin"
        average_temperature = random.randint(10, 20)  
    elif month in [6, 7, 8]: 
        season = "Yaz"
        condition = "Sıcak ve güneşli"
        average_temperature = random.randint(25, 35)
    elif month in [9, 10, 11]:  
        season = "Sonbahar"
        condition = "Serin ve rüzgarlı"
        average_temperature = random.randint(15, 25) 
    
    result =  f"{day}.{month} - {season} mevsiminde Türkiye'de hava durumu: {condition}, Ortalama sıcaklık: {average_temperature}°C"
    return result

tools = [search_tool, weather_forecast]

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """
        You are a fashion combination recommender.
        You are a smart assistant who helps users complete their outfits. Help the user complete their outfit by following these steps.
        While doing this, get current weather information and make appropriate clothing suggestions.
        1. Create a list with detailed descriptions of suitable products (no more than 2-3 products).   
        2. Send these products in order to the products search tool to check if they are among our available products.
        3. Finally, create a message to the user according to the list of products you have obtained
        REMEMBER! The final answer should be in Turkish.
        You have access to the following tool: {tool_names}.
        """),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)


upper_container = st.container()


# Ses kaydetme fonksiyonu
def record_audio(filename, duration=5, rate=44100, channels=1,  silence_threshold=500, silence_duration=3):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=channels, rate=rate, input=True, frames_per_buffer=1024)
    
    silent_chunks = 0
    chunk_duration = 1024 / rate
    
    frames = []
    with upper_container:
        st.info("Kayıt başladı...")
    for _ in range(0, int(rate / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)
        
        audio_data = np.frombuffer(data, dtype=np.int16)
        rms = np.sqrt(np.mean(np.square(audio_data)))  # RMS hesaplaması

        if rms < silence_threshold:
            silent_chunks += 1
        else:
            silent_chunks = 0  
                
                
        if silent_chunks * chunk_duration >= silence_duration:
            # st.info("Sessizlik algılandı, kayıt sonlandırılıyor.")
            break
    
    with upper_container:
        st.success("Kayıt tamamlandı.")
    
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

# Whisper API ile sesi metne çevir
def transcribe_audio(file_path):
    with open(file_path, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file
    )
    return transcript.text

# OpenAI TTS-1 modeli ile metni sese çevir
def get_openai_response(prompt):
    speech_file_path = Path(__file__).parent / "speech.mp3"
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=prompt
    ) as response:
        response.stream_to_file(speech_file_path)
        
        
def create_response(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})        
    with upper_container:
        with st.chat_message("user"):
            st.write(prompt)

    if st.session_state.productinfo != "":
        prompt = prompt + " " + st.session_state.productinfo 
        st.session_state.productinfo = ""

    with upper_container:
        with st.chat_message("assistant"):   
            oneri = agent_executor.invoke({"input": prompt})
            openai_response = get_openai_response(oneri['output'][0]['text'])
            st.audio(os.path.join("pages", "speech.mp3"), format="audio/mpeg", loop=False)
            st.write(oneri['output'][0]['text'])
        st.session_state.messages.append({"role": "assistant", "content": oneri['output'][0]['text']})
    
    for product in st.session_state.products:
        with upper_container:
            get_product_card(product)
        st.session_state.messages.append({"role": "product", "content": product})
    st.session_state.products.clear()


footer_container = st.container()
with footer_container:
    col1, col2 = st.columns([9, 1])

    with col1:
        if prompt := st.chat_input("Size nasıl yardımcı olabilirim?"):
            create_response(prompt)
    with col2:
        if st.button(":material/mic:"):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
                audio_file_path = temp_audio_file.name
    
            # Mikrofonla ses kaydet
            record_audio(audio_file_path)
    
            # Whisper API ile metne çevir
            transcript = transcribe_audio(audio_file_path) 
            
            create_response(transcript)


# Float the footer container and provide CSS to target it with
footer_container.float("bottom: 30px;")