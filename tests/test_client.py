import asyncio
import json
import os
import unittest
from unittest.mock import patch

import httpx

from codex_deepseek.client import DeepSeekError, ask, get_api_key, list_models, validate_key

FAKE_KEY = "test-credential-not-real"


class ClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"DEEPSEEK_API_KEY": FAKE_KEY}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    async def test_request_and_provider_metadata(self):
        def handler(request):
            self.assertEqual(str(request.url), "https://api.deepseek.com/chat/completions")
            self.assertEqual(request.headers["Authorization"], f"Bearer {FAKE_KEY}")
            data = json.loads(request.content)
            self.assertEqual(data["model"], "requested-alias")
            self.assertEqual(len(data["messages"]), 2)
            self.assertEqual(data["messages"][1], {"role": "user", "content": "订单幂等？"})
            self.assertFalse(data["stream"])
            return httpx.Response(200, json={
                "model": "actual-provider-id", "id": "completion-1",
                "choices": [{"message": {"content": " 使用唯一请求号。 "}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 42},
            })
        result = await ask("订单幂等？", "requested-alias", transport=httpx.MockTransport(handler))
        self.assertEqual(result["response_model"], "actual-provider-id")
        self.assertEqual(result["requested_model"], "requested-alias")
        self.assertEqual(result["answer"], "使用唯一请求号。")
        self.assertEqual(result["usage"]["total_tokens"], 42)

    async def test_absent_metadata_is_not_guessed(self):
        result = await ask("question", transport=httpx.MockTransport(lambda _: httpx.Response(
            200, json={"choices": [{"message": {"content": "answer"}, "finish_reason": "length"}]})))
        self.assertIsNone(result["response_model"])
        self.assertEqual(result["requested_model"], "deepseek-flash")
        self.assertEqual(result["finish_reason"], "length")

    async def test_model_environment_and_override(self):
        os.environ["DEEPSEEK_MODEL"] = "environment-model"
        from codex_deepseek.client import validate_request
        self.assertEqual(validate_request("q", None, 180), "environment-model")
        self.assertEqual(validate_request("q", "explicit-model", 180), "explicit-model")

    async def test_invalid_inputs_never_send_request(self):
        def fail(_):
            self.fail("Invalid input must not reach the network")
        for prompt, model, timeout in [("", None, 180), ("x" * 50001, None, 180),
                                       ("q", "bad model", 180), ("q", None, True),
                                       ("q", None, 9), ("q", None, 601)]:
            with self.subTest(prompt_length=len(prompt), model=model, timeout=timeout):
                with self.assertRaises(DeepSeekError):
                    await ask(prompt, model, timeout, transport=httpx.MockTransport(fail))

    async def test_http_error_does_not_echo_key_or_body(self):
        for status in (302, 401, 429, 500):
            with self.subTest(status=status), self.assertRaises(DeepSeekError) as error:
                await ask("q", transport=httpx.MockTransport(lambda _: httpx.Response(
                    status, text=f"private prompt and {FAKE_KEY}", headers={"Location": "https://example.com"})))
            self.assertIn(str(status), str(error.exception))
            self.assertNotIn(FAKE_KEY, str(error.exception))
            self.assertNotIn("private prompt", str(error.exception))

    async def test_network_errors_and_timeout_are_sanitized(self):
        for exception in (httpx.ConnectError(FAKE_KEY), httpx.ReadTimeout(FAKE_KEY)):
            def handler(_, error=exception):
                raise error
            with self.assertRaises(DeepSeekError) as error:
                await ask("q", transport=httpx.MockTransport(handler))
            self.assertNotIn(FAKE_KEY, str(error.exception))

    async def test_cancel_propagates(self):
        async def handler(_):
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await ask("q", transport=httpx.MockTransport(handler))

    async def test_bad_response_shapes(self):
        for body in ([], {}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}):
            with self.subTest(body=body), self.assertRaises(DeepSeekError):
                await ask("q", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)))

    async def test_invalid_json(self):
        with self.assertRaisesRegex(DeepSeekError, "invalid JSON"):
            await ask("q", transport=httpx.MockTransport(lambda _: httpx.Response(200, text="not json")))

    async def test_models_uses_get(self):
        def handler(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.path, "/models")
            return httpx.Response(200, json={"data": [{"id": "example-model"}]})
        result = await list_models(transport=httpx.MockTransport(handler))
        self.assertEqual(result["data"][0]["id"], "example-model")

    async def test_environment_key_precedes_keychain(self):
        with patch("codex_deepseek.client.subprocess.run") as run:
            self.assertEqual(get_api_key(), FAKE_KEY)
            run.assert_not_called()
        os.environ["DEEPSEEK_API_KEY"] = "invalid key"
        with self.assertRaises(DeepSeekError):
            get_api_key()

    async def test_keychain_read(self):
        os.environ.pop("DEEPSEEK_API_KEY")
        with patch("codex_deepseek.client.sys.platform", "darwin"), patch(
            "codex_deepseek.client.subprocess.run"
        ) as run:
            run.return_value.returncode = 0
            run.return_value.stdout = FAKE_KEY
            self.assertEqual(get_api_key(), FAKE_KEY)
            self.assertNotIn(FAKE_KEY, str(run.call_args))

    async def test_missing_key(self):
        os.environ.pop("DEEPSEEK_API_KEY")
        with patch("codex_deepseek.client.sys.platform", "linux"), self.assertRaisesRegex(DeepSeekError, "Missing"):
            get_api_key()

    async def test_key_validation(self):
        for value in ("", "one two", "one\ntwo", "one\ttwo"):
            with self.subTest(value=value), self.assertRaises(DeepSeekError):
                validate_key(value)


if __name__ == "__main__":
    unittest.main()
