import streamlit as st
from PIL import Image
from dotenv import load_dotenv
from langchain_core.messages import (
    HumanMessage,
)
import uuid
from single_agent import graph, state, GlobalState, loginState
from image_info import get_product_info
from utils import mask_password, display_stars, calculate_file_hash
import re
import time
import os
load_dotenv(override=True)

product_info_state = GlobalState()

col1, col2 = st.columns([1, 5])

with col1:
    st.image(os.path.join(".", "assets", "logo.png"), width=100)
with col2:
    st.title("EZYAI")

with st.expander("Örnek Mesajlar"):
    st.info('500 tl altı siyah jogger arıyorum', icon="ℹ️")
    st.info('Kargom nerde?', icon="ℹ️")
    st.info('Siyah kumaş pantolonum var kombinimi tamamlar mısın?', icon="ℹ️")
    
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
            res = get_product_info(path)
            st.session_state.messages.append({"role": "resim", "content": path})
            st.success(res)
            st.session_state.productinfo = res
            st.image(img, caption='Yüklenen Resim', width=100)
            st.success("Resim başarıyla yüklendi!")
    except Exception as e:
        st.error("Lütfen geçerli bir resim dosyası yükleyin.")     


# Ürünle ilgili bilgilerin gösterildiği kart yapısı
def get_product_card(product):
    # print(product)
    with st.container(border=True):
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(product[5], width=100)
        with col2:
            st.write(product[1])
            st.write(product[3])
            # st.write(product[10])
            st.markdown(display_stars(product[10]), unsafe_allow_html=True)
            if st.button("Sepete ekle", key=str(uuid.uuid4())):
                st.write("Why hello there")



if "threadid" not in st.session_state:
    st.session_state.threadid = str(uuid.uuid4())
    
if "loggedin" not in st.session_state:
    st.session_state.loggedin = False

if "messages" not in st.session_state:
    st.session_state.messages = []

# Geçmiş kullanıcı mesajlarının saklandığı ve ekrana bastırıldığı kısım
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


# Kullanıcının giriş yapıp yapmama durumuna göre butonlar gösteriliyo
# Giriş yapmışsa 'Çıkış Yap' butonu, giriş yapmamışsa 'Giriş Yap' butonu gösterilir
if st.session_state.loggedin is False:
    if st.button('Giriş Yap', use_container_width=True):
        loginState.isStarted = True
        loginState.username = ""
        loginState.password = ""
        response = "Kullanıcı adınızı giriniz:"
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
else:
    if st.button('Çıkış Yap', use_container_width=True):
        loginState.isStarted = False
        loginState.username = ""
        loginState.password = ""
        loginState.user = None
        st.session_state.loggedin = False
        response = "Çıkış yaptınız."
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

if prompt := st.chat_input("Size nasıl yardımcı olabilirim?"):
        if loginState.isStarted:
            if loginState.username == "":
                loginState.username  = prompt
            elif loginState.password == "":
                loginState.password = prompt
                prompt = mask_password(prompt)
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        
        if st.session_state.productinfo != "":
            prompt = prompt + " " + st.session_state.productinfo 
            st.session_state.productinfo = ""
        
        with st.chat_message("assistant"):
            start_time = time.perf_counter()
            config = {
                "configurable": {
                    "thread_id": st.session_state.threadid,
                }
            }
            
            response = None
            
            if loginState.isStarted is False:
                events = graph.invoke(
                    {
                        "messages": [
                            HumanMessage(content=prompt)
                        ],
                    }, config=config
                )
            
                response = events['messages'][-1].content
                
                print(response)
                
                patterns = [
                    r'FINAL ANSWER:\s*(.*)',
                    r'FİNAL CEVAP:\s*(.*)',
                    r'FINAL CEVAP:\s*(.*)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response, re.DOTALL)
                    if match:
                        response = match.group(1)
                        break 
    
            if loginState.isStarted is True and st.session_state.loggedin is False:
                if loginState.username == "":
                    response = "Kullanıcı adınızı giriniz:"
                elif loginState.password == "":
                    response = "Şifrenizi giriniz:"
                else:
                    if loginState.username == "kemal" and loginState.password == "1234":
                        response = "Kullanıcı girişi başarılı. Yapmak istediğiniz işlemi girebilirsiniz."
                        st.session_state.loggedin = True
                        loginState.isStarted = False
                        loginState.user = loginState.username
                        loginState.username = ""
                        loginState.password = ""
                        st.write(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()
                    else:
                        response = "Kullancı girişi maalesef yapılamadı."
                        loginState.isStarted = False
                        loginState.username = ""
                        loginState.password = ""
                        
                    
            if response is not None:            
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            st.markdown(f"İki işlem arasında geçen süre: {elapsed_time:.6f} saniye")
            
            if state.get_value() is not None:
                get_product_card(state.get_value())
                st.session_state.messages.append({"role": "product", "content": state.get_value()})
                state.set_value(None)
