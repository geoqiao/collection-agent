# Few-Shot Examples: D类 - 争议

## Example 1: 否认债务

**User:** "我根本没借过这笔钱，你们搞错人了！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户明确否认债务存在
- 情绪: angry/negative
- D类争议触发单向门，停止催收，提供证据或升级

**Intent:**
```xml
<intent>
  <category>D</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>angry</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>get_fee_breakdown</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
      </parameters>
    </tool_call>
    <tool_call>
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>debt_denial</type>
        <priority>high</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"您的疑虑我已记录。我将为您调取相关的借款合同和还款记录供您核实。在争议调查期间，我们将暂停催收联系。调查完成后我们会第一时间通知您。"

---

## Example 2: 质疑金额

**User:** "你们算的金额不对，我已经还了5000，为什么还显示欠8000？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户质疑账单金额，认为已还款未被记录
- 情绪: negative
- D类争议，需提供还款记录核查

**Intent:**
```xml
<intent>
  <category>D</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
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
    <tool_call>
      <name>get_fee_breakdown</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"理解您的疑问。我正在核查您的还款记录和账单明细。根据系统显示：[展示核查结果]。如您仍有异议，我可以为您创建争议工单，由专人详细核查。"

---

## Example 3: 费用异议

**User:** "这利息和罚息太高了，不符合法律规定！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户对费用合法性提出质疑
- 情绪: negative
- D类争议，需提供费用明细和法律依据

**Intent:**
```xml
<intent>
  <category>D</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>get_fee_breakdown</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <include_legal_basis>true</include_legal_basis>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"您的关切我理解。我正在为您调取详细的费用构成及计算依据。所有费用均按照合同约定及相关法律法规计算。如您对计算方式仍有疑问，可安排专员为您详细解释。"

---

## Example 4: 声称已还清

**User:** "我早就还清了，你们凭什么还催我？把结清证明拿出来！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户声称已还清，要求结清证明
- 情绪: angry
- D类争议，需核查还款状态

**Intent:**
```xml
<intent>
  <category>D</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>angry</emotion>
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
        <check_full_settlement>true</check_full_settlement>
      </parameters>
    </tool_call>
    <tool_call>
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>full_settlement_claim</type>
        <priority>high</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉给您带来困扰。我正在紧急核查您的还款记录和结清状态。如您确实已还清，我们将立即更正并道歉。核查结果将尽快通知您，在此期间暂停催收联系。"

---

## Example 5: 身份被盗用

**User:** "这不是我借的，我的身份证被盗用了，我要报警！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户声称身份被盗用
- 情绪: angry
- D类争议，高度敏感，需立即升级

**Intent:**
```xml
<intent>
  <category>D</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>angry</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>tool_call</type>
  <tool_calls>
    <tool_call>
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>identity_fraud</type>
        <priority>urgent</priority>
      </parameters>
    </tool_call>
    <tool_call>
      <name>pause_collection</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <hours>168</hours>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常理解您的担忧。如您认为存在身份被盗用情况，我们将立即暂停催收并启动身份核查流程。建议您同时向公安机关报案，我们将全力配合调查。专人会尽快与您联系处理此事。"
