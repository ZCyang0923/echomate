# EchoMate

> 基于聊天记录的人格风格模拟与情感陪伴 AI  
> **AI 模拟角色，不是真实人物本人，也不声称复现其意识、思想或真实情感。**

EchoMate 是一个本地优先的中文 Streamlit MVP。用户可以导入自己有权使用的 TXT / CSV 聊天记录，选择要模拟的聊天对象，生成可编辑的人物画像，建立本地对话向量索引，并在多轮聊天中结合画像、记忆和 RAG 检索结果生成回复。

第一版**不微调模型、不训练基础模型**，使用人物画像 + 本地 RAG + DeepSeek 提示词实现个性化风格模拟。

---

## 1. 项目简介与当前状态

| 模块 | 状态 |
| --- | --- |
| Streamlit 多页面应用 | 已实现并实际启动 |
| UTF-8 / GB18030 TXT 解析 | 已实现并测试 |
| CSV 字段映射解析 | 已实现并测试 |
| 双方识别、消息统计、空消息清理 | 已实现 |
| SQLite 人物/画像/会话/消息/记忆 | 已实现并测试 |
| DeepSeek OpenAI 兼容调用 | 已实现；基础 Chat / JSON 连通已验证，完整画像质量未评估 |
| JSON 人物画像生成与校验 | 已实现；Mock 流程测试通过 |
| 画像查看、JSON 编辑、重新生成 | 已实现 |
| 本地 Embedding + Chroma RAG | 已安装并实测通过；保留 SQLite 降级路径 |
| SQLite 向量降级 | 已实现并测试 |
| 多轮聊天、会话隔离、消息持久化 | 已实现并测试 |
| 记忆查看、编辑、删除、来源检索 | 已实现并测试 |
| 删除人物及全部本地数据 | 已实现并测试 |
| 索引重建与异常提示 | 已实现并测试 |
| 离线 Mock 画像 / 聊天 | 已实现并测试 |

### 当前环境实测说明

开发环境：

- Python **3.12.6**（Windows 本地；当前唯一完成依赖安装、测试和启动验证的版本）
- Streamlit 1.66.1
- pandas 3.0.6
- numpy 2.5.4
- OpenAI Python SDK 3.39.0
- **chromadb 1.5.9**（已实测）
- **sentence-transformers 6.2.0**（已实测）
- **torch 2.14.1**
- 不在 README 或源码中记录 API Key；Key 只从本机 `.env` 读取

因此本次实际运行与测试覆盖的是：

- 真实本地 semantic embedding：`paraphrase-multilingual-MiniLM-L12-v2`
- 真实本地 ChromaDB 持久化、索引、检索与删除
- 模型缓存目录：`data/hf_cache`（约 458MB，已下载）
- DeepSeek 基础 Chat 与 JSON Output 的最小连通性验证
- OpenAI 兼容客户端的配置/错误路径与 Fake LLM 单元测试
- Mock 画像 / Mock 聊天

**未完成真实联调的部分：**

1. 未用真实 Key 生成完整人物画像并评估画像质量；
2. 未在真实大模型返回下评估长对话风格一致性与越界行为；
3. 未使用 DeepSeek 真实调用做端到端成本/延迟测试。

代码已按 DeepSeek 官方 OpenAI 兼容接口与 JSON Output 文档实现，并在没有 API Key 时提供清晰的配置提示与完整可运行的 Mock 模式。

---

## 2. 功能说明

### 首页

- 产品定位、使用流程与 AI 边界提示；
- 人物/消息/画像/记忆统计；
- 当前 LLM、Embedding、向量后端状态；
- 隐私与 API 数据边界说明。

### 人物管理

- 创建、查看、编辑、删除人物；
- 每个人物拥有稳定 `person_id`；
- 删除人物时先删除向量索引，再级联删除 SQLite 中画像、导入消息、会话、记忆；
- 删除操作要求勾选确认并输入人物昵称。

### 聊天记录导入

- 上传 TXT / CSV 或使用内置虚构示例；
- 使用授权确认必须先勾选；
- 支持常见中文编码自动识别；
- CSV 可自定义发送者、内容、可选时间字段；
- TXT 提供自动识别、常见预设、自定义正则；
- 显示原始预览、解析统计、双方消息数、失败/未识别行、续行数量；
- 未识别内容不会被静默丢弃，而是作为续行或计入异常统计；
- 确认导入后写入 SQLite 并建立人物索引。

### 人物画像

- 通过 DeepSeek JSON Output 生成结构化画像；
- 长聊天按消息数/字符数分批，限制最大批次数；
- 分批结果合并；
- 画像字段包括语言风格、口头禅、标点/Emoji 习惯、情绪表达、互动习惯、兴趣、共同经历、事实、不确定信息；
- 要求事实/经历附带原文证据；
- 禁止推断心理疾病、隐私属性、真实意图等；
- 支持查看、JSON 编辑、校验保存、重新生成；
- 保存后自动同步“记忆库”；
- 聊天时使用最新数据库中的画像和记忆。

### RAG

- 将连续消息切成带重叠的对话窗口；
- 保存发送者、时间、消息 ID 等元数据；
- 使用本地 sentence-transformers 多语言模型（已实测）；
- 使用 ChromaDB 持久化向量（已实测）；
- 依赖缺失时仍可降级为确定性哈希向量 + SQLite 向量表；
- 检索时强制按 `person_id` 过滤；
- 离线哈希降级模式额外做轻量词面重合重排，降低跑题；
- 控制 top-k、上下文长度；
- 没有相关资料时提示模型承认不确定。

### 专属聊天

- 会话按人物隔离、按会话保存；
- 支持新建会话、切换会话、清空当前会话；
- 每轮保存用户与 AI 消息；
- 回复上下文包含：
  - 当前人物画像（风格字段）；
  - 当前记忆库中的事实/经历；
  - 当前问题检索出的历史片段；
  - 最近若干轮当前会话；
  - 当前用户输入；
- 不把 AI 回复自动写回记忆或历史聊天；
- 在 UI 和系统提示中都明确“AI 模拟角色”；
- 展示本轮参考的历史原文片段。

### 记忆管理

- 查看画像摘要、共同经历、事实与证据；
- 可将画像中的经历/事实重新同步为记忆；
- 可编辑或删除记忆；
- 可查看某条记忆对应的历史原文片段；
- 可重建当前人物索引；
- 可清空当前人物聊天与画像数据但保留人物；
- 可永久删除人物及全部本地数据。

---

## 3. 技术栈

- Python 3.12.6（当前唯一已验证版本；见下节）
- Streamlit（单体应用；没有独立的前端 Node 服务或后端 API 服务）
- pandas
- OpenAI Python SDK（DeepSeek 兼容接口）
- ChromaDB（主路径）
- sentence-transformers（本地语义 Embedding 主路径）
- SQLite（Python 标准库）
- python-dotenv
- pytest

### 3.1 环境要求与 Python 版本兼容性

**推荐使用 Python 3.12.6（Windows 64 位）。** 本项目没有 `pyproject.toml`、`setup.py`、`Pipfile`、`environment.yml`、`Dockerfile`、`runtime.txt`、`.python-version`、CI 工作流或云端部署配置；当前验证发生在本地 Windows 11 + PowerShell 环境。

| Python 版本 | 状态 | 依据与限制 |
| --- | --- | --- |
| 3.12.6（Windows） | **已验证支持** | 本项目 `.venv` 实际安装、41 项测试通过、Streamlit 启动成功；ChromaDB 与 sentence-transformers 主路径已实测 |
| 3.12.x 其他补丁版本 | 理论兼容但未验证 | 与已验证版本同一 minor；未在本机安装测试 |
| 3.11.x | 理论兼容但未验证 | 项目代码和部分依赖允许 3.11，但本机没有 3.11 解释器；当前完整依赖集合中的 numpy 2.5.4 要求 Python >=3.12，干净环境会解析出不同依赖版本，未完成测试 |
| 3.10.x / 3.9.x | **不支持** | 当前 Streamlit 1.66.1 与 pandas 3.0.6 的 `Requires-Python` 均为 `>=3.11`；3.9 系统环境还缺少 Chroma/ST，不能作为本项目的验证环境 |
| Linux / 云端 | 未验证 | 仓库没有容器、CI 或云端配置；不要在文档中把 Windows 路径当作通用部署路径 |

补充说明：

- 当前已安装版本的 `Requires-Python` 证据：Streamlit 1.66.1 `>=3.11`、pandas 3.0.6 `>=3.11`、numpy 2.5.4 `>=3.12`；不同 Python 版本会因依赖解析得到不同组合。
- 当前 `requirements.txt` 使用版本范围而不是完整锁文件；不同 Python 版本可能解析出不同的 pandas、numpy、Streamlit 版本。
- 以上“已验证”仅指本机 Python 3.12.6 的实际测试结果，不表示其他版本获得官方支持。
- 启动前先确认解释器：

```powershell
python --version
# 应显示 Python 3.12.x；如果系统默认 python 是 3.9，请使用 py -3.12 创建/调用 .venv
```


---

## 4. 项目结构

```text
echomate/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml
├── pages/
│   ├── 1_人物管理.py
│   ├── 2_导入聊天记录.py
│   ├── 3_人物画像.py
│   ├── 4_专属聊天.py
│   └── 5_记忆管理.py
├── core/
│   ├── config.py
│   ├── errors.py
│   ├── chat_parser.py
│   ├── llm_client.py
│   ├── profile_builder.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   ├── rag_service.py
│   ├── import_service.py
│   ├── chat_service.py
│   └── memory_service.py
├── database/
│   ├── db.py
│   └── repositories.py
├── ui/
│   ├── common.py
│   └── runtime.py
├── tools/
│   └── convert_wechat_export.py
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_profile.py
│   ├── test_rag.py
│   ├── test_memory.py
│   ├── test_chat.py
│   ├── test_llm.py
│   └── test_wechat_converter.py
├── sample_data/
│   ├── demo_chat.txt
│   └── demo_chat.csv
└── data/
    └── .gitkeep
```

---

## 5. 安装与配置

### 5.1 安装依赖

建议使用 Python 3.12.6 的虚拟环境。**不要直接使用系统默认的 `python`**，本机默认解释器可能是 Python 3.9：

```powershell
cd F:\deepseek_workarea\echomate
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 必须确认显示 Python 3.12.x
python --version

python -m pip install -r requirements.txt
```

如果 PowerShell 不允许执行激活脚本，可以只对当前进程放行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

也可以不激活，始终使用带路径的解释器：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

依赖中包含 ChromaDB 与 sentence-transformers。后者会自动安装 PyTorch，体积较大；如果只是离线演示，即使不安装它们，EchoMate 也会：

- Embedding 自动降级为 `hash`；
- 向量存储自动降级为 SQLite 表；
- 在 UI 和 README 中明确标识降级状态。

安装完成后检查：

```powershell
python -m pip check
python -m pytest -q
```

### pip 安装卡住时

本项目在当前 Windows 环境中遇到 pip resolver 长时间 CPU 占用、没有安装进度的问题，已改用 `uv` 完成依赖安装。后续重装可优先使用：

```powershell
# 只安装一次 uv（当前 .venv 已安装）
python -m pip install uv

# 使用独立缓存目录，避免系统目录权限问题
$env:UV_CACHE_DIR = "F:\deepseek_workarea\.uv-cache"
.venv\Scripts\uv.exe pip install --python .venv\Scripts\python.exe -r requirements.txt --index-url https://pypi.org/simple
```

如果仍然使用 pip，建议只安装最小依赖，并避免同时运行多个安装进程。

### 5.2 配置 DeepSeek

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
DEEPSEEK_API_KEY=你的_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

模型名称只从环境变量读取，不散落在业务代码里。默认示例遵循 DeepSeek 当前官方文档中的 `deepseek-flash`；如官方调整模型名，请以官方文档为准：

- <https://api-docs.deepseek.com/zh-cn/>
- <https://api-docs.deepseek.com/zh-cn/guides/json_mode/>

**没有 Key 也可以启动应用**：侧边栏会显示配置说明，并自动启用离线演示模式。

### 5.3 可选配置

详见 `.env.example`：

- `EMBEDDING_MODEL`
- `EMBEDDING_BACKEND=auto|hash|sentence_transformers`
- `VECTOR_BACKEND=auto|chroma|sqlite`
- `HF_HOME`（默认 `data/hf_cache`）
- `ECHOMATE_TEMP_DIR`（默认 `data/tmp`）
- 请求超时/重试
- 画像批次大小、最大批次数、最大 token
- 聊天历史条数
- RAG top-k、上下文长度、最低相关度
- 分块大小与重叠
- 上传大小上限

修改 `.env` 后需要重启 Streamlit 进程。

---

## 6. 启动

使用项目虚拟环境启动，避免系统里的旧 `streamlit` 抢到 Python 3.9：

```powershell
cd F:\deepseek_workarea\echomate
.\.venv\Scripts\python.exe -m streamlit run app.py
```

或先激活虚拟环境再启动：

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

本地地址通常是：

```text
http://localhost:8501
```

不要直接执行全局的 `streamlit run app.py`；本机全局 `streamlit` 可能绑定到 Python 3.9。若启动时提示 `ModuleNotFoundError`，先执行 `python --version` 并确认是 3.12.x，再检查是否使用了 `.venv` 中的解释器。

---

## 7. 第一次使用：导入示例并聊天

内置数据为虚构聊天（小满 / 阿远），不含任何真实私人信息。

1. 启动应用，点击侧边栏「导入聊天记录」。
2. 勾选“我确认自己有权使用这份聊天记录…”。
3. 数据来源选择「内置示例 TXT」或「内置示例 CSV」。
4. 点击「解析并预览」；检查有效消息数（示例为 45 条）与发送者统计（2 人）。
5. 在“要模拟的聊天对象”中选择 `小满`。
6. 选择“新建人物”，填写昵称，例如 `小满`，点击「确认导入并建立索引」。
7. 进入「人物画像」，点击「生成人物画像」。在未配置 API Key 时会使用离线 Mock 画像；配置后取消侧边栏的“离线演示模式”即可调用 DeepSeek。
8. 进入「专属聊天」，在输入框发送消息，例如：
   - `今天有点累，想聊聊`
   - `你还记得上次一起看的电影吗`
9. 可以展开 AI 回复下的「本次参考的历史片段」，查看本轮实际检索到的原文。
10. 在「记忆管理」中检查自动提取的共同经历/事实，并测试编辑、删除、重建索引或清空数据。

> 若使用自定义 TXT，请确保格式与所选规则一致。最稳妥的 TXT 格式是：
> `[2024-05-01 20:15] 小满: 晚上好`
>
> 无法识别时，使用 CSV 并手动选择发送者和内容字段。

---

## 8. 微信聊天记录导入教程

> **EchoMate 不读取微信本地数据库，也不负责解密微信数据库。**  
> 本节使用的外部工具负责从已登录的 Windows 微信导出聊天记录；EchoMate 只接收导出的 TXT/CSV。两个项目不是同一个项目，EchoMate 也不会在运行时调用该工具。

### 8.1 外部导出工具

参考版本：**wechat-chat-export v1.4.0**

- Release 页面：<https://github.com/zhuzhangxue/wechat-chat-export/releases/tag/v1.4.0>
- 项目 README：<https://github.com/zhuzhangxue/wechat-chat-export>

截至该版本，Release 的 Assets 中提供：

| 文件 | 用途 |
| --- | --- |
| `WeChat-Chat-Export-for-LLM.exe` | Windows 单文件可执行程序，不需要额外安装 Python |
| `WeChat-Chat-Export-for-LLM-Windows.zip` | Windows 打包版本 |
| `LICENSE`、`THIRD_PARTY_NOTICES.md` | 许可证与第三方声明 |

以下流程依据该版本 Release 说明和项目 README 整理；工具界面可能随版本变化，请以实际 Release 为准。本文没有在这台机器上实际运行外部导出工具。

外部工具 README 说明其面向 Windows 微信 4.1.12+，需要先登录微信并保持微信在后台运行。它会在本机读取微信数据，并尽量导出文字、引用、系统消息和仍有缓存的媒体。媒体是否完整取决于本机缓存，不能保证恢复已清理的图片或视频。

### 8.2 第一步：准备并导出

1. 在 Windows 上登录微信，确认要导出的是**单个好友或单个群聊**，不要先导出全部聊天。
2. 打开上面的 v1.4.0 Release 页面，滚动到底部的 **Assets**。
3. 优先下载 `WeChat-Chat-Export-for-LLM.exe`；如果希望使用压缩包，再选择 `WeChat-Chat-Export-for-LLM-Windows.zip`。
4. 下载前核对发布者、版本号 `v1.4.0` 和文件名。该版本没有商业代码签名，Windows SmartScreen 可能提示未知发布者；请先核对来源和文件，不要为了运行工具而关闭 Defender 或添加安全软件排除项。
5. 运行工具。按工具 README 的说明：
   - 输入好友的准确备注、昵称或群名；
   - 选择是否导出图片、文件、语音、视频；
   - 如自动定位不到数据目录，手动指定微信数据目录；
   - 点击「开始导出」。
6. 如果工具要求手动指定数据目录，以微信「设置 → 文件管理」显示的数据目录为准。通常可以选择数据根目录或 `xwechat_files` 目录；**不要选择 `Backup\...\files` 这类备份子目录**。
7. 如果目录识别失败，先回到微信确认实际数据目录，再看外部工具自己的故障排查说明；不要在不确定的情况下选择其他微信账号或旧的备份目录。

导出完成后，外部工具通常会生成：

```text
exports/
└─ <聊天名称>/
   ├─ chat_full_for_llm.txt
   ├─ chat_full_for_llm.md
   ├─ chat_full_parsed.json
   └─ media/
```

EchoMate 需要的是其中的 `chat_full_for_llm.txt`。不要上传 `.md`、`.json` 或 `media/` 目录；它们不是本项目当前要解析的聊天文本格式。

### 8.3 第二步：确认导出文件

外部工具生成的 TXT 通常类似：

```text
========== 2025-08-30 ==========

2025-08-30 13:18:07 | 小满：瓦
2025-08-30 13:18:42 | 我：打工
2025-08-30 13:18:49 | 小满：[动画表情]
```

这个格式带有 `YYYY-MM-DD HH:mm:ss | 发送者：正文` 和日期分隔标题。EchoMate 的自动 TXT 解析规则不能可靠识别这个竖线格式：自动识别可能把 `| 小满` 当成发送者，导致发送者和时间显示异常。

因此，**外部工具导出的原始 TXT 不能直接上传**。请先使用仓库内的本地转换工具转成 EchoMate 支持的方括号格式。

### 8.4 第三步：转换为 EchoMate 格式

仓库提供了独立的标准库脚本：

```text
tools/convert_wechat_export.py
```

它只读取外部 TXT、写出新文件，不访问微信数据库，不联网，不修改输入文件。转换命令：

```powershell
cd F:\deepseek_workarea\echomate

.\.venv\Scripts\python.exe tools\convert_wechat_export.py `
  --input "D:\微信导出\小满\chat_full_for_llm.txt" `
  --output-dir "F:\deepseek_workarea\converted_for_website"
```

请把 `--input` 换成你自己的实际路径。输出目录不存在时会创建 `converted_for_website`；如果该目录已经存在，脚本会创建一个带时间戳的新目录，不会覆盖已有结果。

转换后得到：

```text
converted_for_website/
├── chat_for_website.txt
└── conversion_report.txt
```

关键行为：

- 删除外部工具的固定表头、`========== 日期 ==========` 标题和空行；
- 保留原始消息顺序；
- 保留 `我`、好友备注和群聊发送者名称，不猜测真实姓名；
- `[图片]`、`[动画表情]`、`[语音]`、`[视频]`、`[文件]` 等占位符原样保留；
- 引用行和转发卡片中的无时间戳内容会并入上一条顶层消息，用 ` ⏎ ` 表示原始换行，避免把其他人的名字拆成新的顶层消息；
- 不删除重复消息，按原始顺序保留；
- 不做时区转换，保留原始日期时间字符串；
- 转换前后计算原文件 SHA-256；如果数量或解析结果异常，脚本会停止并报错，不会静默丢弃消息。

转换后的目标格式是：

```text
[2025-08-30 13:18] 小满: 瓦
[2025-08-30 13:18] 我: 打工
[2025-08-30 13:18] 小满: [动画表情]
```

EchoMate 的「方括号时间 + 发送者」TXT 规则支持这种格式；仓库已用一个 15,354 条消息的转换结果做过解析验证。

### 8.5 第四步：导入 EchoMate

1. 按 [第 6 节](#6-启动) 启动应用。
2. 点击侧边栏「导入聊天记录」。
3. 勾选“我确认自己有权使用这份聊天记录…”。
4. 在“数据来源”选择「上传文件」。
5. 上传 `chat_for_website.txt`。当前文件选择器只接受 `.txt` 和 `.csv`。
6. 选择 TXT 解析规则：
   - 通常使用「自动识别」；
   - 如果自动识别失败，选择「方括号时间 + 发送者」；
   - 不要对上面的方括号格式使用「仅发送者冒号」规则。
7. 点击「解析并预览」，确认：
   - 有效消息数；
   - 发送者列表；
   - 解析失败/未识别行；
   - 续行合并数；
   - 前 20 条预览。
8. 在“要模拟的聊天对象”中选择目标好友或群聊发送者。
9. 选择「新建人物」，或选择「追加到已有」并确认目标发送者与已有档案一致。
10. 点击「确认导入并建立索引」。成功后会显示导入消息数、目标人物消息数和本地索引分块/向量数。

当前导入页的行为：

- 单文件默认上限 **10 MB**，可通过 `.env` 的 `MAX_UPLOAD_MB` 调整（代码允许 1–100 MB）；
- 支持 TXT、CSV；不直接读取微信数据库、Markdown、JSON 或媒体目录；
- 导入成功后写入本地 SQLite，并建立当前人物的向量索引；
- 同一人物重复导入同一文件（相同 SHA-256）会被拒绝；
- 追加导入要求目标发送者与已有档案一致，不会覆盖已有消息；
- 删除人物会清理其消息、画像、会话、记忆和当前向量索引；清空内容会保留人物档案但删除聊天内容。

---

## 9. 文件格式要求与示例

### 9.1 TXT（推荐）

EchoMate 内置的 TXT 规则：

| 规则 | 示例 | 说明 |
| --- | --- | --- |
| 方括号时间 + 发送者 | `[2025-08-30 13:18] 小满: 瓦` | **推荐**；网站格式和转换脚本输出使用此格式 |
| 日期时间 + 发送者 | `2025-08-30 13:18:07 小满: 瓦` | 不支持时间与发送者之间的 `|` |
| 仅发送者冒号 | `小满: 瓦` | 没有时间戳；不推荐用于正式导入 |
| 自定义正则 | 由用户提供 | 必须包含 `sender` 和 `content` 命名分组 |

TXT 要求：

- 日期使用 `YYYY-MM-DD`，时间使用 `HH:mm`（方括号规则）；
- 建议使用 UTF-8，不带 BOM；解析器也能读取带 BOM 的 UTF-8 和 GB18030；
- 每条消息一行；
- 发送者与正文之间使用英文冒号加一个空格；
- 发送者可以是 `我`、好友备注名、群聊昵称或 `系统消息`；
- 正文中的英文冒号、竖线、问号和 Emoji 不会被当作字段分隔符；
- 媒体占位符只是文本，EchoMate 不会自动打开或转写媒体。

### 9.2 CSV

CSV 通过字段映射导入：

- 必须选择发送者字段和消息内容字段；
- 时间字段可选；
- 建议列名包含 `sender`/`发送者` 与 `content`/`消息内容`，便于自动猜测；
- 适合外部工具已经整理成结构化字段的场景。

### 9.3 导入限制

- 不直接支持微信/QQ 专有数据库、`Backup` 文件、`.tar.enc`、Markdown 和 JSON；
- 不自动解密微信数据库；
- 不把媒体文件名当作消息正文；
- 不保证导出的图片、语音、视频完整；
- 同一分钟内的多条消息按原始文件顺序保留；转换后去掉秒，不要用输出时间重新排序。

---

## 10. 常见问题

### Q1：外部工具无法识别微信数据目录

先在微信「设置 → 文件管理」确认实际数据目录，再在工具中手动选择数据根目录或 `xwechat_files`。不要选择 `Backup\...\files` 子目录；如果仍有问题，查看外部工具 README 的目录探测说明。

### Q2：应该上传哪一个导出文件？

选择外部工具生成的：

```text
<聊天名称>/chat_full_for_llm.txt
```

不要上传 `.md`、`.json` 或 `media/`。EchoMate 当前只解析 TXT/CSV。

### Q3：直接上传外部 TXT 后发送者显示成 `| 小满`

这是原始格式与 EchoMate 规则不一致。先运行：

```powershell
.\.venv\Scripts\python.exe tools\convert_wechat_export.py --input "...\chat_full_for_llm.txt" --output-dir "...\converted_for_website"
```

再上传生成的 `chat_for_website.txt`。

### Q4：网站提示格式不正确

依次检查：

1. 是否上传了 `.txt` 或 `.csv`；
2. TXT 是否采用方括号格式；
3. 文件是否超过 10 MB；
4. 编码是否为 UTF-8 或 GB18030；
5. 解析统计中的“解析失败/未识别”是否异常；
6. 是否误把 Markdown/JSON 当成 TXT。

### Q5：中文乱码

优先将文件另存为 UTF-8（无 BOM 或有 BOM 均可），再重新解析。不要用 ANSI 编码保存中文后直接上传。

### Q6：部分消息没有解析

查看解析预览中的失败/未识别行和续行统计。外部 TXT 中的日期标题、引用和转发卡片需要先经过转换脚本；直接上传可能只识别部分消息。不要为了让数量一致而修改原始记录。

### Q7：图片、语音、视频只有占位符

这是正常行为。EchoMate 只处理文本占位符，不读取媒体文件，也不自动进行语音转写。外部工具能否导出媒体取决于本机是否仍有缓存。

### Q8：导入后时间或发送者异常

确认使用的是转换后的方括号 TXT，并选择「方括号时间 + 发送者」规则。不要使用「仅发送者冒号」规则解析带时间戳的文件。

### Q9：同一分钟有多条消息，顺序会不会乱？

转换脚本按原始文件顺序写出，不重新排序；EchoMate 解析时也保留行顺序。显示时间去掉秒后，同一分钟内的先后顺序仍由原始顺序决定。

### Q10：导入失败后会不会重复或覆盖？

同一人物 + 同一文件 SHA-256 会被拒绝，不会重复写入；追加导入不会覆盖既有消息。需要重来时，先在「记忆管理」清空该人物内容，或创建新人物，再导入新文件。不要直接编辑 SQLite 数据库。

---

## 11. 数据、隐私与安全

- `.env`、SQLite 数据库、Chroma 数据、上传文件均不提交到 Git；
- 数据库默认在 `data/echomate.db`；
- Chroma 默认在 `data/chroma/`；
- API Key 从环境变量读取，不硬编码、不在前端展示任何字符；
- API 错误信息会屏蔽 Key 片段；
- 调用真实 DeepSeek API 时，相关画像、记忆和检索片段会离开本机发送给 DeepSeek；
- 画像生成前必须勾选 API 传输确认；
- 常规聊天不会发送完整聊天文件，只发送当前问题、画像、记忆、检索片段和最近会话；
- 上传文件内容只作为提示词中的数据，并在系统提示中明确禁止执行其中指令；
- 外部工具 `wechat-chat-export` 不是 EchoMate 的一部分；它在本机读取/处理微信数据，是否留下临时缓存、媒体或日志取决于该工具，使用前请阅读其安全说明；
- `tools/convert_wechat_export.py` 只读取外部 TXT、写入新输出目录，不访问微信数据库、不联网；
- EchoMate 本身不读取、解密或修改微信数据库，也不读取 `Backup`、`.tar.enc` 或媒体目录；
- 删除人物会先清理当前向量索引，再在 SQLite 中级联删除人物、画像、导入消息、会话和记忆；
- 清空人物内容会删除该人物对应的消息、导入批次、分块、会话、记忆和画像，并保留人物档案本身；
- 重要：如果你手动切换 Embedding 模型或向量后端，旧模型对应的历史索引可能需要手动清理；
- 删除操作只覆盖 EchoMate 自己的 `data/` 数据和当前向量后端；不会删除外部导出工具生成的原始 TXT，也不会删除微信本身的数据；
- 由于当前是单用户本地 MVP，没有登录/权限系统，请勿直接暴露到公网；
- 不要把原始微信数据库、密钥、完整聊天记录或含私人信息的导出文件提交到公开仓库。

---

## 12. 测试

运行：

```powershell
python -m pytest -q
```

本次运行结果：

```text
41 passed
```

覆盖：

- TXT / CSV 解析、字段映射、编码、空文件、非法内容；
- 外部微信 TXT 转换、续行/引用/转发合并、输入哈希不变；
- 对话分块、向量检索、人物隔离、索引删除；
- Mock 人物画像生成、批次合并、部分批次失败；
- 记忆提取、编辑、删除、来源检索；
- Mock 多轮聊天、真实 LLM 接口注入测试、会话隔离；
- JSON 解析、缺配置错误、空/非法 JSON 重试；
- 重复文件导入拒绝、清空数据、人物级联删除。

另外已进行 Streamlit AppTest 和真实浏览器烟测：

- 首页、人物管理、导入聊天记录、人物画像、专属聊天、记忆管理均无运行时异常；
- 真实浏览器中通过文件选择器上传 TXT 并解析成功；
- 自定义侧边栏与多页面导航正常；
- 内置 TXT、CSV 示例可解析；
- 转换后的 15,354 条真实样本可被 `parse_txt` 以「方括号时间 + 发送者」规则完整解析；
- Mock 画像可生成并同步记忆；
- 聊天消息可在页面重跑后保留；
- 新会话与清空会话功能正常。

未覆盖：

- 真实 DeepSeek 完整画像生成与质量评估；
- 真实 DeepSeek 输出质量、成本与延迟评估；
- 大规模消息量下的 ChromaDB 性能压测；
- Linux / 云端部署测试。

已额外实测：

- ChromaDB 1.5.9 持久化、索引、查询、按人物删除；
- sentence-transformers 6.2.0 本地模型加载与 384 维向量；
- 45 条示例消息切分为 8 个对话片段并成功检索；
- 转换脚本在真实导出文件上生成 15,354 条消息、原始 SHA-256 不变；
- 删除人物后 Chroma 向量数量归零。

> 本仓库当前没有 GitHub Actions、Dockerfile、`runtime.txt` 或 Streamlit Community Cloud 配置，因此未声称已完成云端部署验证。

---

## 13. 已实现 / 未实现 / 已知限制

### 已实现

- 完整六页（首页 + 五业务页）Streamlit 应用；
- 文本/CSV 解析与统计；
- 外部微信 TXT 转换工具（`tools/convert_wechat_export.py`）；
- 人物、画像、会话、消息、记忆 SQLite 持久化；
- DeepSeek JSON 画像生成与重试；
- 本地 sentence-transformers + ChromaDB 向量索引与 RAG；
- 画像编辑、记忆编辑、来源查看；
- 多轮聊天、会话隔离、删除流程；
- 离线 Mock 模式；
- Chroma / sentence-transformers 自动降级；
- 隐私提示与 API Key 保护；
- 自动化测试。

### 未实现 / 当前限制

- 未完成真实 DeepSeek 完整画像生成、风格质量与安全边界评估；
- 没有用户登录、多租户或公网部署安全加固；
- 没有流式输出；
- 没有自动从聊天中增量提取“记忆”的独立 LLM 流程；记忆当前由画像同步或人工编辑；
- TXT 只支持常见规则/自定义正则；外部工具的原始竖线格式需先运行转换脚本，不直接支持微信/QQ 专有数据库；
- 外部导出工具不是本项目的一部分，其媒体恢复、微信版本兼容和数据访问能力由该工具决定；
- 哈希降级检索只适合演示，语义检索质量明显弱于 sentence-transformers；
- SQLite 向量降级不适合大规模消息量；
- 画像质量高度依赖聊天数量、模型与提示词，仍可能出现错误概括；
- 未做敏感信息自动脱敏（手机号、地址等），导入真实记录前应自行清理；
- 未做 token 精确计数，使用字符/消息数限制成本；
- 切换 Embedding 模型/向量后端后需要重建索引，旧后端数据可能需要手动清理；
- 单进程 SQLite，不适合高并发；
- 没有 Dockerfile、CI 或云端部署配置，Windows 本地之外的环境未验证。

### 下一阶段值得实现

1. 完成真实 DeepSeek 画像生成与风格/安全质量评估，加入成本预算与用量统计；
2. 流式回复；
3. 增量索引和更好的对话窗口切分；
4. 记忆抽取改为独立的、可审核的 LLM 流程；
5. 敏感信息检测与一键脱敏；
6. Chroma 后端切换时的旧集合清理机制；
7. 用户认证与加密存储；
8. 更细粒度的数据导出/删除审计；
9. 对话安全评估集与越界回复测试；
10. 支持更多聊天导出格式。

---

## 14. 免责声明

EchoMate 仅用于个人聊天风格探索和情感陪伴。它不是逝者复活、意识上传或真实人物复制工具。请不要使用它冒充他人、欺骗、骚扰或未经授权处理他人隐私数据。聊天记录的合法使用权由使用者自行确认。

---

## 15. 主要文件索引

- `core/chat_parser.py`：TXT/CSV 解析与统计
- `core/profile_builder.py`：画像 JSON 结构、分批生成与 Mock
- `core/embedding_service.py`：sentence-transformers / 哈希降级
- `core/vector_store.py`：Chroma / SQLite 向量后端
- `core/rag_service.py`：切块、索引、检索
- `core/chat_service.py`：上下文装配与多轮聊天
- `core/memory_service.py`：画像到记忆、来源检索
- `database/db.py`、`database/repositories.py`：SQLite 数据层
- `ui/common.py`、`ui/runtime.py`：共享 UI 与运行时服务
- `tools/convert_wechat_export.py`：外部微信 TXT 到方括号 TXT 的本地转换工具
- `tests/test_wechat_converter.py`：转换工具的回归测试
