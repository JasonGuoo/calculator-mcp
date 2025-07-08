# Calculator MCP Server – 系统设计草案

**创建时间：2025-07-06 10:05:49 (CST)**

---

## 1. 总体架构
```
       ┌──────────────┐
       │    Client    │ ① HTTP (JSON-RPC / REST)
       └──────┬───────┘
              │
              ▼
       ┌────────────────┐
       │  MCP Server    │ ② 调用 CLI 进程或直接 import 库
       │  (FastAPI)     │
       └──────┬─────────┘
              │
              ▼
 ┌────────────────────────┐
 │ calculator_cli.py      │ ③ 命令行入口
 │ (argparse / click)     │--> 解析命令行参数
 └──────┬─────────────────┘
        │ import
        ▼
 ┌────────────────────────┐
 │ calc_core/             │ ④ 纯 Python 库
 │   ├─ parser.py         │
 │   ├─ evaluator.py      │
 │   └─ __init__.py       │
 └────────────────────────┘
```

---

## 2. 输入 / 输出规范
### 2.1 底层库 (`calc_core`)
- **输入**：`str`，示例 `"3*(4+5)-sqrt(16)"`
- **输出**：`float | int | Decimal`（按实现决定）

### 2.2 CLI (`calculator_cli.py`)
- **调用格式**：
  ```bash
  python calculator_cli.py "3*(4+5)-sqrt(16)"
  ```
- **STDOUT**：计算结果（纯文本）

### 2.3 MCP Server
- **POST** `/evaluate`
  - Request JSON: `{ "expression": "3*(4+5)-sqrt(16)" }`
  - Response JSON: `{ "result": 23 }`
- **错误**：HTTP 400，payload `{ "error": "Invalid expression" }`

### 2.4 预定义常量（15 位有效数字）

| 标识符 | 含义 | 数值 |
|--------|------|------|
| `pi` | 圆周率 | `3.14159265358979` |
| `e` | 自然常数 | `2.71828182845905` |

### 2.5 预定义函数

| 函数 | 说明 | 参数约束 | 返回值 / 备注 |
|------|------|---------|--------------|
| `sin(x)` | 正弦函数 | `x` 单位：弧度 | `[-1, 1]` |
| `cos(x)` | 余弦函数 | `x` 单位：弧度 | `[-1, 1]` |
| `tan(x)` | 正切函数 | `x` 单位：弧度；当 `cos(x)=0` 时抛出 `DomainError` | `ℝ` |
| `asin(x)` | 反正弦 | `x ∈ [-1,1]` | 返回弧度值 |
| `acos(x)` | 反余弦 | `x ∈ [-1,1]` | 返回弧度值 |
| `atan(x)` | 反正切 | `x ∈ ℝ` | 返回弧度值 |
| `sqrt(x)` | 平方根 | `x ≥ 0` | 若 `x < 0` 抛出 `DomainError` |
| `log(x, b=10)` | 对数 | `x > 0`；可选底 `b > 0 且 b ≠ 1`。省略 `b` 时默认为 `e`（自然对数） | |
| `exp(x)` | 自然指数 | `x ∈ ℝ` | 计算 `e^x` |
| `abs(x)` | 绝对值 | `x ∈ ℝ` | 非负实数 |

> **大小写**：所有常量与函数名均区分大小写，建议使用全小写。
>
> **空白**：表达式中可插入任意空白字符，解析器将忽略。

> **精度要求**：内部计算与常量值统一保证 **15 位有效数字**。所有算术与函数结果默认保留 15 位有效数字，超出部分按 `Decimal` 四舍五入处理。

#### 使用示例

```text
sin(pi/2)            # 1
log(100, 10)         # 2
sqrt(16) + tan(pi/4) # 5
asin(1) + acos(0)    # 1.5708 + 1.5708
```

---

## 3. 功能模块与主要类
| 模块 | 主要职责 |
|------|-----------|
| `ExpressionParser` | `parse(expr: str) -> AST`，基于 **lark-parser** 自定义文法生成抽象语法树 |
| `Evaluator` | `evaluate(ast) -> Number`；支持 `+ - * / ^`、括号、函数，例如 `sin`, `sqrt` 等；暴露 `calculate(expr)` |
| CLI | 解析命令行参数，调用 `calc_core.calculate`，打印结果；错误时返回非零 exit code |
| MCP Server | 基于 FastAPI 暴露 `/evaluate`；校验请求体，调用库或 CLI；错误转成 HTTP 400 |
| 错误处理 | 自定义 `CalcError` 统一异常 |

---

## 4. 实现方式建议

### 4.0 技术选型确认
- 解析库：**lark-parser**（AST 解析）
- 高精度：`decimal.Decimal`
- 环境管理：**uv**（所有安装/执行命令均使用 `uv` 前缀，如 `uv pip install`, `uv run pytest`）
- 错误类型：自定义 `CalcError`

1. **安全性**：使用 `lark` 自定义文法并绝不调用 `eval()`。
2. **精度**：若需要高精度可用 `decimal.Decimal`。
3. **错误处理**：统一抛出 `CalcError`，上层捕获处理。
4. **部署**：FastAPI + Uvicorn；可用多 worker。

---


### 4.1 解析器实现原理（Lark）

#### 实现流程概述

> **名词澄清**：下文出现的 `Transformer` 均指 **Lark** 中的解析树转换类 `lark.Transformer`。它只是将语法树映射/转换成其他结构或计算结果，**与机器学习领域的 Transformer 神经网络模型（如 GPT、BERT）毫无关联**。
1. **定义文法**（`parser.py`）
   ```ebnf
   ?start: sum
   ?sum: product
        | sum "+" product   -> add
        | sum "-" product   -> sub
   ?product: power
        | product "*" power  -> mul
        | product "/" power  -> div
   ?power: atom
        | power "^" atom     -> pow
   ?atom: NUMBER            -> number
        | FUNC "(" sum ")"  -> func
        | "(" sum ")"
   %import common.SIGNED_NUMBER -> NUMBER
   %import common.CNAME        -> FUNC
   %import common.WS_INLINE
   %ignore WS_INLINE
   ```
2. **Parse Tree → AST / 直接计算**
   - 继承 `lark.Transformer`；对 `add`, `sub`, `mul`, `div`, `pow`, `number`, `func` 等节点返回 `Decimal` 或对应操作结果。
   - 数字 token 在 `number` 动作内执行 `Decimal(value)` 转换。
   - 函数调用节点只允许白名单（例如 `sqrt`, `sin`, `cos`, `tan`, `log`）。
3. **Evaluator （`evaluator.py`）**
   - 若在 Transformer 中已直接返回 `Decimal`，则解析过程即完成计算，返回最终值。
   - 遇到错误（语法、除零、超出范围）抛出 `CalcError`。
4. **性能**
   - 对于普通表达式（<1K token）解析 <1ms；使用 `LALR` 模式提升速度。

#### Lark 简介
- **项目主页**：<https://github.com/lark-parser/lark>
- **核心特点**：
  - 支持近乎所有上下文无关文法（LALR、Earley、CYK）。
  - 自带 Transformer/Visitor API，将 Parse Tree 转成任意数据结构。
  - 内置工具（文法可视化、调试、自动完成功能）。
  - 无第三方依赖；在 PyPI 活跃维护，MIT 许可证。
- **体积 & 性能**：单文件核心 <200KB；对于 LALR 文法，性能接近 `ply/lex-yacc`。

#### 项目中使用 Lark 的具体步骤
1. **安装依赖**
   ```bash
   pip install lark-parser
   ```
2. **编写文法** – 在 `calc_core/parser.py` 声明常量 `GRAMMAR`（见上方 EBNF）。
3. **创建解析器实例**
   ```python
   from lark import Lark, Transformer, v_args
   parser = Lark(GRAMMAR, parser="lalr", lexer="contextual", propagate_positions=True)
   ```
4. **实现 Transformer** – 继承 `lark.Transformer`，在每个动作方法里使用 `Decimal` 进行运算并返回结果。
5. **封装公共 API**
   ```python
   def calculate(expr: str) -> Decimal:
       try:
           tree = parser.parse(expr)
           return CalcTransformer().transform(tree)
       except Exception as exc:
           raise CalcError(str(exc))
   ```
6. **性能优化** – 启动时可将 `parser` 序列化到文件（`parser.save('calc_parser.pkl')`），下次加载 `Lark.load()` 以减少构建时间。
7. **测试** – 使用 pytest 读取 `tests/*.yaml`，对每条 `expr` 调用 `calculate` 并断言 `Decimal(str(expected))` 相等；对 `error` 用 `pytest.raises(CalcError)` 检验。
8. **集成 CLI / MCP Server** – CLI 直接调用 `calculate(expr)` 并打印；FastAPI 端点解析 JSON 后同样调用并返回结果或 HTTP 400。


## 5. 表达式处理流程
当系统（CLI 或 MCP Server）收到一个表达式字符串后，整体处理分为以下 8 步：
1. **输入获取**
   - CLI：从命令行参数获取完整表达式。
   - MCP Server：HTTP POST JSON 体中的 `expression` 字段。
2. **输入预处理**
   - 去除前后空白与不可见控制字符。
   - 限制最大长度（如 10 KB）防止 DoS。
3. **解析阶段**
   - 将表达式字符串传递给 `ExpressionParser.parse()`（基于 Lark）。
   - 若语法不符合文法，Lark 抛出 `UnexpectedToken` 等异常 → 转换为 `CalcError`。
4. **语义校验**
   - `Transformer` 中对函数名进行白名单校验。
   - 检查除零、过大指数等显式错误并抛出 `CalcError`。
5. **求值阶段**
   - `Transformer` 节点递归计算，所有数字均使用 `decimal.Decimal` 保证精度。
   - 复合函数调用（如 `log(x, b)`) 在受控环境中执行。
6. **结果归一化**
   - 将 `Decimal` 结果规范化（去掉多余尾随 0）。
   - 根据调用方需要返回 `int`（整数结果时）、`str` 或 JSON number。
7. **错误映射**
   - 任何 `CalcError` 在 CLI 转换为非零退出码并打印错误消息。
   - 在 MCP Server 中映射为 HTTP 400，响应 JSON `{ "error": "..." }`。
8. **日志与监控**
   - 记录解析耗时、表达式长度、是否命中缓存（若启用）。
   - 异常栈追踪仅打印到日志，避免泄露内部实现。

> 以上流程确保了安全、可维护且高精度的计算服务。

---

## 6. 文件/包组织 & 依赖
```
calculator-mcp/
├─ calc_core/
│  ├─ __init__.py        （暴露 calculate）
│  ├─ parser.py
│  ├─ evaluator.py
│  └─ errors.py
├─ calculator_cli.py      （可生成入口点 `calc`）
├─ mcp_server.py          （FastAPI 应用）
├─ requirements.txt       （lark-parser, fastapi, uvicorn, pydantic, click）
└─ README.md
```
在 `pyproject.toml` 中配置 console-script：
```toml
[project.scripts]
calc = "calculator_cli:main"
```

---

## 6. 调用流程示例
1. **通过 MCP Server**
   ```bash
   curl -X POST http://localhost:8000/evaluate \
        -H "Content-Type: application/json" \
        -d '{"expression":"2^10 + 5"}'
   ```
2. **通过 CLI**
   ```bash
   calc "tan(pi/4)"
   ```

---

## 7. 安全与测试
- 单元测试：`pytest`，覆盖 parser 与 evaluator
- Fuzz 测试：随机生成表达式确保稳健
- DoS 保护：限制表达式长度与递归深度
- Docker 部署：`uvicorn --workers N --host 0.0.0.0 --port 8000 mcp_server:app`

---

## 8. 里程碑 (MVP)
1. `calc_core.calculate` 支持基本四则运算
2. 打包 CLI (`calc`)
3. FastAPI `/evaluate` 接口
4. 单元测试 & README

---

> 若需进一步的代码实现或 CI/CD 脚本，请随时告知！
