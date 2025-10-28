# フロントエンド側の接続切断対策
import streamlit as st
import boto3
import json
import time
import os
from dotenv import load_dotenv  
from botocore.config import Config

# 環境変数をロード
load_dotenv()

# タイムアウト設定を追加
config = Config(
    read_timeout=300,  # 5分
    retries={'max_attempts': 3}
)

# チャットボックスを描画
if prompt := st.chat_input("メッセージを入力してね"):
    # ユーザーのプロンプトを表示
    with st.chat_message("user"):
        st.markdown(prompt)

    # エージェントの回答を表示
    with st.chat_message("assistant"):
        # AgentCoreランタイムを呼び出し
        agentcore = boto3.client('bedrock-agentcore', config=config)
        payload = json.dumps({
            "prompt": prompt,
            "tavily_api_key": os.getenv("TAVILY_API_KEY")
        })

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = agentcore.invoke_agent_runtime(
                    agentRuntimeArn=os.getenv("AWS_BEDROCKAGENTCORE_ARN"),
                    payload=payload.encode()
                )
                
                # ストリーミングレスポンス処理
                container = st.container()
                text_holder = container.empty()
                buffer = ""
                
                # タイムアウト付きでレスポンス処理
                start_time = time.time()
                timeout_seconds = 300  # 5分
                
                try:
                    for line in response.get("response", "").iter_lines():
                        # タイムアウトチェック
                        if time.time() - start_time > timeout_seconds:
                            container.error("⏰ 処理がタイムアウトしました")
                            break
                            
                        if line and line.decode("utf-8").startswith("data: "):
                            data = line.decode("utf-8")[6:]

                            # 文字列コンテンツの場合は無視
                            if data.startswith('"') or data.startswith("'"):
                                continue

                            try:
                                # 読み込んだ行をJSONに変換
                                event = json.loads(data)

                                # ツール利用を検出
                                if "event" in event and "contentBlockStart" in event["event"]:
                                    if "toolUse" in event["event"]["contentBlockStart"].get("start", {}):
                                        # 現在のテキストを確定
                                        if buffer:
                                            text_holder.markdown(buffer)
                                            buffer = ""
                                        # ツールステータスを表示
                                        container.info("🔍 Tavily検索ツールを利用しています")
                                        text_holder = container.empty()

                                # テキストコンテンツを検出
                                if "data" in event and isinstance(event["data"], str):
                                    buffer += event["data"]
                                    text_holder.markdown(buffer)
                                elif "event" in event and "contentBlockDelta" in event["event"]:
                                    buffer += event["event"]["contentBlockDelta"]["delta"].get("text", "")
                                    text_holder.markdown(buffer)
                                    
                            except json.JSONDecodeError as e:
                                st.warning(f"JSON解析エラー: {e}")
                                continue
                                
                    # 最後に残ったテキストを表示
                    text_holder.markdown(buffer)
                    break  # 成功した場合はリトライループを抜ける
                    
                except Exception as e:
                    if buffer:  # 部分結果がある場合は表示
                        text_holder.markdown(buffer)
                        container.warning(f"部分的な結果を表示中 - エラー: {str(e)}")
                    raise
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    st.warning(f"試行 {attempt + 1} 失敗: {str(e)} - 再試行中...")
                    time.sleep(2 ** attempt)  # 指数バックオフ
                else:
                    st.error(f"エージェント実行に失敗しました: {str(e)}")
                    st.info("💡 ネットワーク接続を確認するか、質問を短くして再試行してください")



# # 必要なライブラリをインポート
# import os, boto3, json
# import streamlit as st
# from botocore.config import Config
# from dotenv import load_dotenv

# config = Config(
#     read_timeout=1500,   # 読み取りタイムアウトを長く
#     connect_timeout=1200,
#     retries={'max_attempts': 5}
# )

# # .envファイルから環境変数をロード
# load_dotenv(override=True)

# # サイドバーで設定を入力
# # with st.sidebar:
# #     agent_runtime_arn = st.text_input("AgentCoreランタイムのARN")
# #     tavily_api_key = st.text_input("Tavily APIキー", type="password")

# # タイトルを描画
# st.title("なんでも検索エージェント")
# st.write("Strands AgentsがMCPサーバーを使って情報収集します！")

# # チャットボックスを描画
# if prompt := st.chat_input("メッセージを入力してね"):
#     # ユーザーのプロンプトを表示
#     with st.chat_message("user"):
#         st.markdown(prompt)

#     # エージェントの回答を表示
#     with st.chat_message("assistant"):
#         # AgentCoreランタイムを呼び出し
#         agentcore = boto3.client('bedrock-agentcore', config=config)
#         payload = json.dumps({
#             "prompt": prompt,
#             "tavily_api_key": os.getenv("TAVILY_API_KEY")
#         })
#         response = agentcore.invoke_agent_runtime(
#             agentRuntimeArn=os.getenv("AWS_BEDROCKAGENTCORE_ARN"),
#             payload=payload.encode()
#         )

#         ### ここから下はストリーミングレスポンスの処理 ------------------------------------------
#         container = st.container()
#         text_holder = container.empty()
#         buffer = ""
#         print(response.get("response"))
#         # レスポンスを1行ずつチェック
#         for line in response.get("response", "").iter_lines():
#             if line and line.decode("utf-8").startswith("data: "):
#                 data = line.decode("utf-8")[6:]

#                 # 文字列コンテンツの場合は無視
#                 if data.startswith('"') or data.startswith("'"):
#                     continue

#                 # 読み込んだ行をJSONに変換
#                 event = json.loads(data)

#                 # ツール利用を検出
#                 if "event" in event and "contentBlockStart" in event["event"]:
#                     if "toolUse" in event["event"]["contentBlockStart"].get("start", {}):
#                         # 現在のテキストを確定
#                         if buffer:
#                             text_holder.markdown(buffer)
#                             buffer = ""
#                         # ツールステータスを表示
#                         container.info("🔍 Tavily検索ツールを利用しています")
#                         text_holder = container.empty()

#                 # テキストコンテンツを検出
#                 if "data" in event and isinstance(event["data"], str):
#                     buffer += event["data"]
#                     text_holder.markdown(buffer)
#                 elif "event" in event and "contentBlockDelta" in event["event"]:
#                     buffer += event["event"]["contentBlockDelta"]["delta"].get("text", "")
#                     text_holder.markdown(buffer)
#             print(data)

#         # 最後に残ったテキストを表示
#         text_holder.markdown(buffer)
#         ### ------------------------------------------------------------------------------
