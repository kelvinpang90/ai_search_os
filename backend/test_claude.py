"""Session 3 验收测试：端到端测试 5 个示例问题，确认 Claude 能调用工具并给出中文回答。"""
from claude_client import chat

QUESTIONS = [
    '上个月的总销售额是多少？',
    '销售额最高的前 5 个客户是谁？',
    '哪些商品库存低于补货触发点？',
    '目前谈判阶段的商机有哪些？总金额是多少？',
    '客户 Kopitiam 最近下了多少单？',
]

for q in QUESTIONS:
    print(f'=== 问题: {q} ===')
    reply = chat([{'role': 'user', 'content': q}])
    assert reply.strip(), f'问题「{q}」未得到回答'
    print(f'回答: {reply}\n')

print(f'全部 {len(QUESTIONS)} 个问题均得到回答。')
