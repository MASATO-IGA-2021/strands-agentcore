# 必要なライブラリをインポート
from dotenv import load_dotenv
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# .envファイルから環境変数を読み込む
load_dotenv()

# MCPクライアントを作成
mcp = MCPClient(
    lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")
)

# MCPクライアントを起動しながら、エージェント作成＆呼び出し
with mcp:
    agent = Agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        tools=mcp.list_tools_sync()
    )
    agent("Bedrock Agentcoreのランタイムってどんな機能？一言で説明して。")
