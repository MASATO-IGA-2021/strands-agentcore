# 改良版: 接続管理のベストプラクティス実装
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import asyncio
from contextlib import asynccontextmanager
import logging
logging.basicConfig(level=logging.DEBUG)

app = BedrockAgentCoreApp()

class MCPConnectionManager:
    """MCP接続の管理とプーリング"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._connection_pool = []
        self._tools_cache = None
        self._cache_expiry = None
        
    @asynccontextmanager
    async def get_connection(self, timeout=120):
        """タイムアウト付きの接続取得"""
        mcp = MCPClient(lambda: streamablehttp_client(
            f"https://mcp.tavily.com/mcp/?tavilyApiKey={self.api_key}"
        ))
        
        try:
            # タイムアウト付きで接続
            async with asyncio.timeout(timeout):
                async with mcp:
                    yield mcp
        except asyncio.TimeoutError:
            logging.error(f"MCP connection timeout after {timeout}s")
            raise
        except Exception as e:
            logging.error(f"MCP connection error: {e}")
            raise
    
    async def get_tools_cached(self, cache_duration=300):
        """ツール情報のキャッシュ付き取得（5分間キャッシュ）"""
        import time
        
        if (self._tools_cache and self._cache_expiry and 
            time.time() < self._cache_expiry):
            return self._tools_cache
            
        # キャッシュが無効な場合、新しく取得
        async with self.get_connection(timeout=10) as mcp:
            tools = mcp.list_tools_sync()
            self._tools_cache = tools
            self._cache_expiry = time.time() + cache_duration
            return tools

class RobustAgent:
    """接続切断に対応したロバストなエージェント"""
    
    def __init__(self, model: str, connection_manager: MCPConnectionManager):
        self.model = model
        self.connection_manager = connection_manager
        
    async def execute_with_retries(self, prompt: str, max_retries=3):
        """リトライ機能付きエージェント実行"""
        
        # ツール情報をキャッシュから取得
        tools = await self.connection_manager.get_tools_cached()
        
        agent = Agent(
            model=self.model,
            tools=tools,
            # 短いタイムアウトでツール実行
            tool_timeout=30
        )
        
        for attempt in range(max_retries):
            try:
                # 短い接続でストリーミング開始
                async with self.connection_manager.get_connection(timeout=60) as mcp:
                    # ツール実行時のみ接続を使用
                    agent._mcp_connection = mcp
                    
                    stream = agent.stream_async(prompt)
                    async for event in stream:
                        yield event
                    return
                    
            except (asyncio.TimeoutError, ConnectionError) as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数バックオフ

@app.entrypoint
async def invoke_agent(payload, context):
    """改良版エントリーポイント"""
    
    prompt = payload.get("prompt")
    tavily_api_key = payload.get("tavily_api_key")
    
    # 接続管理とキャッシング
    connection_manager = MCPConnectionManager(tavily_api_key)
    
    # ロバストなエージェント作成
    robust_agent = RobustAgent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        connection_manager=connection_manager
    )
    
    try:
        # リトライ付きで実行
        async for event in robust_agent.execute_with_retries(prompt):
            yield event
            
    except Exception as e:
        # エラーハンドリング
        yield {
            "type": "error",
            "data": f"エージェント実行中にエラーが発生しました: {str(e)}"
        }

# 代替案: 軽量版（シンプルな改善）
@app.entrypoint  
async def invoke_agent_simple(payload, context):
    """軽量改善版"""
    
    prompt = payload.get("prompt")
    tavily_api_key = payload.get("tavily_api_key")
    
    # 1. ツール情報を事前取得（短時間接続）
    mcp = MCPClient(lambda: streamablehttp_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}"
    ))
    
    # 短時間でツール情報のみ取得
    try:
        async with asyncio.timeout(10):  # 10秒タイムアウト
            with mcp:
                tools = mcp.list_tools_sync()
    except asyncio.TimeoutError:
        yield {"type": "error", "data": "ツール情報の取得がタイムアウトしました"}
        return
    
    # 2. エージェント作成（ツール情報は既に取得済み）
    agent = Agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        tools=tools
    )
    
    # 3. 実行時のみ接続（必要時に再接続）
    try:
        # ツール実行が必要になったときに再接続する仕組み
        with mcp:
            stream = agent.stream_async(prompt)
            async for event in stream:
                yield event
    except Exception as e:
        yield {"type": "error", "data": f"実行エラー: {str(e)}"}

app.run()
