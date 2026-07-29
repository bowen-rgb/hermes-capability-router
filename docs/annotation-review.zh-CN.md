# Annotation 审核与标签修正

自动发现不会直接激活能力。每个发现项都会保留在审核队列中，并以清晰的视觉状态显示：

| 标识 | 含义 | 能否进入运行时能力库 |
| --- | --- | --- |
| 🟡 | 待审核 | 否 |
| 🟠 | 需要修正 | 否，先解决标红问题 |
| 🟢 | 已批准 | 是 |
| 🔴 | 已拒绝 | 否，但仍保留在审核历史中 |
| 🟥 | 标签明确有误 | 否，必须手动修正或移除 |
| 🟧 | 自动检查提示 | 可继续检查，不等同于错误 |

这避免了“6 个工具批准了 5 个，但看不到第 6 个哪里有问题”的情况：每个草稿始终独立显示状态、来源、置信度、标签和具体问题。

## 在 Hermes 中审核

```text
/capability-review
/capability-review pending
/capability-review approve <编号>
/capability-review reject <编号> [原因]
/capability-review set-tags <编号> 标签一, 标签二
/capability-review mark-wrong <编号> <错误标签> [原因]
/capability-review presets
/capability-review apply-preset <编号> <预设类别 ID>
```

示例：某个工具只理解图像内容，却被错误标注为 OCR：

```text
/capability-review mark-wrong 6 ocr 该工具不提取文字，只做图像理解
/capability-review set-tags 6 image understanding, visual reasoning
/capability-review apply-preset 6 vision.image_understanding
/capability-review approve 6
```

`mark-wrong` 会显示红色问题，并阻止批准；`set-tags` 移除被标错标签后会重新评估该草稿。`reject` 不会删除记录，因此日后仍能看到哪一个工具被拒绝以及原因。

## 预设类别

预设目录覆盖视觉、文档、文本、代码、网页研究、数据、音频与自动化等常见能力，例如：

```text
vision.image_text_extraction
vision.image_understanding
document.parsing
text.translation
text.summarization
text.retrieval
code.development
web.research
data.analysis
audio.speech_to_text
audio.text_to_speech
automation.workflow
```

它们是审核时的可编辑建议，而不是强制分类；无法匹配的发现项可以保留为自定义 capability。

分类层次参考了 Hugging Face 对任务的做法：先使用少量稳定的粗粒度任务分类，再以细粒度标签表达差异。该项目未复制其代码或分类数据。参见 [Hugging Face Tasks 文档](https://huggingface.co/docs/hub/models-tasks)。

对于 MCP 发现项，MCP 仅是一种 implementation/调用协议；审核的是它所提供的 capability，而不是把 MCP 本身当成类别。GitHub 的官方 MCP Server 展示了工具可覆盖代码、仓库、Issue、PR 与工作流等不同能力域，可作为 discovery 结果的人工判断参考。参见 [GitHub MCP Server](https://github.com/github/github-mcp-server)。
