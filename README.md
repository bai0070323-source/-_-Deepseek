# 聊天记录分析工具 💬

基于 DeepSeek AI 的聊天记录分析工具，支持 GUI 界面、CLI 命令行和 FastAPI 后端三种使用方式。

## 功能

上传导出的 JSON 聊天记录，从以下维度进行 AI 分析：

- 双方关系定位与亲密度
- 暧昧程度评估（0~100）
- 谁更主动
- 情绪变化曲线
- 双方性格特点
- 是否存在冷淡期
- 聊天氛围变化
- 关系发展趋势
- 双方依赖感
- 隐藏情绪与潜台词

## 使用方式

### 方式一：GUI 界面（推荐）

```bash
pip install openai
python gui.py
```

### 方式二：CLI 命令行

1. 打开 `分析.py`，填入 API Key 和聊天文件路径
2. 运行：
```bash
python 分析.py
```

### 方式三：FastAPI 后端

```bash
pip install openai fastapi uvicorn
python 分析\(函数\).py
```

访问 `http://localhost:8000/docs` 查看 API 文档。

## 依赖

- Python 3.8+
- openai >= 1.0（DeepSeek API）

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "微信聊天分析" gui.py
```

## 注意事项

- 需要 DeepSeek API Key（[deepseek.com](https://api.deepseek.com)）
- 聊天记录仅发送至 DeepSeek API 进行分析，不会上传至其他第三方
- 请勿在公开仓库中包含真实的聊天记录 JSON 文件

## 许可

MIT License

## 声明

如需导出微信聊天记录请参考
https://github.com/ILoveBingLu/CipherTalk
