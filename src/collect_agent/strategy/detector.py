from collect_agent.core.constants import Intent


class IntentDetector:
    KEYWORDS = {
        Intent.WILLING_TO_PAY: [
            "还", "付", "处理", "解决", "明天", "后天", "下周", "月底",
            "可以", "愿意", "尽量", "安排",
        ],
        Intent.UNWILLING_TO_PAY: [
            "没钱", "不还", "不付", "困难", "失业", "破产",
            "凭什么", "不", "拒绝", "没能力",
        ],
        Intent.COMPLAINT: [
            "投诉", "举报", "垃圾", "骗子", "骚扰", "违法",
            "威胁", "恐吓", "曝光",
        ],
        Intent.PAYMENT_METHOD_INQUIRY: [
            "怎么还", "哪里还", "方式", "渠道", "转账", "支付宝",
            "微信", "银行卡", "怎么操作",
        ],
        Intent.OPERATION_INQUIRY: [
            "失败", "错误", "不行", "打不开", "点不了", "卡",
            "问题", "bug", "故障",
        ],
    }

    def detect(self, text: str) -> Intent:
        text = text.lower().strip()

        if not text or text in {"嗯", "哦", "好", "知道了", "。", ",", " "}:
            return Intent.INEFFECTIVE_CONTACT

        scores = {intent: 0 for intent in Intent}
        for intent, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[intent] += 1

        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

        return Intent.INEFFECTIVE_CONTACT