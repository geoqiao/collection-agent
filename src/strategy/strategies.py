from src.core.constants import Intent


STRATEGIES = {
    Intent.WILLING_TO_PAY: {
        "type": "confirm_plan",
        "description": "确认还款计划",
        "max_rounds": 3,
        "actions": ["ask_timing", "confirm_amount", "send_reminder"],
    },
    Intent.UNWILLING_TO_PAY: {
        "type": "negotiate",
        "description": "谈判协商",
        "max_rounds": 3,
        "actions": ["probe_reason", "negotiate_plan", "warn_consequences"],
    },
    Intent.INEFFECTIVE_CONTACT: {
        "type": "re_engage",
        "description": "重新建立联系",
        "max_rounds": 4,
        "actions": ["remind", "change_channel", "contact_guarantor"],
    },
    Intent.COMPLAINT: {
        "type": "pause_collection",
        "description": "暂停催收并转客服",
        "max_rounds": 1,
        "actions": ["acknowledge", "apologize", "transfer_to_cs"],
    },
    Intent.PAYMENT_METHOD_INQUIRY: {
        "type": "guide_payment",
        "description": "指导还款操作",
        "max_rounds": 5,
        "actions": ["provide_options", "send_link", "confirm_completion"],
    },
    Intent.OPERATION_INQUIRY: {
        "type": "troubleshoot",
        "description": "解决操作问题",
        "max_rounds": 3,
        "actions": ["diagnose", "provide_steps", "escalate_if_needed"],
    },
    "standard_reminder": {
        "type": "standard_reminder",
        "description": "标准提醒（敏感职业专用）",
        "max_rounds": 1,
        "actions": ["send_standard_message"],
    },
}


RESPONSE_TEMPLATES = {
    "confirm_plan": [
        "您好{name}，感谢您愿意处理此事。请问您计划什么时候还款？",
        "好的，{name}。请问您能否结清全部{amount}元？",
        "明白了，{name}。那我们就约定{date}前还款，届时我会再提醒您。",
    ],
    "negotiate": [
        "{name}，我理解您可能有困难。能告诉我是什么原因导致暂时无法还款吗？",
        "{name}，根据您的情况，我们可以协商一个分期方案，您觉得每月还多少比较合适？",
        "{name}，如果长期逾期不还款，可能会影响您的信用记录，甚至面临法律诉讼。",
    ],
    "re_engage": [
        "{name}，您好。关于您的逾期账单，请尽快处理。",
        "{name}，我们注意到您的账单已逾期{days}天，请尽快联系我们处理。",
    ],
    "pause_collection": [
        "非常抱歉给您带来不好的体验，{name}。我会记录您的问题并转给客服处理。在此期间，我们将暂停催收。",
    ],
    "guide_payment": [
        "{name}，您可以通过以下方式还款：1. App内一键还款 2. 银行转账 3. 支付宝/微信。需要我发送还款链接吗？",
    ],
    "troubleshoot": [
        "{name}，请您尝试以下步骤：1. 刷新页面 2. 清除缓存 3. 重新登录。如果问题仍然存在，我可以帮您转接客服。",
    ],
    "standard_reminder": [
        "您好，这里是{{机构名称}}。您在{{平台名称}}的借款已逾期{days}天，逾期金额{amount}元。逾期将影响您的个人信用记录，并可能产生罚息。请您尽快安排还款。如有疑问，请联系客服{{客服电话}}。",
    ],
}
