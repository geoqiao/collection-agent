# Few-Shot Examples: CRISIS - 危机信号

## Example 1: 自杀倾向

**User:** "我不想活了，死了算了，你们别逼我了。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户表达自杀倾向，属于危机信号
- 情绪: negative（极度绝望）
- CRISIS 触发单向门，立即停止催收，启动危机干预

**Intent:**
```xml
<intent>
  <category>CRISIS</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>escalate</type>
  <tool_calls>
    <tool_call>
      <name>trigger_crisis_protocol</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <crisis_type>suicidal_ideation</crisis_type>
        <priority>urgent</priority>
      </parameters>
    </tool_call>
    <tool_call>
      <name>alert_crisis_team</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <message_content>用户表达自杀倾向</message_content>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"我非常理解您现在的感受。无论遇到什么困难，都有人愿意帮助您。请拨打心理援助热线 400-161-9995，有专业的心理咨询师 24 小时在线。您并不孤单。"

---

## Example 2: 自残威胁

**User:** "你们再催我，我就割腕！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户以自残威胁，属于危机信号
- 情绪: angry/negative
- CRISIS 触发单向门，立即停止催收，启动危机干预

**Intent:**
```xml
<intent>
  <category>CRISIS</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>angry</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>escalate</type>
  <tool_calls>
    <tool_call>
      <name>trigger_crisis_protocol</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <crisis_type>self_harm_threat</crisis_type>
        <priority>urgent</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"我非常担心您的安全。请立即联系心理援助热线 400-161-9995，或拨打 110 寻求紧急帮助。您的生命安全是最重要的。"

---

## Example 3: 严重疾病/住院

**User:** "我得了癌症，正在化疗，真的没钱还。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户披露严重疾病，属于危机/特殊情况
- 情绪: negative（绝望）
- CRISIS 触发单向门，停止催收，启动特殊处理

**Intent:**
```xml
<intent>
  <category>CRISIS</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>escalate</type>
  <tool_calls>
    <tool_call>
      <name>trigger_crisis_protocol</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <crisis_type>severe_illness</crisis_type>
        <priority>high</priority>
      </parameters>
    </tool_call>
    <tool_call>
      <name>request_medical_documentation</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉听到这个消息。您的健康是最重要的。我会将您的情况升级至特殊处理团队，他们将根据您的实际情况制定合适的方案。请您保重身体。"

---

## Example 4: 家庭暴力/人身安全

**User:** "我丈夫知道后会打死我的，求你们别说了。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户披露家庭暴力风险，属于危机信号
- 情绪: negative（恐惧）
- CRISIS 触发单向门，停止催收，提供安全资源

**Intent:**
```xml
<intent>
  <category>CRISIS</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>escalate</type>
  <tool_calls>
    <tool_call>
      <name>trigger_crisis_protocol</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <crisis_type>domestic_violence</crisis_type>
        <priority>urgent</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"您的安全是最重要的。如果您处于危险中，请立即拨打 110 报警，或联系全国反家暴热线 12338。我们会暂停所有联系，您的安全优先。"

---

## Example 5: 重大变故（丧亲/灾害）

**User:** "家里刚出了车祸，我孩子走了，你们现在别找我。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户披露重大丧亲变故，属于危机信号
- 情绪: negative（极度悲痛）
- CRISIS 触发单向门，停止催收，表达慰问并升级

**Intent:**
```xml
<intent>
  <category>CRISIS</category>
  <confidence>high</confidence>
  <escalation>true</escalation>
  <emotion>negative</emotion>
</intent>
```

**Action:**
```xml
<action>
  <type>escalate</type>
  <tool_calls>
    <tool_call>
      <name>trigger_crisis_protocol</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <crisis_type>bereavement</crisis_type>
        <priority>high</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉听到这个噩耗。请节哀顺变。我会立即暂停所有催收联系，您的特殊情况将升级至专人处理。如有需要，心理援助热线 400-161-9995 随时为您提供支持。"
