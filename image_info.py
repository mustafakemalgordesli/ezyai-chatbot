import base64
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
import boto3
import os

load_dotenv(override=True)

aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

bedrock_client = boto3.client(service_name='bedrock-runtime', region_name='us-east-1', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
model = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    client=bedrock_client
)


# Resim dosyasını okuyup, bu resmi bir yapay zeka ) analiz etmesi için bir istekte bulunarak, 
# görüntüdeki kıyafetle ilgili bir ürün açıklaması oluşturur.
def get_product_info(path: str):
    image1_media_type = "image/jpeg"
    
    with open(path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image1_media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": """
                    Describe the main outfit that takes up the most space in this image with a 1-2 sentence product description, 
                    as if it were an e-commerce product description. Add only concrete comments. Don't add your own interpretation. Must be Turkish!
                    """
                }
            ],
        }
    ]
    
    res = model.invoke(messages)
    return res.content