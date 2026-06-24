import json
from openai import OpenAI

# Deepseek API
client = OpenAI(
	api_key="", #请在这里输入您的api_key
	base_url="https://api.deepseek.com"
)
# 聊天文件获取
chat_path = r""


# -----------------------以上内容可修改-----------------------------


# 读取聊天文件
with open(chat_path, "r", encoding="utf-8") as f:
	data = json.load(f)
print(data.keys())
chat_data = data["messages"]
print(f"成功读取 {len(chat_data)} 条聊天记录")
# 拼接聊天
chat_text = ""
for msg in chat_data:
	content = msg.get("content", "")
	# 跳过空消息
	if not content:
		continue
	sender = msg.get("senderDisplayName", "未知")
	time = msg.get("formattedTime", "")
	msg_type = msg.get("type", "")
	chat_text += (
		f"[{time}] "
		f"{sender} "
		f"({msg_type}): "
		f"{content}\n"
	)
# 检查
if not chat_text.strip():
	print("未识别到聊天记录")
	exit()
#输入内容(prompt)
prompt = f"""
请你作为专业的关系分析AI。
分析以下微信聊天记录：
请详细分析：
1. 双方关系
2. 暧昧程度（0~100）
3. 谁更主动
4. 情绪变化
5. 双方性格特点
6. 是否存在冷淡期
7. 聊天氛围
8. 关系发展趋势
9. 双方依赖感
10. 是否存在隐藏情绪
聊天记录：
{chat_text}
"""
print("\n正在发送给 DeepSeek 分析...\n")
# 调用deepseek
response = client.chat.completions.create(
	model="deepseek-v4-flash",
	messages=[
		{
			"role": "user",
			"content": prompt
		}
	],
	temperature=0.7
)
# 结果获取
result = response.choices[0].message.content
print(result)
# 保存
with open("分析结果.txt", "w", encoding="utf-8") as f:
	f.write(result)
print("\n分析完成")
print("结果已保存：分析结果.txt")

