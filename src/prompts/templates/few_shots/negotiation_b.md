# Few-Shot Examples: B类 - 协商意愿

## Example 1: 请求延期

**User:** "最近失业了，能不能宽限两周？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户提出延期请求，属于协商意图
- 情绪: negative（失业压力）
- 需评估延期资格，不直接拒绝

**Intent:**
```xml
<intent>
  <category>B</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
  <tool_calls>
    <tool_call>
      <name>check_extension_eligibility</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <requested_days>14</requested_days>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"理解您目前的困难。我可以帮您申请延期还款，请稍等，我正在查询您的延期资格。"

---

## Example 2: 请求减免

**User:** "利息太高了，能不能减免一部分？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户对利息提出异议，希望减免
- 情绪: negative
- 需查询减免政策，不承诺具体金额

**Intent:**
```xml
<intent>
  <category>B</category>
  <confidence>high</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
  <tool_calls>
    <tool_call>
      <name>check_relief_options</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"您的诉求我已记录。我需要查询一下当前是否有适用的减免政策，请稍等。"

---

## Example 3: 部分还款协商

**User:** "我先还 2000，剩下的下个月再还，可以吗？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户提出部分还款方案
- 情绪: neutral
- 需评估部分还款是否可接受

**Intent:**
```xml
<intent>
  <category>B</category>
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
      <name>evaluate_partial_payment</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <amount>2000</amount>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"感谢您愿意先还一部分。我先帮您确认一下这个方案是否可行，请稍等。"

---

## Example 4: 要求调整还款日

**User:** "能不能把还款日改到每月 15 号？我工资那天发。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户希望调整还款日以匹配收入周期
- 情绪: neutral
- 属于合理协商请求

**Intent:**
```xml
<intent>
  <category>B</category>
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
      <name>check_date_change_eligibility</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <preferred_date>15</preferred_date>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"理解您的需求，将还款日调整到发薪日确实更方便。我来帮您查询是否可以调整，请稍等。"

---

## Example 5: 质疑费用

**User:** "逾期费怎么这么多？我不认可，要重新算。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户对逾期费用提出质疑
- 情绪: negative
- 需核实费用明细，保持客观

**Intent:**
```xml
<intent>
  <category>B</category>
  <confidence>medium</confidence>
  <escalation>false</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>reply</type>
  <tool_calls>
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
"我来为您调取详细的费用明细，包括本金、利息和逾期费用的计算方式，请稍等。"
