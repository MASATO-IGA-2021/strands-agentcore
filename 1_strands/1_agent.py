# 必要なライブラリをインポート
from dotenv import load_dotenv
from strands import Agent

# .envファイルから環境変数を読み込む
load_dotenv()

# エージェントを作成して起動
agent = Agent("us.anthropic.claude-haiku-4-5-20251001-v1:0")
agent("JAWS-UG主催のAI Builders Dayはどこで開催される？")