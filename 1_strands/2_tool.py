# 必要なライブラリをインポート
import os
from dotenv import load_dotenv
from strands import Agent, tool
from tavily import TavilyClient

# .envファイルから環境変数を読み込む
load_dotenv()

# Web検索関数をツールとして定義
@tool
def search(query):
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    return tavily.search(query)

# ツールを設定したエージェントを作成
agent = Agent(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    tools=[search]
)

# エージェントを起動
agent("JAWS-UG主催のAI Builders Dayはどこで開催される？")
