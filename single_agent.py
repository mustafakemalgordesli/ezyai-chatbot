from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import MessagesPlaceholder
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Annotated, Sequence, TypedDict, Optional, List
from typing_extensions import TypedDict
import operator
from dotenv import load_dotenv
import functools
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import tools_condition
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
import sqlite3
from langchain_chroma import Chroma
from langchain.tools.base import StructuredTool
import boto3
from langchain_aws import ChatBedrock, BedrockEmbeddings
import os

load_dotenv(override=True)

aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name='us-east-1', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

class GlobalState:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalState, cls).__new__(cls)
            cls._instance.value = None  
        return cls._instance
    
    def set_value(self, value):
        self.value = value
    
    def get_value(self):
        return self.value

state = GlobalState()

class LoginState:
    user = None
    isStarted = False
    username = ""
    password = ""   

loginState = LoginState()

embeddings = BedrockEmbeddings(model_id="cohere.embed-multilingual-v3", client=bedrock_client)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory=os.path.join(".", "chroma_langchain_db"), 
)

# This tool allows the user to find the product to be recommended by semantic search.
# Do not ask the user for more information. Make the most appropriate suggestion.
# It uses detailed descriptions of only one product to be shown to the user.
# This tool allows the user to find the product that matches the information entered.
# Do not ask for more information from the user. Make the most appropriate suggestion.
    
# This tool allows the user to find the product that matches the information entered.
# Do not ask for more information from the user. Make the most appropriate suggestio

# this tool is used to search for similar products

def ProductSearch(path: Optional[str] = None, query_params: Optional[str] = None, maxprice: Optional[float] = 2000, minprice: Optional[float] = 0, vote: Optional[float] = 0) -> str:
    """
    This tool is used to search for similar products and allows to find the product that matches the information entered.
    Do not ask for more information. Make the most appropriate suggestion.
    args: 
        query_params: detailed description of the product, do not ask for more information. in the original language.
        maxprice: The maximum price of the product, if any.
        minprice: The minimum price of the product, if any.
        vote: vote rate of product, if any.
    """
    # product = " ".join(query_params.values()).lower()
    print("INPUT TEXT: #######\n", path, maxprice, minprice, query_params, vote)
    print("###############")
    
    if float(vote) > 5:
        vote = 0
        
    price_filter = {
        "$and": [
            {"price": {"$gte": minprice}},
            {"price": {"$lte": maxprice}},
            {"vote": {"$gte": float(vote)}}
        ]
    }
    results = vector_store.similarity_search_with_score(query_params, k=1, filter=price_filter)
    message = ""
    for res, score in results:
        print(f"*[SIM={score:3f}] {res.page_content}  {res.metadata}")
        print(res.metadata.get("id"))
        conn = sqlite3.connect(os.path.join("assets", "products.db"))
        cur = conn.cursor()
        res = cur.execute(f'select * from products where id = {int(res.metadata.get("id"))}')
        item = res.fetchone()
        print(item[10])
        state.set_value(item)
        message += "Bulduğum ürün: " + item[1] + " \türün fiyatı: " + str(item[3]) + " \türün puanı: " + str(item[10])
    return message


def BotInfo(path: Optional[str] = None, query_params: Optional[dict] = None) -> str:
    """This tool gives information to the user about the bot."""
    print("###############BOT INFO#####################\n")
    return "Ben Alışveriş Asistanınız EZY.\nAlışveriş süreçlerinizde size yardımcı olmak için burdayım.\nArağınız ürünü bulmakta size yardımcı olabilirim."

def OrderStatus(path: Optional[str] = None, query_params: Optional[dict] = None) -> str:
    """
    This tool allows customers to check order status.
    If there is no order number for this transaction, it returns the information of the user's last order. Therefore, shipping information is not required.
    """
    print("###############ORDER STATUS#####################\n")
    if loginState.user is None:
        loginState.isStarted = True
        return "Bu işlem için kullanıcı girişi yapmalısınız."
    return "Siparişiniz kargoya verildi. Kargo numaranız: #123456"

def UserLogin() -> str:
    """
    This tool will initiate the user login process, this tool is run to log in.
    """
    print("User login processs")
    if loginState.user is not None:
        return "Zaten kullanıcı girişi yaptınız."
    loginState.isStarted = True
    return "İşlem başlatıldı."

def is_six_digit_number(s):
    s = s.lstrip('#')
    return s.isdigit() and len(s) == 6

def normalize_cargo_number(cargo_number):
    return cargo_number.lstrip('#')

cargo_status_list = ["Kargoya verildi.", "Dağıtım şubesinde.", "Teslimat şubesinde. Gün içerisinde dağıtıma çıkarılacak."]

branch_list = ["İzmir Şubesi", "Ödemiş Şubesi", "İstanbul Şubesi"]

def CargoStatus(path: Optional[str] = None, cargo_number: Optional[str] = None) -> str:
    """
    This tool allows customers to check where their cargo is or what condition it is in.
    If there is no cargo number for this transaction, it returns the information of the user's last cargo. Therefore, shipping information is not required.
    args: 
        cargo_number: it is the cargo number, if any.
    """
    print("###############CARGO STATUS#####################", cargo_number)
    
    row = None
    
    conn = sqlite3.connect(os.path.join(".", "assets", "cargo.db"))
    cursor = conn.cursor()
    
    if cargo_number != None:
        normalized_number = "#" + normalize_cargo_number(cargo_number)
        
        if is_six_digit_number(normalized_number):
            cursor.execute('''
                SELECT * FROM Cargo WHERE cargo_number = ?
            ''', (normalized_number, ))
            row = cursor.fetchone()    
    
    if loginState.user is None and row is None:
        return "Kargo bilgilerinizi görüntüleyebilmem kullanıcı girişi yapmanız veya kargo numarasını girmeniz gerekmektedir."

    if row is None:
        cursor.execute('''
            SELECT * FROM Cargo WHERE  user_id = ?  
            ORDER BY created_at DESC
            LIMIT 1
        ''', (1, ))
        row = cursor.fetchone()
        print(row[1], row[2], row[3], row[4])
    
    if row:
        cargo_status = cargo_status_list[row[3]]
        cargo_branch = branch_list[row[4]]
        return "Kargo kodu: " + row[1] + ".\t" + cargo_status + ".\tBunuduğu şube: " + cargo_branch + "."
    else:
        return "Kargo bulunamadı."


def InvalidQuestion(path: Optional[str] = None, query_params: Optional[dict] = None) -> str:
    """use these tools when you are asked meaningless,invalid,empty,ridiculous,valid questions."""
    print("###############INVALİD QUESTİON#####################\n")
    return "Ben Alışveriş Asistanınız EZY. Daha fazla bilgi verebilir misiniz?."


def get_user_campaigns(user_id):
    conn = sqlite3.connect(os.path.join(".", "assets", "campaign.db")) 
    cursor = conn.cursor()
    query = '''
        SELECT users.name, campaigns.name, campaigns.description, campaigns.discount_rate, campaigns.valid_until
        FROM user_campaigns
        JOIN users ON user_campaigns.user_id = users.user_id
        JOIN campaigns ON user_campaigns.campaign_id = campaigns.campaign_id
        WHERE users.user_id = ?
    '''
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def CampaignInformation() -> List[str]:
    """
    This tool informs you about campaigns specifically assigned to the user if the user is logged in, and about popular campaigns if the user is not logged in.
    """
    res = []
    if loginState.user is not None:
        user_campaigns = get_user_campaigns(1)
        for campaign in user_campaigns:
            res.append(f"Kampanya: {campaign[1]}, Açıklama: {campaign[2]}, İndirim Oranı: %{campaign[3]*100}, Geçerlilik: {campaign[4]}")
    else:        
        res.append(f"Kampanya: Sezon Sonu İndirimi, Açıklama: Sezon sonu ürünlerinde %20 indirim, İndirim Oranı: %20, Geçerlilik: 2024-10-30")
        res.append("Size özel tanımladığımız kampanyalarınızı görüntülemek için giriş yapabilirsiniz.")
    return res
    
tools = [
    StructuredTool.from_function(ProductSearch),
    StructuredTool.from_function(BotInfo),
    StructuredTool.from_function(CampaignInformation),
    StructuredTool.from_function(UserLogin),
    StructuredTool.from_function(CargoStatus),
    StructuredTool.from_function(OrderStatus),
    StructuredTool.from_function(InvalidQuestion),
]


def create_agent(llm, tools, system_message: str):
    """Create an agent"""
    
    llm_with_tools = llm.bind_tools(tools)
    
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a helpful and very powerful AI assistants.
            Use the provided tools to progress towards answering the question.
            If you are unable to fully answer, that's OK, another assistant with different tools
            will help where you left off. Execute what you can to make progress.
            If you or any of the other assistants have the final answer or deliverable,
            You should provide customers with user-friendly, understandable and short messages,
            Answer briefly the answers received from the tools without adding your own subjective interpretation.
            prefix your response with FINAL ANSWER so the team knows to stop.
            REMEMBER! The final answer should be in Turkish.
            You have access to the following tool: {tool_names}.
            """
        ), 
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
    
    return prompt | llm_with_tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender: str

def agent_node(state, agent, name):
    result = agent.invoke(state)
    if isinstance(result, ToolMessage):
        pass
    else:
        result = AIMessage(**result.dict(exclude={"type", "name"}), name=name)
    return {
        "messages": [result],
        "sender": name,
    }

llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    client=bedrock_client
)

shopping_agent = create_agent(
    llm,
    tools=tools,
    system_message="Find the appropriate tool and never change the incoming message and forward it.",
)

shopping_node = functools.partial(agent_node, agent=shopping_agent, name="ShoppingAssistant")

tool_node = ToolNode(tools)

workflow = StateGraph(AgentState)

workflow.add_node("ShoppingAssistant", shopping_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "ShoppingAssistant")

workflow.add_conditional_edges(
    "ShoppingAssistant",
    tools_condition,
)
workflow.add_edge("tools", "ShoppingAssistant")

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)