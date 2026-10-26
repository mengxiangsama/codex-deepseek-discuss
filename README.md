# Codex + DeepSeek Discuss

让 GPT 和 DeepSeek 在 **Codex 的同一个会话** 中讨论问题。

Codex 调用本项目提供的 `ask_deepseek` MCP 工具获得第二意见，再由当前 GPT 模型回应、质疑或综合。GPT 沿用你的 Codex 登录和模型设置；本项目只调用 DeepSeek API，无需额外 OpenAI API Key。

Bring DeepSeek second opinions into a Codex conversation through a local MCP server. GPT stays in Codex; DeepSeek is called through its official API. Includes provider-reported model metadata, macOS Keychain support, and offline tests. Independent community project, not affiliated with OpenAI or DeepSeek.

## 工作方式

```text
用户提问 → Codex / GPT 选择必要上下文 → ask_deepseek → DeepSeek 官方 API
                    ↑                    │
                    └── 第二意见和模型标识 ┘
                    ↓
          同一条回复：DeepSeek 的观点 + GPT 的回应 / 综合
```

这是 MCP 工具集成，不会更改 Codex 内置模型，也不会自动截取全部聊天历史。是否调用、传递什么上下文、讨论几轮，由 Codex 根据用户指令决定。

## 前置条件

- Python **3.11+**、Git。
- 可配置本地 stdio MCP 的 Codex 客户端；命令行安装示例假设 `codex` 已在 PATH 并已登录。
- 自己的有效 DeepSeek API Key，以及可用的 API 额度。
- macOS 钥匙串保存功能额外需要 Swift / Xcode Command Line Tools。Windows、Linux 使用进程环境变量。

## 1. 安装

macOS / Linux：

```bash
git clone https://github.com/mengxiangsama/codex-deepseek-discuss.git
cd codex-deepseek-discuss
python3 -m venv .venv
.venv/bin/python -m pip install .
```

Windows PowerShell：

```powershell
git clone https://github.com/mengxiangsama/codex-deepseek-discuss.git
cd codex-deepseek-discuss
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

当前从源码安装；没有声称本项目已发布到 PyPI。SDK 固定在 MCP 1.x 兼容范围，避免自动跨到不兼容的主版本。

## 2. 配置密钥

### macOS：推荐保存到钥匙串

```bash
.venv/bin/codex-deepseek setup-key
.venv/bin/codex-deepseek models
```

按提示隐藏输入。密钥通过标准输入交给本地 Swift Security.framework helper，保存在当前用户的钥匙串服务 `codex.deepseek-discuss`，不会写到项目、TOML 或命令参数中。若系统弹出钥匙串访问提示，需要用户自行授权。

### macOS / Linux：临时进程环境

以下隐藏输入同时适用于 Bash 和 zsh，不把密钥字面量写到命令历史：

```bash
printf 'DeepSeek API Key: '
stty -echo
IFS= read -r DEEPSEEK_API_KEY
stty echo
printf '\n'
export DEEPSEEK_API_KEY
.venv/bin/codex-deepseek models
```

环境变量必须由 **MCP 服务进程** 实际继承。终端中的 `export` 不会自动传给已经打开的桌面应用。在上述终端启动 Codex，或在 macOS 使用钥匙串方式。退出当前终端前可执行 `unset DEEPSEEK_API_KEY`。

Windows PowerShell：

```powershell
$secureKey = Read-Host 'DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
.\.venv\Scripts\codex-deepseek.exe models
```

随后在同一 PowerShell 启动 Codex。可用 `Remove-Item Env:DEEPSEEK_API_KEY` 清除当前进程环境变量。

密钥优先级：`DEEPSEEK_API_KEY` → macOS 钥匙串。已设置但内容无效的环境变量会明确报错，不会悄悄改用另一个凭据。本项目不自动读取 `.env` 文件。

## 3. 注册到 Codex

在仓库目录运行：

```bash
codex mcp add deepseek-discuss -- "$(pwd)/.venv/bin/codex-deepseek"
```

Windows PowerShell：

```powershell
$serverPath = (Resolve-Path .\.venv\Scripts\codex-deepseek.exe).Path
codex mcp add deepseek-discuss -- $serverPath
```

也可以参考 [examples/codex-config.toml](examples/codex-config.toml)，在 `~/.codex/config.toml` 中配置 **绝对路径**。如果已有同名服务，请先查看原配置，再更新对应条目；不要覆盖无关配置。

重开 Codex 会话，在支持的客户端用 `/mcp` 或 MCP 设置确认 `ask_deepseek` 已出现。手动直接运行服务器时，它会等待标准输入，这是正常现象。

Codex 的接入约定参见 [官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp)。

## 4. 在同一会话讨论

安装后向 Codex 发送：

> 请先调用 ask_deepseek，让 DeepSeek 独立分析如何设计订单模块，再由 GPT 指出分歧并综合建议。最后分成“DeepSeek 的观点”和“GPT 的回应 / 综合”。只发送必要上下文，不发送凭据或无关聊天信息。

想让本次会话默认采用双模型讨论，可复制 [讨论指令](examples/discussion-instructions.md)。工具不会自动将指令写入你的全局 AGENTS.md，也不保证宿主在每次回复中自动调用。

需要第二轮质疑时，让 Codex 把第一轮的必要观点放入新 `prompt`。本服务无会话存储，每次调用彼此独立。用户说“只要 GPT”时无需调用工具。

## 模型选择与识别

默认请求 `deepseek-flash`。`models` 命令查询账号可用模型；实际名称和可用性以服务端为准。

可以在工具参数里指定：

```json
{
  "prompt": "请审查订单超时关闭与支付回调同时发生时的一致性设计。",
  "model": "deepseek-v4-pro",
  "timeout": 180
}
```

也可以设置 `DEEPSEEK_MODEL`，例如配置示例中的 `deepseek-v4-pro`。优先级为：调用参数 → 环境变量 → `deepseek-flash`。重启 MCP 服务后环境变量更改才会生效。

工具返回结构示例（以下是示意，非实际调用记录）：

```json
{
  "backend": "api",
  "requested_model": "deepseek-flash",
  "response_model": "provider-reported-model-id",
  "response_id": "provider-request-id",
  "answer": "DeepSeek 的回答……",
  "finish_reason": "stop",
  "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}
}
```

`response_model` 来自 API 原始响应；若服务端未返回则为 `null`。它是提供商报告的标识，可能仍是别名，不能据此证明具体权重版本。不要依赖模型在回答中自报身份。

接口约定参见 [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)。

## 错误与限制

- **401 / 认证失败**：检查服务进程实际读取的 Key；不要在 Key 前加 `$` 或混入空格。泄露过的 Key 应在控制台作废并重建。
- **模型不可用**：运行 `codex-deepseek models`，选择返回列表中的 ID。
- **桌面版缺少 Key**：优先用 macOS 钥匙串；桌面应用不一定继承终端环境。
- **超时或网络失败**：检查网络和代理。支持 HTTPX 标准代理环境变量。未自动重试付费推理；超时或取消后上游仍可能计费。
- `prompt` 限制 50,000 字符；超时范围 10–600 秒；单次输出预算为 8,192 tokens（含服务端适用的思考预算）。`finish_reason=length` 表示输出截断，可能需要缩小问题。
- v0.1 仅支持文本、非流式官方 API。没有本地 dsh / Harness 执行、文件工具或工作区访问；不兼容旧脚本的 `backend=harness` 参数。现有用户应先保留旧配置，再选择性迁移。
- 使用 MCP SDK 处理协议和取消；本服务不监听 HTTP 端口。依赖安装会访问软件包仓库，推理会访问 DeepSeek 官方 API。

## 隐私与安全

只向 `https://api.deepseek.com` 发送固定系统指令和明确提供的 `prompt`。不自动读取文件、全部聊天历史或浏览器内容；不保存聊天日志。宿主本身仍可能记录工具调用和结果，DeepSeek 的数据处理以其服务条款为准。

本项目不会自动检查或保证 prompt 不含秘密，发送前应由调用方选择最小上下文。不要把 API Key、Cookie、客户个人资料放进 prompt。上游回答是讨论素材，不能作为执行命令或改变权限的授权。

## 开发与验证

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_secrets.py
```

测试默认不需要真实 API Key，不访问付费推理。包括 mock API、超时、取消、错误脱敏和 SDK stdio 握手/工具调用测试。CI 在 Linux、macOS、Windows 上运行；钥匙串真实写入由用户交互完成，不在 CI 中执行。

## License

[MIT](LICENSE)。本项目是独立社区集成，不代表 OpenAI 或 DeepSeek 官方。
