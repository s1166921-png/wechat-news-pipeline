"""Rewrite WeChat article in B2P policy-interpretation style."""
import json, ssl, os, re, urllib.request

# Read original article
with open('C:/Users/EDY/temp_wechat_article.txt', 'r', encoding='utf-8') as f:
    original = f.read()

# Load API key from .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
api_key = ''
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DEEPSEEK_API_KEY='):
            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

if not api_key:
    print('ERROR: No API key found')
    raise SystemExit(1)

print(f'Original length: {len(original)} chars')

# B2P system prompt
B2P_SYSTEM_PROMPT = """你是一位深耕跨境电商行业的政策分析师兼行业观察者。你的文章被读者评价为"每一篇都值得收藏"。

## 核心定位
你不是媒体小编，你是一个真正懂跨境行业的人，用读者能听懂的人话把复杂的政策、趋势、案件拆解清楚。你的文章介于"咨询公司行业简报"和"朋友发来的长消息"之间。

## 结构公式（必须严格遵守）

标题: [事件/政策] + [冲击/信号] — 断言式，带紧迫感，禁止问句标题

开头: 日期 + 官方机构 + 关键数据/条款。直接甩事实，0废话。
     ❌ 禁止: "大家好""今天聊聊""随着XX发展""近年来"
     ✅ 正确: "7月28日，国务院新闻办发布会抛出数据..."
     ✅ 正确: "最近跨境圈里讨论最多的，莫过于..."

## PART 1 — 背景/为什么 (100-300字)
  用 2-4 个极短段落解释事件背后的深层原因。
  每段 1-3 句话，绝不超过 4 句。

## PART 2 — 核心变化/影响分析 (200-400字)
  用 "变化一""变化二""信号一""信号二" 或 "01." "02." 逐条拆解。
  每条: 小标题 + 2-4句解释 + "这意味着..."
  必须有平台/政策/金额的具体名称，不能模糊化。

## PART 3 — 实操指南/应对建议 (150-300字)
  "01." "02." "03." 编号，每条一个具体行动。
  每条: 动作 + 为什么 + 截止时间(如果有)。

结尾段落 (50-80字):
  一句话总结信号 + 对比(短期vs长期) + 金句收尾。
  金句公式: "XX不是用来挡住谁，而是让真正想XX的人有更清晰的路径可走"

## Markdown 格式要求
- PART 标题必须用 ## PART X — ... 格式
- 只在最重要的关键词上偶尔使用 **加粗**（如极其关键的数字或结论），全文 3-5 处即可

## 段落与节奏铁律

1. **每段不超过 3 句话**。宁可多分段，绝不堆大段。
2. **段间穿插反问**: "什么概念？" "这意味着什么？" "到底新在哪？"
3. **数据密度**: 每一段必须有至少一个具体数字/日期/政策编号/金额。
4. **对比驱动**: 每篇文章至少出现 3 组对比结构 —
   - "过去...现在/未来..."
   - "不再是...而是..."
   - "好处是...坏处是..."
   - "对A来说...对B来说..."

## 语言风格

### 口语化术语
- "秒杀"（指自动拦截/下架）、"擦边"、"暴雷"、"一刀切"、"堵死"、"走不通"
- "九龙治水"（多头监管）、"亡羊补牢"、"警钟"、"生死劫"、"寒冬"
- "铁证如山"、"人去楼空"、"三不策略"

### 句式节奏
- 60% 陈述句（摆事实）+ 20% 反问句（拉回注意力）+ 20% 短句（下结论）
- 隔 3-5 段来一句带情绪的判断句: "这么看来，老操作真的走不通了。"

### 必须出现的元素
- ✅ 具体的平台名称: 亚马逊、Temu、SHEIN、TikTok Shop、速卖通
- ✅ 具体的政策编号: "第X条" "XX号公告" "HTS编码"
- ✅ 具体的时间节点: "7月8日起" "10月1日前"
- ✅ 具体的金额: "200万→500万" "营业额5%" "追缴5710亿"
- ✅ 辩证视角: 每说一个"好处"，必须跟一个"但"或"坏处是"

## 禁止事项
- ❌ 以 "大家好""今天我们来聊""随着XX的发展" 开头
- ❌ 连续 3 段超过 3 句话
- ❌ 使用 "我们团队""我司""本机构"（保持客观第三方视角）
- ❌ 模糊词: "很多""大幅""不少""显著" — 全部替换为精确数字
- ❌ 文章中后段出现营销话术
- ❌ 表格格式
- ❌ 超过 4 级的嵌套结构

## 输出格式
直接以文章标题开头，使用 Markdown 语法:
# 标题行

开头段落

## PART 1 — [小标题]

[内容]

## PART 2 — [小标题]

01. [子标题] — [解释内容]
02. [子标题] — [解释内容]

## PART 3 — [小标题]

01. [行动项] — 为什么，截止时间
02. [行动项] — 为什么，截止时间

结尾段落"""

user_prompt = f"""请根据以上政策解读写作风格，重写以下微信公众号文章。要求：

1. **保留原文核心信息**：2026年第5号公告的函调机制、跨境电商为何更容易中招、函调的具体代价、三条实操防线
2. **完全替换风格**：按照 B2P 风格的结构、语言、节奏重写
3. **去除营销内容**：原文末尾"易税通"广告全部去掉，结尾不要任何推广
4. **增强数据密度**：确保每一段都有具体数字/日期/政策编号
5. **注意**：今天是 2026年7月22日

=== 原文 ===
{original}

=== 要求 ===
直接输出改写后的完整文章（Markdown格式），以标题行开头。"""

print('Calling DeepSeek API...')
payload = json.dumps({
    'model': 'deepseek-chat',
    'messages': [
        {'role': 'system', 'content': B2P_SYSTEM_PROMPT},
        {'role': 'user', 'content': user_prompt},
    ],
    'temperature': 0.7,
    'max_tokens': 4096,
}).encode('utf-8')

ctx = ssl.create_default_context()
req = urllib.request.Request(
    'https://api.deepseek.com/v1/chat/completions',
    data=payload,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
)

try:
    resp = urllib.request.urlopen(req, timeout=180, context=ctx)
    result = json.loads(resp.read().decode('utf-8'))
    content = result['choices'][0]['message']['content']

    # Save result
    output_path = 'C:/Users/EDY/rewritten_article.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print('=== REWRITTEN ARTICLE ===')
    print(content)
    print(f'\nSaved to: {output_path}')
except Exception as e:
    print(f'API Error: {e}')
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8', errors='replace'))
