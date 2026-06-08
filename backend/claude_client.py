"""Session 3：Claude API Tool Use 循环（含 System Prompt + history 截断）。"""
import os
from datetime import date

from dotenv import load_dotenv
from anthropic import Anthropic

from tools.definitions import TOOLS
from tools.executors import execute_tool

load_dotenv()

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
MODEL = 'claude-sonnet-4-6'

MAX_HISTORY_MESSAGES = 20  # 超过则只保留最近 N 条，避免撑爆 context window

SYSTEM_PROMPT_TEMPLATE = """你是一个 CRM/ERP 业务数据助手，通过工具查询 MySQL 数据库回答用户的中文或英文问题。

## 当前日期
今天是 {today}。当用户提到"上个月"、"本月"、"今年至今"等相对时间时，
请以这个日期为基准计算实际的起止日期，不要凭训练知识猜测当前时间。

## 数据库与查询规则
- crm_os 和 erp_os 是两个独立的 MySQL 数据库实例，不能在同一条 SQL 里跨库 JOIN。
  如果问题需要同时用到两边的数据（例如按公司名关联 CRM 商机和 ERP 客户），
  请拆分成多次工具调用：先查一边拿到关键信息（如公司名/customer_id），
  再查另一边用名称匹配，最后由你在回答里把结果合并呈现。
- 所有 ERP 查询（包括 execute_readonly_sql 中针对 erp_os 的 SQL）必须带 organization_id = 1 过滤条件，
  因为 ERP 是多租户系统。
- 展示和统计金额时统一使用 base_currency_amount（本位币金额），不要用 total_incl_tax。
  如需展示原始币种金额，同时给出 currency 和 total_incl_tax。
- 所有查询都必须排除软删除和无效记录：deleted_at IS NULL、is_active = 1；
  统计销售额时还要排除已取消（CANCELLED）和草稿（DRAFT）订单。
- 内置的 7 个工具已经处理好上述过滤逻辑，优先使用它们；
  只有在内置工具无法满足需求时才使用 execute_readonly_sql 兜底，
  并自行确保 SQL 满足以上所有规则。

## 禁止访问的内容
以下表和字段任何情况下都不能出现在回答或查询结果中：
- crm_os.users.password_hash
- erp_os.audit_logs（整张表）
- erp_os.ai_call_logs（整张表）
- erp_os.login_attempts（整张表）
如果用户的问题涉及这些内容，礼貌地拒绝并说明无法提供。

## 回答风格
- 始终使用中文回答（除非用户明确用英文提问）。
- 基于工具返回的真实数据作答，不要编造数字。
- 数据较多时用简洁的列表或表格呈现，并给出关键结论或汇总。
"""


def build_system_prompt():
    """生成包含当前日期的 System Prompt，确保"上个月"等相对时间表述被正确换算。"""
    return SYSTEM_PROMPT_TEMPLATE.format(today=date.today().isoformat())


def truncate_history(messages):
    """保留 system 角色之外最近 MAX_HISTORY_MESSAGES 条消息，防止 history 无限增长。"""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    return messages[-MAX_HISTORY_MESSAGES:]


def chat(messages):
    """运行一次完整的 Tool Use 循环，返回 Claude 的最终文本回答。"""
    messages = truncate_history(list(messages))

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=build_system_prompt(),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != 'tool_use':
            return ''.join(block.text for block in response.content if block.type == 'text')

        messages.append({'role': 'assistant', 'content': response.content})

        tool_results = []
        for block in response.content:
            if block.type != 'tool_use':
                continue
            result = execute_tool(block.name, block.input)
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': str(result),
            })

        messages.append({'role': 'user', 'content': tool_results})
