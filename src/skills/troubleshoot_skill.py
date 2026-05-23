"""Troubleshoot skill for technical/operation inquiries."""

from __future__ import annotations

from src.skills.base import Skill, SkillContext, SkillResult, SkillResultStatus, ToolCallRecord
from src.tools.base import ToolResult


class TroubleshootSkill(Skill):
    name = "troubleshoot"
    description = "帮助用户解决技术问题或操作疑问"
    triggers = ["OPERATION_INQUIRY"]
    is_one_way_door = False

    def __init__(self, tools: list | None = None):
        super().__init__(tools)

    async def execute(self, ctx: SkillContext) -> SkillResult:
        user_msg = (ctx.user_message or "").lower()

        if "链接" in user_msg or "打不开" in user_msg or "无法访问" in user_msg:
            response = (
                "如果您无法打开支付链接，请尝试以下方法：\n"
                "1. 检查网络连接是否正常\n"
                "2. 尝试复制链接到浏览器打开\n"
                "3. 清除浏览器缓存后重试\n"
                "4. 如仍有问题，我们可以为您发送新的支付链接或提供其他还款方式。"
            )
        elif "密码" in user_msg or "登录" in user_msg or "账号" in user_msg:
            response = (
                "如果您遇到登录问题，请尝试：\n"
                "1. 点击“忘记密码”重置密码\n"
                "2. 确认输入的账号无误\n"
                "3. 检查是否开启了验证码拦截\n"
                "如问题持续，请联系人工客服协助。"
            )
        elif "扣款" in user_msg or "重复" in user_msg:
            response = (
                "如果您发现重复扣款，请不要担心：\n"
                "1. 我们会核实您的支付记录\n"
                "2. 如确认重复扣款，多余款项将在 3-5 个工作日内原路退回\n"
                "3. 请保留相关支付凭证以便查询"
            )
        else:
            response = (
                "感谢您的咨询。关于您的操作问题，建议：\n"
                "1. 仔细阅读页面提示信息\n"
                "2. 尝试刷新页面或重新进入\n"
                "3. 如问题仍未解决，我们可以为您转接人工客服。"
            )

        return SkillResult(
            status=SkillResultStatus.SUCCESS,
            response_text=response,
            actions=[],
        )
