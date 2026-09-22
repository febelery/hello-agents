import os

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

load_dotenv()

# typesafe_sdk 的 /v1/systemone 是专有接口，Vercel Gateway 不代理
# 直连 typesafe 官方 API，SDK 会自动使用 https://api.typesafe.ai
api_key = os.environ.get("TYPESAFE_API_KEY")
if not api_key:
    raise RuntimeError("请先设置 TYPESAFE_API_KEY 环境变量")

client = TypeSafeClient(api_key=api_key)

ticket = (
    "Hi, I've been trying to connect my Stripe account for 3 days "
    "and the integration keeps failing. I'm losing sales. Please help ASAP."
)

response = client.system_one(
    state=ticket,
    questions={
        "department": Choice(
            instructions="Which team should handle this",
            criteria={
                "billing": "Payment or subscription issues",
                "technical": "Bugs or integration problems",
                "sales": "Pricing or account questions",
            },
        ),
        "frustration": Score(
            instructions="How frustrated the customer appears",
            criteria=[
                "Calm, just stating facts",
                "Frustrated but civil",
                "Very angry, strong language",
            ],
        ),
        "is_urgent": Noul(
            instructions="The message conveys urgency or time-sensitivity",
        ),
    },
)

print("department :", response.answers["department"].choice)
print("frustration:", response.answers["frustration"].score)
print("is_urgent  :", response.answers["is_urgent"].noul)
