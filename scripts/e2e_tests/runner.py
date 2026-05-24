"""E2E test runner — executes test cases against the real agent with LLM."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Allow running directly without package installation
if str(Path(__file__).parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parents[2]))

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.main import CollectAgentSystem
from collect_agent.skills.base import SkillResult
from scripts.e2e_tests.test_cases import TestCase


@dataclass
class TestResult:
    """Result of a single test case execution."""

    name: str
    passed: bool = True
    intent_category: str = ""
    intent_confidence: str = ""
    response_text: str = ""
    errors: list[str] = field(default_factory=list)
    skill_status: str = ""
    thinking_preview: str = ""


class E2ERunner:
    """Runs E2E tests against the full CollectAgentSystem with real LLM."""

    def __init__(self) -> None:
        self.system = CollectAgentSystem.from_config()
        self._test_users: set[str] = set()

    def _create_user(self, test_case: TestCase) -> str:
        """Create a test user for the test case."""
        user_id = f"e2e_{test_case.name}"
        state = UserState(
            user_id=user_id,
            profile=UserProfile(
                user_id=user_id,
                name="测试用户",
                overdue_days=test_case.overdue_days,
                amount_due=test_case.amount_due,
                occupation=test_case.occupation,
            ),
        )
        self.system.store.save(state)
        self._test_users.add(user_id)
        return user_id

    async def _send_message(
        self, user_id: str, message: str, round_num: int = 0
    ) -> SkillResult | None:
        """Send a user message and get the skill result."""
        session = self.system.session_manager.get_or_create(user_id)

        # Pre-set negotiation round if needed
        if round_num > 0:
            session.user_state.conversation.negotiation_round = round_num

        event = Event(
            user_id=user_id,
            type=EventType.USER_REPLIED,
            payload={"message": message},
        )
        return await session.handle_event(event)

    def _check_intent(
        self, test_case: TestCase, session, result: SkillResult | None
    ) -> list[str]:
        """Check intent classification against expectations."""
        errors: list[str] = []
        intent_check = test_case.intent_check
        if intent_check is None:
            return errors

        actual_category = session.user_state.conversation.current_intent
        expected = intent_check.category.value

        if actual_category != expected:
            errors.append(
                f"意图错误: 期望 {expected}, 实际 {actual_category}"
            )

        # Note: fast-path keywords bypass LLM and may not set confidence.
        # Full confidence verification requires LLM-based evaluation.
        return errors

    def _check_response(
        self, test_case: TestCase, result: SkillResult | None
    ) -> list[str]:
        """Check response quality against expectations."""
        errors: list[str] = []
        resp_check = test_case.response_check
        if resp_check is None:
            return errors

        if result is None:
            errors.append("无 SkillResult 返回")
            return errors

        text = result.response_text or ""

        # Forbidden substrings
        for forbidden in resp_check.forbidden_substrings:
            if forbidden in text:
                errors.append(f"回复包含禁止内容: '{forbidden}'")

        # Required substrings
        if resp_check.required_substrings:
            found = any(req in text for req in resp_check.required_substrings)
            if not found:
                reqs = ", ".join(resp_check.required_substrings)
                errors.append(f"回复缺少必要内容 (期望包含: {reqs})")

        # Max length
        if resp_check.max_length > 0 and len(text) > resp_check.max_length:
            errors.append(f"回复过长: {len(text)} > {resp_check.max_length}")

        return errors

    async def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case and return the result."""
        result = TestResult(name=test_case.name)

        try:
            user_id = self._create_user(test_case)

            # Send the user message
            skill_result = await self._send_message(
                user_id,
                test_case.user_message,
                test_case.negotiation_round,
            )

            # Get the session state after handling
            session = self.system.session_manager.get(user_id)
            if session:
                result.intent_category = (
                    session.user_state.conversation.current_intent or ""
                )

            if skill_result:
                result.skill_status = skill_result.status
                result.response_text = skill_result.response_text or ""
                result.thinking_preview = skill_result.thinking[:200]

            # Run checks
            if session:
                intent_errors = self._check_intent(test_case, session, skill_result)
                result.errors.extend(intent_errors)

            response_errors = self._check_response(test_case, skill_result)
            result.errors.extend(response_errors)

            # Run extra assertions
            if test_case.extra_assertions and skill_result:
                extra = test_case.extra_assertions(skill_result)
                result.errors.extend(extra)

            result.passed = len(result.errors) == 0

        except Exception as e:
            result.passed = False
            result.errors.append(f"执行异常: {e}")

        return result

    async def run_all(self, test_cases: list[TestCase]) -> list[TestResult]:
        """Run all test cases and return results."""
        results: list[TestResult] = []
        for tc in test_cases:
            print(f"\n{'='*60}")
            print(f"运行: {tc.name} — {tc.description}")
            print(f"{'='*60}")
            result = await self.run_test(tc)
            results.append(result)

            status = "PASS" if result.passed else "FAIL"
            print(f"结果: {status}")
            print(f"  意图: {result.intent_category}")
            print(f"  回复: {result.response_text[:150]}...")
            if result.errors:
                for err in result.errors:
                    print(f"  ❌ {err}")

        return results


def print_summary(results: list[TestResult]) -> None:
    """Print a summary of all test results."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"\n{'='*60}")
    print(f"测试总结: {passed}/{total} 通过, {failed} 失败")
    print(f"{'='*60}")

    if failed > 0:
        print("\n失败的用例:")
        for r in results:
            if not r.passed:
                print(f"  ❌ {r.name}: {', '.join(r.errors)}")

    print("\n通过的用例:")
    for r in results:
        if r.passed:
            print(f"  ✅ {r.name}")


async def main() -> None:
    from scripts.e2e_tests.test_cases import ALL_TESTS

    runner = E2ERunner()
    results = await runner.run_all(ALL_TESTS)
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
