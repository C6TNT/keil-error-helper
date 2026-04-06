# keil-error-helper

一个面向 `Keil / C51 / 蓝桥杯单片机模板工程` 场景的轻量 Windows 诊断工具。

第一版目标不是自动改代码，而是帮助初学者更快完成这些事：

- 从一长段编译输出里提取第一条真正错误
- 判断错误属于哪一类
- 给出简单直接的中文解释
- 告诉用户先检查哪几个位置
- 结合蓝桥杯模板工程判断更像是哪一层的问题
- 提醒这类错误最容易把模板哪里改坏
- 一键生成适合发给学长或群里的求助文本

## 当前版本目标

当前是第一版原型，包含：

- 规则引擎
- 命令行分析入口
- `PySide6` 桌面界面骨架
- 适合发给学长或群里的求助文本生成功能

## 当前版本

- `V0.1`

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
│  │  └─ engine.py
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

### 3. 命令行测试

```powershell
python app/cli.py
```

然后直接粘贴 `Keil` 报错输出。

## 当前支持的能力

- 提取第一条关键 `error`
- 提取出错文件和行号
- 识别常见 `Keil/C51` 错误类型
- 根据文件路径定位更像是 `App / BSP / Devices / Drivers / Examples` 哪一层的问题
- 结合模板常见坑点给出额外提醒
- 生成适合发给学长或群里的结构化求助文本

输出内容包括：

- 错误原文
- 错误类型
- 中文解释
- 最可能原因
- 建议先检查的位置
- 模板定位建议
- 模板常见坑点提醒
- 下一步动作

## 使用建议

- 优先粘贴完整 Build Output
- 先只修第一条错误
- 修完后重新编译，再看新的第一条错误
- 如果准备求助，优先用“复制求助文本”按钮

## 后续迭代方向

- 支持按“页面 / 按键 / 参数 / 频率 / 超声波”做更细粒度建议
- 支持更丰富的蓝桥杯模板规则库
- 支持结果卡片化展示，进一步降低新手阅读压力
