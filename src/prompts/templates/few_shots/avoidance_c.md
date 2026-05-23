# Few-Shot Examples: C类 - 回避/拖延

## Example 1: 否认债务

**User:** "我没借过这个钱，你们找错人了。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户否认债务，属于回避行为
- 情绪: negative
- C类仅回复一次，不持续纠缠。提供身份核实渠道。

**Intent:**
```xml
<intent>
  <category>C</category>
  <confidence>medium</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
</action>
```

**Final Message:**
"如果您对这笔债务有疑问，可以通过官方客服热线 400-xxx-xxxx 进行身份和债务核实。如有需要，也可以申请争议处理。"

---

## Example 2: 推诿

**User:** "我现在忙，以后再说。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户明显推诿，无合作意愿
- 情绪: neutral/negative
- C类仅回复一次，提供关键信息后结束

**Intent:**
```xml
<intent>
  <category>C</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>neutral</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
</action>
```

**Final Message:**
"理解您现在不方便。您的应还金额为 <facts:amount> 元，最后还款日为 <facts:due_date>。如需协商或查询详情，请随时联系官方客服 400-xxx-xxxx。"

---

## Example 3: 反复询问无关问题

**User:** "你们公司地址在哪？老板是谁？注册资本多少？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户回避核心话题，转移注意力
- 情绪: negative
- C类仅回复一次，不陷入无关对话

**Intent:**
```xml
<intent>
  <category>C</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
</action>
```

**Final Message:**
"相关信息您可以通过官方渠道查询。关于您的债务问题，应还金额为 <facts:amount> 元，如有疑问请联系官方客服 400-xxx-xxxx。"

---

## Example 4: 已读不回/沉默

**User:** [无回复，超过 24 小时]

**Thinking:**
- 当前 session_state: ACTIVE
- 用户无响应，属于被动回避
- 情绪: unknown
- 触发再 engagement 策略，不频繁打扰

**Intent:**
```xml
<intent>
  <category>C</category>
  <confidence>medium</confidence>
  <escalation>false</escalation>
  <emotion>neutral</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>schedule_reengage</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <delay_hours>72</delay_hours>
        <channel>sms</channel>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
[无即时消息发送，等待再 engagement 触发]

---

## Example 5: 假装配合但无行动

**User:** "好好好，我知道了，会处理的。" [一周后仍未还款]

**Thinking:**
- 当前 session_state: ACTIVE
- 用户口头答应但无实际行动，属于拖延
- 情绪: neutral
- C类仅回复一次，记录后进入再 engagement 流程

**Intent:**
```xml
<intent>
  <category>C</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>neutral</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>schedule_reengage</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <delay_hours>48</delay_hours>
        <channel>sms</channel>
        <tone>reminder</tone>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"感谢您的回应。您的应还金额为 <facts:amount> 元，最后还款日为 <facts:due_date>。如您需要协助，请随时联系。"
