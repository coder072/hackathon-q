import asyncio
import json
from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.services.intent.assessment import AnalysisContext
from app.services.intent.catalog import load_official_sites
from app.services.intent.llm import LlmIntentClassifier


class FakeCompletions:
    def __init__(self, reply=None, error=None, delay=0.0):
        self.reply, self.error, self.delay = reply, error, delay
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.reply


def reply(payload, finish_reason="stop", refusal=None):
    content = payload if isinstance(payload, str) else json.dumps(payload)
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish_reason, message=message)])


def classifier(completions: FakeCompletions, timeout=1.0) -> LlmIntentClassifier:
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return LlmIntentClassifier(client, "gpt-4.1-mini", load_official_sites(), timeout)


def run(coro):
    return asyncio.run(coro)


def test_parses_structured_output_and_sends_catalog_enum():
    completions = FakeCompletions(
        reply(
            {
                "serviceKey": "naver",
                "intentCode": "SERVICE_LOGIN",
                "confidence": 1.7,
                "matchesIntent": False,
                "explanation": "네이버가 아닌 주소예요.",
            }
        )
    )
    context = AnalysisContext(
        "naver.github.io", 5, 0, ("유명 서비스(naver)와 유사한 도메인입니다.",)
    )
    result = run(classifier(completions).classify("네이버 로그인", context))
    assert (result.matches_intent, result.explanation) == (False, "네이버가 아닌 주소예요.")

    assert (result.service_key, result.intent_code, result.source) == (
        "naver",
        "SERVICE_LOGIN",
        "llm",
    )
    assert result.confidence == 1.0  # 범위를 벗어난 값은 0~1 로 자른다
    response_format = completions.kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert "naver" in schema["properties"]["serviceKey"]["enum"]
    assert "NONE" in schema["properties"]["intentCode"]["enum"]
    assert completions.kwargs["model"] == "gpt-4.1-mini"
    # 사용자 문장은 데이터로 감싸서 보낸다
    assert {"matchesIntent", "explanation"} <= set(schema["required"])
    user = completions.kwargs["messages"][-1]["content"]
    assert user.startswith("<user_message>네이버 로그인</user_message>")
    assert "도메인: naver.github.io" in user and "위험 점수: 5" in user


def test_none_means_unknown():
    completions = FakeCompletions(
        reply({"serviceKey": "NONE", "intentCode": "NONE", "confidence": 0})
    )
    result = run(classifier(completions).classify("모르겠어요"))
    assert (result.service_key, result.intent_code) == (None, None)


def _request() -> httpx2.Request:
    return httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


@pytest.mark.parametrize(
    "completions",
    [
        # 카탈로그 밖 키(예: 프롬프트 인젝션으로 만든 값)는 버린다
        FakeCompletions(
            reply({"serviceKey": "evil", "intentCode": "SERVICE_LOGIN", "confidence": 1})
        ),
        FakeCompletions(reply("https://evil.example/login")),
        FakeCompletions(reply({"serviceKey": "naver"})),
        FakeCompletions(reply("", refusal="I can't help with that.")),
        FakeCompletions(reply({}, finish_reason="length")),
        FakeCompletions(reply({}, finish_reason="content_filter")),
        FakeCompletions(error=openai.APIConnectionError(request=_request())),
        FakeCompletions(
            error=openai.RateLimitError(
                "no credits", response=httpx2.Response(429, request=_request()), body=None
            )
        ),
        FakeCompletions(delay=1),
    ],
)
def test_failures_return_none_for_rule_fallback(completions):
    assert run(classifier(completions, timeout=0.05).classify("네이버 로그인")) is None
