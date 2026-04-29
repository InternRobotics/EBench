<div align="right">

[English](README.md) | 简体中文

</div>

<div align="center">

<img src="assets/ebench-teaser.png" alt="EBench — Elemental Mobile Manipulation Benchmark" width="92%" />

# EBench：Elemental Mobile Manipulation Benchmark

**从单一成功率，升级为多维能力画像。**
*由[上海人工智能实验室](https://www.shlab.org.cn/)发布。*

<p>
  <a href="https://internrobotics.github.io/EBench-doc/zh-cn/"><img alt="Project Page" src="https://img.shields.io/badge/%E9%A1%B9%E7%9B%AE%E4%B8%BB%E9%A1%B5-EBench%20Docs-1f6feb?style=for-the-badge&logo=readthedocs&logoColor=white"></a>
  <img alt="arXiv" src="https://img.shields.io/badge/arXiv-coming%20soon-lightgrey?style=for-the-badge&logo=arxiv&logoColor=white">
  <a href="https://internrobotics.shlab.org.cn/eval"><img alt="Leaderboard" src="https://img.shields.io/badge/%E6%8E%92%E8%A1%8C%E6%A6%9C-%E5%9C%A8%E7%BA%BF%E6%8C%91%E6%88%98%E8%B5%9B-22c55e?style=for-the-badge&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge"></a>
</p>

<p>
  <a href="https://github.com/InternRobotics/GenManip"><img alt="Simulation Server" src="https://img.shields.io/badge/%E4%BB%BF%E7%9C%9F%E6%9C%8D%E5%8A%A1%E7%AB%AF-GenManip-181717?style=for-the-badge&logo=github&logoColor=white"></a>
  <a href="https://github.com/InternRobotics/genmanip-client"><img alt="Client CLI" src="https://img.shields.io/badge/%E5%AE%A2%E6%88%B7%E7%AB%AF%20CLI-genmanip--client-181717?style=for-the-badge&logo=github&logoColor=white"></a>
</p>

<p>
  <a href="https://huggingface.co/datasets/InternRobotics/EBench-Assets"><img alt="HF Assets" src="https://img.shields.io/badge/HuggingFace-%E8%B5%84%E4%BA%A7-orange?style=for-the-badge&logo=huggingface&logoColor=white"></a>
  <a href="https://huggingface.co/datasets/InternRobotics/EBench-Dataset"><img alt="HF Dataset" src="https://img.shields.io/badge/HuggingFace-%E6%95%B0%E6%8D%AE%E9%9B%86-orange?style=for-the-badge&logo=huggingface&logoColor=white"></a>
  <img alt="ModelScope" src="https://img.shields.io/badge/ModelScope-coming%20soon-lightgrey?style=for-the-badge&logoColor=white">
</p>

</div>

---

## EBench 是什么？

EBench 是一个基于 NVIDIA Isaac Sim 的室内 VLA 操作仿真评测框架。它不再把模型行为压缩成一个总成功率，而是产出一份**多维能力画像**，让模型"强在哪里、弱在哪里"变得可读、可比、可定位。

本仓库是 EBench 项目的**入口仓库**，存放 Baseline 代码与辅助脚本；仿真运行时、`gmp` CLI、以及数据集分别托管在各自独立的仓库（见上方导航徽章）。

## EBench 的不一样

- **三类操作形态全覆盖** —— 同时覆盖*长程操作（Long-Horizon）*、*精细操作（Dexterous & Precise）*与*移动操作（Mobile）*三类任务，而非只专精其一。
- **五维原子诊断** —— 每个任务都打上 *Scene · Atomic Skill · Horizon · Precision · Mobility* 标签，把黑盒分数拆成可读的强弱坐标。
- **四维泛化测试** —— 在 *Object · Background · Instruction · Mixed* 上施加可控扰动，使分数下滑能够被归因到具体的泛化失败类型。
- **严格训测隔离** —— `val_train` / `val_unseen` 公开供调参；隔离的 `test`（Test-Mini）驱动排行榜，分数反映真实泛化而非对评测分布的拟合。

评测同时提供两条赛道：**Specialist**（Tabletop 或 Mobile Manip）与 **Generalist**（同时覆盖两类形态）。

完整方法论、任务体系与各维度设计原则请见[项目文档](https://internrobotics.github.io/EBench-doc/zh-cn/)。

## 项目组成

EBench 由若干仓库组成，**本仓库是项目入口**：

| 组件 | 仓库地址 | 提供内容 |
| --- | --- | --- |
| **EBench**（本仓库） | [InternRobotics/EBench](https://github.com/InternRobotics/EBench) | Baseline 代码、脚本、项目入口 |
| **GenManip** | [InternRobotics/GenManip](https://github.com/InternRobotics/GenManip) | Isaac Sim 评测服务端、任务配置 |
| **genmanip-client** | [InternRobotics/genmanip-client](https://github.com/InternRobotics/genmanip-client) | `gmp` CLI 与 `EvalClient` Python API |
| **EBench-Assets** | [🤗 EBench-Assets](https://huggingface.co/datasets/InternRobotics/EBench-Assets) | 场景、物体与任务资产 |
| **EBench-Dataset** | [🤗 EBench-Dataset](https://huggingface.co/datasets/InternRobotics/EBench-Dataset) | 训练轨迹（LeRobot 格式） |
| **文档站点** | [internrobotics.github.io/EBench-doc](https://internrobotics.github.io/EBench-doc/zh-cn/) | 环境配置、评测流程、CLI 参考 |
| **在线挑战赛** | [internrobotics.shlab.org.cn/eval](https://internrobotics.shlab.org.cn/eval) | 远程评测、排行榜、诊断报告 |

```
EBench/
├── baselines/       # 参考策略实现（每个 baseline 一个子目录）
├── scripts/         # 评测与结果分析脚本
├── assets/          # 本 README 使用的静态素材
├── LICENSE
└── README.md
```

## 快速开始

EBench 采用 client–server 架构：服务端运行 Isaac Sim，客户端（`gmp` CLI）是一个轻量包，直接装在模型所在的 Python 环境即可。

```bash
# 1. 启动服务端  →  详见环境配置
#    https://internrobotics.github.io/EBench-doc/zh-cn/getting-started/environment/

# 2. 在模型环境中安装客户端
git clone https://github.com/InternRobotics/genmanip-client.git
cd genmanip-client && pip install -e .

# 3. 运行一次评测
gmp submit ebench/generalist/test --run_id my_first_run
gmp eval  -a r5a -g lift2 --worker_ids 0
gmp status
```

8 卡 RTX 4090 上跑完整套验证集大约需要 **30 分钟**。完整的环境配置、资产下载与 `gmp` 命令参考请见[文档站点](https://internrobotics.github.io/EBench-doc/zh-cn/)。

## 任务总览

**26 种任务**分布在*长程任务（Long-Horizon）*、*抓取放置（Pick-and-Place）*、*灵巧精细操作（Dexterous & Precise）*三个任务族；与四维泛化、三层划分组合后，共构成 **794 条评测任务**。完整视频演示见[任务展示](https://internrobotics.github.io/EBench-doc/zh-cn/evaluation/task-showcase/)。

## Baseline

参考策略放在 `baselines/<name>/` 下，每个 baseline 自带 README 与 `gmp eval` 兼容的入口命令。EBench 已在 **π0**、**π0.5**、**XVLA**、**InternVLA-A1** 上完成首轮验证 —— 当前结果与各维度诊断报告请见[排行榜](https://internrobotics.shlab.org.cn/eval)。

接入自己的模型请参考[接入自定义模型](https://internrobotics.github.io/EBench-doc/zh-cn/evaluation/custom-model/)。

## 在线挑战赛

[internrobotics.shlab.org.cn/eval](https://internrobotics.shlab.org.cn/eval) 提供 7×24 小时在线评测平台。所有提交都在隔离的 Test-Mini 上以可复现的标准化协议执行，并自动生成诊断报告（能力雷达、验证→测试迁移曲线、泛化雷达、任务级热力图）。提交流程见[挑战赛](https://internrobotics.github.io/EBench-doc/zh-cn/challenge/)页面。

## 引用

论文即将发布。在论文公开之前：

```bibtex
@misc{ebench2026,
  title  = {EBench: Elemental Mobile Manipulation Benchmark},
  author = {Shanghai AI Laboratory},
  year   = {2026},
  note   = {Preprint coming soon},
  url    = {https://internrobotics.github.io/EBench-doc/}
}
```

## 协议

MIT，详见 [LICENSE](LICENSE)。基于 [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac/sim)、[cuRobo](https://github.com/NVlabs/curobo) 与 [LeRobot](https://github.com/huggingface/lerobot) 数据格式构建。欢迎提交 issue 与 PR。
