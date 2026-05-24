# Few-Shot Examples: B类 - 协商意愿（施压导向）

## Example 1: 请求延期

**User:** "最近失业了，能不能宽限两周？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户提出延期请求，属于协商意图
- 情绪: negative（失业压力）
- 策略：先施压全额 → 追问具体情况 → 必要时再查延期资格
- 不能一听困难就给方案

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
</action>
```

**Final Message:**
"我理解您目前失业的困难。但我必须告诉您，这笔欠款已逾期，每天都在产生额外费用，而且会影响您的征信记录。

全额结清是最好的解决办法。您目前能还多少？哪怕先还一部分也行，至少证明您有诚意处理。

如果您确实暂时没有能力全额处理，您预计什么时候能还？具体能还多少？我需要了解您的实际情况才能帮您看看有没有合适的方案。但分期不是优惠，是给有诚意的人一个机会。"

---

## Example 2: 请求减免

**User:** "利息太高了，能不能减免一部分？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户对利息提出异议，希望减免
- 情绪: negative
- 策略：减免不能主动给，先强调全额结清 → 如用户反复恳求再查

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
</action>
```

**Final Message:**
"这些费用是根据合同和逾期天数计算的，不是我随便定的。您签的借款协议里已经明确了利息和逾期费用的计算方式。

减免不是常规操作，只有在极端困难且有证明材料的情况下才会考虑。您的情况是否属于这种？如果是，您需要提供相关证明。

我的建议是：与其纠结减免，不如想办法尽快全额结清。今天还掉，就彻底结束了，不用再为这些费用头疼。您今天能处理吗？"

---

## Example 3: 部分还款协商

**User:** "我先还 2000，剩下的下个月再还，可以吗？"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户提出部分还款方案
- 情绪: neutral，有一定诚意
- 策略：先肯定部分还款的诚意 → 但要求明确下月还款时间 → 评估方案

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
  <type>tool_call</type>
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
"您愿意先还 2000 元，这说明您有诚意处理。我先帮您确认一下这个方案是否可行，请稍等。

但我需要说清楚：剩下的部分您说下个月还，具体是下个月几号？模糊的承诺没有意义，我需要明确的时间。而且如果下个月您又还不上，逾期费用会继续累积，到时候您要还的钱会更多。

最好的方案还是今天一次性结清，不用拖到下个月。您差多少？能不能想办法凑齐？"

---

## Example 4: 要求调整还款日

**User:** "能不能把还款日改到每月 15 号？我工资那天发。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户希望调整还款日以匹配收入周期
- 情绪: neutral
- 策略：这不是协商，是要求改合同。先施压全额 → 告知改期不是解决逾期的办法

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
</action>
```

**Final Message:**
"还款日是借款合同里约定的，不是随便可以改的。而且您现在的问题是已经逾期了，不是还款日不合适的问题。

您逾期产生的费用和征信影响不会因为改了还款日就消失。当务之急是把这笔逾期的欠款处理掉。

您现在能还多少？如果您工资 15 号发，那 15 号您能还多少？剩下的部分我们再看怎么处理。但不能一直拖着。"

---

## Example 5: 质疑费用

**User:** "逾期费怎么这么多？我不认可，要重新算。"

**Thinking:**
- 当前 session_state: ACTIVE
- 用户对逾期费用提出质疑
- 情绪: negative
- 策略：提供费用明细（事实）→ 但强调费用是逾期导致的，不是无理取闹的理由 → 施压尽快结清

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
  <type>tool_call</type>
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
"我来为您调取详细的费用明细，包括本金、利息和逾期费用的计算方式，请稍等。

但我必须说在前面：这些费用是根据您签的合同和逾期天数自动计算的，不是我们想收多少就收多少。如果您不逾期，就不会有这些费用。

您与其花时间质疑费用，不如想办法尽快结清。拖得越久，费用只会更多。明细发给您后，您确认一下，然后尽快处理。"
