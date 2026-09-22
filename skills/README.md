# EBench coding agent skills

这套 skills 帮助 coding agent 完成 EBench **机器人策略评测**：准备环境、接入模型、运行实验、定位失败、解释结果。它们不是用于评测 coding agent 自身的 benchmark。

## 从哪里开始

| Skill | 优先级 | 适用请求 | 交付物 |
| --- | --- | --- | --- |
| [ebench-setup](ebench-setup/SKILL.md) | P0 | 首次使用、检查环境、复现 baseline | 环境检查结果、缺失项、可执行启动命令 |
| [ebench-evaluate](ebench-evaluate/SKILL.md) | P0 | 本地或在线评测、启动多 worker | 可追溯的 run、日志与完成状态 |
| [ebench-analyze](ebench-analyze/SKILL.md) | P0 | 生成报告、比较模型、分析能力短板 | HTML 报告、数据覆盖情况、带证据的结论 |
| [ebench-integrate-policy](ebench-integrate-policy/SKILL.md) | P1 | 把自己的 VLA 接入 EBench | observation/action 适配器及契约验证 |
| [ebench-debug](ebench-debug/SKILL.md) | P1 | 卡住、报错、动作异常、成功率异常 | 故障定位、最小修复、验证证据 |

P0 覆盖已有模型从准备到报告的完整路径；自定义模型先使用模型接入 skill，出现故障时再使用排查 skill。暂不单独拆出训练、数据下载、排行榜发布 skill：它们不是每次评测都需要，训练和数据准备可先沿用 baseline 文档。

## 使用方法

Skills 放在版本管理下的 `skills/`，每个目录包含标准 `SKILL.md`（含 `name` / `description`）。**此目录本身不保证被所有 agent 自动发现**。最直接的使用方式是在 EBench 仓库中让 agent 读取具体文件：

```text
请读取 skills/ebench-setup/SKILL.md，检查当前环境是否可以运行 X-VLA 在线评测，列出缺失项。
请读取 skills/ebench-evaluate/SKILL.md，用已有 endpoint 和 run_id 启动我的模型，只用 worker 0。
请读取 skills/ebench-integrate-policy/SKILL.md，把我的策略接入 EvalClient，先验证输入输出契约。
请读取 skills/ebench-debug/SKILL.md，排查这个 run 的 reset timeout，保留现有结果。
请读取 skills/ebench-analyze/SKILL.md，比较这两个结果目录，输出报告并说明评测覆盖是否一致。
```

也可以按所用 agent 的技能安装机制导入这些目录。安装后，若 agent 支持 `$skill-name`，可用 `$ebench-evaluate` 等名称调用；不要把复制整套技能到用户全局目录作为评测的前置条件。

所有 skill 中的仓库路径都相对 **EBench 根目录**，不是相对 skill 所在目录。技能正文使用英文，便于国际用户复用；agent 可以按用户语言回答。首次使用优先提供模型/检查点、在线或本地模式、split/赛道、GPU/worker 预算；已有任务再提供 run_id 和 endpoint。Token 通过本地环境或已有凭据机制提供，不写入仓库或报告。

## 维护与验收

以当前 checkout 的 baseline 和 `third_party/genmanip-client` 源码为准；升级 submodule 后，复核 CLI 参数、动作转换和结果解析行为。不要把某个 baseline 的归一化或动作布局当成所有模型的协议。

新增或修改 skill 时，除了检查 frontmatter 和文件引用，还应使用以下场景审阅其行为：

| 场景 | 预期行为 |
| --- | --- |
| 新 clone 缺少 submodule | 明确缺失依赖，不把 import 失败当作模型故障 |
| 用户要求真实模型评测 | 使用 baseline/自定义策略入口，不把 `gmp eval` 假动作算作模型成绩 |
| 已有在线 task 等待资源 | 查询已有 task，不重复创建任务 |
| step 超时，执行状态未知 | 丢弃旧 chunk，有限恢复并记录中断，不盲目重发动作 |
| analyse 输入为空 | 指出无本地结果，不把内置参考报告说成用户成绩 |
| 两个 run 的 split 或任务覆盖不同 | 标记不可直接比较，说明分母与缺失数据 |

这些场景是维护验收标准，不表示已执行 GPU 或在线平台端到端验证。
