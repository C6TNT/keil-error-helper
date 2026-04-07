# keil-error-helper

一个面向 `Keil / C51 / 蓝桥杯单片机模板工程` 场景的轻量 Windows 诊断工具。

它的目标不是自动改代码，而是帮助刚入门的同学更快完成这些事：

- 从一长段编译输出里找到第一条真正需要处理的错误
- 用更容易理解的话解释这条错误
- 告诉你先检查哪几个位置
- 结合蓝桥杯模板工程判断更像是哪一层的问题
- 一键生成适合发给学长或发群求助的文本
- 在需要时调用 AI 做更深入的排查建议

## 当前版本

- `V1.0`

## 产品状态

当前版本为 `V1.0`，定位为稳定正式版。

后续维护原则：

- 优先修复真实用户反馈
- 优先补新生高频问题
- 尽量不无节制增加复杂功能
- 继续保持“规则优先，AI 增强”的产品方向

## 当前版本能力

- 本地规则引擎
- 命令行分析入口
- `PySide6` 桌面界面
- 提取第一条关键错误
- 识别常见 `Keil / C51` 报错类型
- 根据文件路径定位更像是 `App / BSP / Devices / Drivers / Examples` 哪一层的问题
- 结合模板常见坑点给出额外提醒
- 生成适合发给学长或群里的结构化求助文本
- 场景选择
- 结果卡片化展示
- 优先级提示条
- 内置示例报错
- AI 设置
- AI 连接测试
- AI 深入分析
- 复制 AI 全部内容
- 复制单张 AI 卡片
- 复制 AI 卡片摘要
- 应用内关于页和版本信息
- 单文件 `exe` 稳定运行

## 项目结构

```text
Keil报错诊断器
├─ app/
│  ├─ main.py
│  ├─ cli.py
│  ├─ core/
│  │  ├─ parser.py
│  │  ├─ classifier.py
│  │  ├─ formatter.py
│  │  ├─ engine.py
│  │  ├─ ai_client.py
│  │  └─ config_store.py
│  ├─ data/
│  │  └─ keil_errors.json
│  └─ ui/
│     └─ main_window.py
├─ requirements.txt
├─ VERSION
├─ CHANGELOG.md
└─ run_app.bat
```

## 运行方式

### 1. 安装依赖

```powershell
pip install -r requirements.txt
```

### 2. 启动桌面版

```powershell
python app/main.py
```

或者直接双击：

- `run_app.bat`

## 推荐使用流程

1. 粘贴完整 `Keil` 编译输出
2. 先点 `开始分析`
3. 先修第一条错误
4. 修完后重新编译，再看新的第一条错误
5. 如果准备求助，优先使用：
   - `复制求助文本`
   - `复制 AI 摘要`
   - `复制问题卡 / 检查卡 / 漏改卡`
6. 如果要用 AI，先在 `AI 设置` 里填好配置，再点 `测试连接`

## AI 使用方式

从 `V0.5` 开始，推荐直接在应用内配置：

1. 打开 App
2. 点击 `AI 设置`
3. 填入：
   - API Key
   - Base URL
   - Model
4. 保存后先点 `测试连接`
5. 测试通过后再使用 `AI 深入分析`

配置会保存在应用目录下的 `config.json` 中。

当前默认推荐配置：

- `Base URL`：`https://api-inference.modelscope.cn/v1`
- `Model`：`Qwen/Qwen3.5-35B-A3B`

## 当前稳定性说明

目前这版已经修过这些关键问题：

- `exe` 启动时包导入失败
- 部分机器上输入框文字不可见
- 点击 `开始分析` 看起来没反应
- 单文件 `exe` 漏打包 `keil_errors.json`

这意味着当前版本不只是源码能跑，打包后的 `exe` 也已经能完成完整诊断流程。

## 仓库地址

- GitHub: [https://github.com/C6TNT/keil-error-helper](https://github.com/C6TNT/keil-error-helper)

