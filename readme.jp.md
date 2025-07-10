# 電卓-MCP (Calculator-MCP)

> 高精度の34桁計算機マイクロサービスで、あらゆるLLMワークフローに簡単に組み込むことができます。REST APIと[MCP](https://github.com/cascade-ai/mcp)サーバーの両方を公開し、エージェントが安全かつ決定論的に数式を評価できるようにします。

---
## サポートされている式

Calculator-MCPは、標準的な算術演算と、科学関数および定数のセットを理解します。

| カテゴリ | 構文 / 例 |
|----------|-----------------|
| 加算 / 減算 | `1 + 2 - 3` |
| 乗算 / 除算 | `4 * 5 / 2` |
| べき乗 | `2 ** 10` → `1024` |
| 括弧 & 単項 +/- | `-(1 + 2) * 3` |
| 定数 | `pi`, `e` |
| 三角関数 | `sin(pi/6)`, `cos(pi/3)`, `tan(pi/4)` |
| 逆三角関数 | `asin(0.5)`, `acos(1)`, `atan(1)` |
| 対数 | `log(8, 2)` (底は任意; `log(10)` = ln) |
| 平方根 & べき乗 | `sqrt(2)`, `pow` は `**` を使用 |
| 指数関数 | `exp(1)` |
| 絶対値 | `abs(-3.5)` |

すべての計算は、34桁精度の `result` 文字列を返します。

---
## なぜこれが必要なのですか？

大規模言語モデルは、正確な算術が苦手であることで有名です。数値に関する事実を幻覚したり、不正確な結果を返したりすることがあります。**Calculator-MCP**は、エージェントに決定論的な34桁精度の神託を提供し、すべての計算が信頼でき、再現可能であることを保証します。

---
## 特徴
- Pythonの `decimal` を使用した34桁の十進数演算
- 標準的な数学関数：三角関数、対数、べき乗など
- RESTエンドポイント：`POST /evaluate`、`GET /healthz`
- 関数呼び出し/ツール呼び出しに対応したMCP関数 `calc.evaluate`
- YAML駆動のテストスイートと100%型付けされたコードベース

---
## クイックスタート

### 前提条件
* Python ≥ 3.11 ([uv](https://github.com/astral-sh/uv)で管理)

`uv`をまだインストールしていない場合は、一度だけインストールしてください：
```bash
pip install uv
```

### インストール
```bash
git clone https://github.com/your-org/calculator-mcp.git
cd calculator-mcp
uv pip install -r requirements.txt   # 自動的に .venv を作成します
```

---
### REST APIの実行
```bash
uv run python -m uvicorn app.main:app --reload --port 8000
# Swagger UI: http://127.0.0.1:8000/docs
```

### MCPサーバーの実行 (HTTP)
```bash
uv run python -m uvicorn server.main:app --reload --port 9000
```
*注意：直接的なツール統合（例：Cursor内）については、以下の `stdio` サーバーの説明を参照してください。*

---
## 大規模言語モデル (LLM) との統合

このプロジェクトには、モデルコンテキストプロトコル（MCP）を使用して、計算機をLLM搭載エージェントと統合する方法を示す、完全で実行可能な例が含まれています。

エージェントは、公式の `mcp` Pythonライブラリを使用して、自然言語のクエリに基づいて計算機の関数を動的に検出し、呼び出します。

### 仕組み

この例は、公式のMCP `stdio` クライアントパターンに従っています：

1.  **`stdio_server.py`**: 標準入出力を介して通信する軽量のMCPサーバー。コアの `calculate` 関数をインポートして公開します。
2.  **`examples/smart_calculator_agent.py`**: `stdio_server.py` をサブプロセスとして起動するクライアントエージェント。OpenAIのGPT-4を使用してユーザーのクエリを解釈し、必要に応じて公式の `mcp` ライブラリを使用して計算機ツールを呼び出します。

この分離により、コアの計算機ロジックがサーバー実装から独立していることが保証されます（HTTPまたは `stdio` を介して実行可能）。

### 例の実行

1.  **OpenAI APIキーを設定する**：

    プロジェクトのルートに `.env` ファイルを作成し、キーを追加します：

    ```
    OPENAI_API_KEY="sk-..."
    ```

2.  **エージェントを実行する**：

    `uv` を使用してクライアントスクリプトを実行します。クライアントは自動的に `stdio` サーバーを起動します。

    ```bash
    uv run python examples/smart_calculator_agent.py
    ```

### サンプルコード (`smart_calculator_agent.py`)

エージェントの完全なソースコードは `examples` ディレクトリにあります。`stdio` サーバーを起動し、LLMと対話する方法を示しています。

[**エージェントのソースコードを表示 (`smart_calculator_agent.py`)**](./examples/smart_calculator_agent.py)

---

## MCP互換ツールでの使用 (例: Cursor)

プロジェクトのルートディレクトリに `.cursor/mcp.json` ファイルを作成することで、この計算機をCursorなどのMCP互換クライアントに直接統合できます。このファイルは、ツールを見つけて通信する方法をCursorに伝えます。

### 方法1：実行中のHTTPサーバーへの接続 (推奨)

この方法は、MCPサーバーが実行中で、Cursorから接続したい場合に使用します。

1.  **MCPサーバーを起動する**：まず、仕様に準拠したJSON-RPCサーバーが実行されていることを確認します。
    ```bash
    uv run python -m uvicorn server.main:app --reload --port 9000
    ```

2.  **Cursorを設定する**：
    *   プロジェクトに `.cursor/mcp.json` という名前のファイルを作成します。
    *   次のJSON構成を追加します。これにより、サーバーが指定されたURLで利用可能であり、標準のMCPプロトコルを話すことがCursorに伝わります。
      ```json
      {
        "mcpServers": {
          "calculator": {
            "url": "http://127.0.0.1:9000"
          }
        }
      }
      ```
    *   ファイルを保存します。Cursorは自動的にそれを検出し、サーバーに `tools/list` リクエストを送信し、`calc.evaluate` ツールをAIが利用できるようにします。

### 方法2：ローカルStdioツールとして実行

この代替方法は、別のサーバープロセスを管理したくない場合に便利です。Cursorは、標準入出力を使用してオンデマンドでツールを起動および停止します。

1.  **Cursorを設定する**：
    *   プロジェクトに `.cursor/mcp.json` という名前のファイルを作成します。
    *   ファイルに次のJSON構成を追加します：
      ```json
      {
        "mcpServers": {
          "calculator": {
            "command": "uv",
            "args": ["run", "python", "stdio_server.py"],
            "cwd": "${workspaceFolder}"
          }
        }
      }
      ```
    *   ファイルを保存します。Cursorはバックグラウンドで `stdio_server.py` スクリプトを実行し、`calculate` 関数をAIが利用できるようにします。

---
## テスト
```bash
uv run pytest -q
```

---
## ライセンス
MIT
