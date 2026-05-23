# Few-Shot Examples: A类 - 合作意愿

## Example 1: 确认还款

**User:** "好的，我明天就把钱还上。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户明确表示明天还款，属于积极合作态度
- 情绪: positive
- 无需催收压力，应提供还款指引并确认

**Intent:**
```xml
<intent>
  <category>A</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>positive</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
  <tool_calls>
    <tool_call>
      <name>send_payment_guide</name>
      <parameters>
        <channel>sms</channel>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"感谢您的配合！还款方式已发送至您的手机，请查收。还款成功后系统会自动更新状态，如有任何问题随时联系。"

---

## Example 2: 询问还款方式

**User:** "我想还款，但是不知道怎么操作，可以教一下吗？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户主动询问还款方式，合作意愿明确
- 情绪: positive
- 需要提供清晰的还款指引

**Intent:**
```xml
<intent>
  <category>A</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>positive</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
  <tool_calls>
    <tool_call>
      <name>send_payment_guide</name>
      <parameters>
        <channel>current</channel>
        <detail_level>step_by_step</detail_level>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"当然可以。您可以通过以下方式还款：1. 银行转账至账户 xxx；2. 支付宝/微信扫码支付；3. 登录APP在线还款。需要我发送详细的操作步骤到您的手机吗？"

---

## Example 3: 请求分期

**User:** "我现在手头紧，能不能分期还？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户表达还款意愿但提出分期请求
- 情绪: neutral，略带焦虑
- 需要评估分期资格并引导

**Intent:**
```xml
<intent>
  <category>A</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>neutral</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
  <tool_calls>
    <tool_call>
      <name>check_installment_eligibility</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"理解您的情况。我可以帮您查询分期还款的资格和可选方案，请稍等。"

---

## Example 4: 确认金额

**User:** "我欠的是 5280 元对吗？我这就去还。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户主动确认金额并表示立即还款
- 情绪: positive
- 需核对金额（从 facts 读取）并给予确认

**Intent:**
```xml
<intent>
  <category>A</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>positive</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
</action>
```

**Final Message:**
"是的，您的应还金额为 5280 元。感谢您的配合，还款成功后我们会及时更新您的账户状态。"

---

## Example 5: 已还款确认

**User:** "我已经还了，你们查一下。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户声称已还款，需要核实
- 情绪: neutral
- 应先感谢，再查询系统确认

**Intent:**
```xml
<intent>
  <category>A</category>
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
      <name>verify_payment</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"感谢您的还款。我正在为您核实到账情况，请稍等片刻。"
