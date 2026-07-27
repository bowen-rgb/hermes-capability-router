# Hermes 能力路由插件

这是一个 Hermes **通用插件**，不是 MCP Server。它不会修改 Hermes 核心，而是通过
公开的 Plugin Hook 在工具选择前提供能力路由建议。

**语言：** [English](README.md) | [简体中文](README.zh-CN.md) | [Français](README.fr.md)

许可证：[MIT](LICENSE)。

## 它解决什么问题？

插件管理的是“能力（Capability）”，不是把某一个工具当成能力本身。

```text
能力：图片文字提取（OCR）
实现：PaddleOCR Python 包 | CLI | API | MCP 工具 | 本地视觉模型
```

能力是稳定的；具体实现可以随安装环境、成本、速度与可用性变化。

## 两条生命周期

### 1. 运行时路由：三层 Router

每次用户请求会经过：

```text
用户请求
  -> Hermes Plugin Hook
  -> 第一层 Scene Router（大场景：vision / document / coding）
  -> 第二层 Semantic Router（具体意图：OCR / 图片理解）
  -> 第三层 Capability Resolver（查能力并对实现排序）
  -> 向 Hermes 注入路由建议
  -> Hermes 执行；可选策略守卫检查工具调用
```

```text
运行时路由
├── Scene Router
├── Semantic Router
└── Capability Resolver
    ├── Capability Registry
    ├── Capability Index / 本地向量检索
    └── Implementation Ranking
        └── Python 包 | CLI | API | MCP | 本地模型 | Plugin/Skill
```

示例：`把这张截图里的文字提取出来`

```text
vision -> text_extraction -> vision.image_text_extraction
```

### 2. 能力发现与 Annotation

这是一条后台生命周期。它只建立待审核草稿，**不会**把猜测的能力直接启用。

```text
已安装或外部来源
  -> Discovery Engine
  -> Annotation Engine
  -> 人工审核（pending review）
  -> Capability Registry
  -> Capability Index
```

```text
Discovery & Annotation
├── Discovery Engine
│   ├── Hermes Plugin / Python 包 / CLI 工具
│   ├── GitHub 仓库与 README
│   ├── MCP 工具
│   └── 本地模型
└── Annotation Engine
    ├── 提取元数据
    ├── 场景、意图与能力分类
    ├── 多语言标签生成
    ├── 优势和限制分析
    └── 持久化待审核队列
```

在 Hermes 中使用 `/capability-review` 查看草稿；确认来源和本机可用性后，使用
`/capability-review approve <编号>` 批准。

## 中文、法语和英文适配

路由器对简体中文、繁體中文、法语和英文都提供显式词表；法语同时包含常见的带重音与
不带重音输入。未被词表覆盖的同义表达会使用本地多语言 embedding 进行匹配。

```text
中文：把这张截图里的文字提取出来
Français : Extrais le texte de cette capture d'écran.
English  : Extract the text from this screenshot.
          -> vision -> text_extraction

中文：这张图片里有什么？
Français : Qu'y a-t-il dans cette image ?
English  : What is in this image?
          -> vision -> image_understanding
```

## 安装本地 Embedding（可选）

Embedding 不是强制依赖：没有模型时，显式关键词仍然可以路由；安装后会增强同义句和
跨语言表达的识别。

在 Hermes 所使用的 Python 环境中安装：

```powershell
$HermesPython = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"
& $HermesPython -m pip install "sentence-transformers>=2.7,<3" "huggingface-hub>=0.34,<1.0"
```

联网下载模型一次：

```powershell
& $HermesPython -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

实际生效的插件配置文件：

```text
%LOCALAPPDATA%\hermes\plugins\hermes-capability-router\data\router-config.json
```

```json
{
  "embedding": {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "offline_only": true,
    "threshold": 0.42
  }
}
```

修改配置后重启 Gateway。`offline_only` 在模型下载完成后保持 `true`；`threshold`
越高，匹配越严格。

## 致谢与上游参考

本插件为独立实现，并以 MIT 许可证发布。下列项目没有被复制或打包进本项目；它们分别
提供架构启发或可选集成能力：

| 项目 | 与本插件的关系 |
| --- | --- |
| [aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router) | **仅架构参考。** 本插件的 Semantic Router 借鉴了它的 route / utterance / embedding threshold 思路；不导入、不打包，也不是运行时依赖。 |
| [huggingface/sentence-transformers](https://github.com/huggingface/sentence-transformers) | **可选运行时依赖。** 仅在启用本地 embedding 语义回退时使用。 |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | **可选集成。** 只有在安装其可选 fetcher 依赖后，`ScraplingFetcher` 才用于 HTML 提取。 |
| [GitHub REST API](https://docs.github.com/en/rest) | **外部元数据接口。** 用于发现仓库简介和 README；公开仓库发现不需要 Token。 |

请分别查看每个上游项目自己的许可证与署名要求。

## 安装插件

将 `plugin/` 目录内的内容复制到：

```text
%LOCALAPPDATA%\hermes\plugins\hermes-capability-router\
```

重启 Hermes Gateway，然后用 `hermes plugins list` 确认插件已启用。
