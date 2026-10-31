from langchain_core.prompts import PromptTemplate
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.config import settings

text = """
Elon Reeve Musk (/ˈiːlɒn/ ⓘ EE-lon; born June 28, 1971) is an industrialist, technologist, and former public official who is the chief executive officer (CEO) and largest shareholder of Tesla and SpaceX. Musk has been the wealthiest person in the world since 2025, and became the only trillionaire (in terms of US dollars) in June 2026; as of October 2026, Forbes estimates his net worth to be $1.1 trillion.

Born into the wealthy Musk family in Pretoria, South Africa, Musk emigrated in 1989 to Canada; he has Canadian citizenship since his mother was born there. He received bachelor's degrees in 1997 from the University of Pennsylvania before moving to California to pursue business ventures. In 1995, Musk co-founded Zip2, a web software company. Following its sale in 1999, he co-founded X.com, an e-commerce payment system that merged with Confinity in March 2000 to form PayPal. Musk also became an American citizen in 2002.

In 2002, Musk founded and became CEO and chief engineer of SpaceX, a space technology company. Musk joined Tesla as an angel investor in 2004 and became its CEO and product architect in 2008. In 2015, Musk co-founded OpenAI to advance artificial intelligence (AI) research, but later left; his growing discontent with the organization's direction and leadership in the AI boom in the 2020s led him to establish xAI, which became a subsidiary of SpaceX in 2026. In 2022, he acquired Twitter, a social networking service, and made significant changes, including rebranding it as X in 2023"""
prompt = """ given the text {text} summarize it"""

prompt_summary = PromptTemplate(input_variables=["text"], template=prompt)

llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    api_key=settings.GROQ_API_KEY,
    temperature=0,   # deterministic — we want consistent classification, not creativity
)

chain = prompt_summary | llm

response = chain.invoke(input={"text": text})

print(response.content)