# Few-Shot Examples: E类 - 投诉/威胁

## Example 1: 威胁投诉

**User:** "你们再打电话我就去银保监会投诉你们！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户明确威胁投诉，情绪激烈
- 情绪: angry
- E类触发单向门，立即道歉并停止催收，进入投诉处理流程

**Intent:**
```xml
<intent>
  <category>E</category>
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
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>regulatory_threat</type>
        <priority>high</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉给您带来了不好的体验。您的投诉我已记录并升级至专人处理，后续将由投诉专员与您联系，联系电话 400-xxx-xxxx。感谢您的反馈。"

---

## Example 2: 威胁法律行动

**User:** "我要起诉你们，骚扰我！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户威胁法律诉讼
- 情绪: angry
- E类触发单向门，停止催收，记录并升级

**Intent:**
```xml
<intent>
  <category>E</category>
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
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>legal_threat</type>
        <priority>high</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉。您的诉求我已记录并升级，将由法务和投诉专员跟进处理。后续联系人会主动与您取得联系，请保持电话畅通。"

---

## Example 3: 社交媒体威胁

**User:** "我要把你们的行为发到微博和抖音，让所有人都知道！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户威胁公开曝光，舆情风险高
- 情绪: angry
- E类触发单向门，立即升级至舆情处理

**Intent:**
```xml
<intent>
  <category>E</category>
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
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>reputational_threat</type>
        <priority>urgent</priority>
      </parameters>
    </tool_call>
    <tool_call>
      <name>alert_pr_team</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <threat_level>high</threat_level>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉给您造成了困扰。您的反馈我已紧急升级至相关部门，将有专人与您沟通解决。请您保持电话畅通，我们会尽快联系您。"

---

## Example 4: 声称已报警

**User:** "我已经报警了，警察说你们这是骚扰！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户声称已报警
- 情绪: angry
- E类触发单向门，停止一切催收，记录并升级

**Intent:**
```xml
<intent>
  <category>E</category>
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
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>police_report</type>
        <priority>urgent</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉。您的情况我已记录并升级，将由专人负责跟进。后续会有专员与您联系处理此事，请您保持电话畅通。"

---

## Example 5: 要求赔偿

**User:** "你们骚扰我，我要精神损失赔偿！"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户提出赔偿要求
- 情绪: angry
- E类触发单向门，不争论赔偿合理性，记录并升级

**Intent:**
```xml
<intent>
  <category>E</category>
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
      <name>create_complaint_ticket</name>
      <parameters>
        <user_id>{{user_id}}</user_id>
        <type>compensation_claim</type>
        <priority>high</priority>
      </parameters>
    </tool_call>
  </tool_calls>
</action>
```

**Final Message:**
"非常抱歉给您带来了困扰。您的诉求我已记录并升级，将由专人评估并与您沟通。后续会有专员联系您，请保持电话畅通。"
