import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src import app as assistant_app
from src import dashhome


class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.client = assistant_app.app.test_client()
        assistant_app._assistant_request_times.clear()

    def test_chat_endpoint_uses_server_key_and_returns_reply(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Hello there."))]
        )
        provider = Mock()
        provider.chat.completions.create.return_value = completion
        payload = {"messages": [{"role": "user", "content": "Hi"}]}

        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "server-secret"}),
            patch.object(assistant_app, "OpenAI", return_value=provider) as openai,
        ):
            response = self.client.post("/assistant/chat", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"reply": "Hello there."})
        openai.assert_called_once()
        self.assertEqual(openai.call_args.kwargs["api_key"], "server-secret")
        self.assertEqual(
            provider.chat.completions.create.call_args.kwargs["messages"][-1],
            {"role": "user", "content": "Hi"},
        )

    def test_chat_endpoint_rejects_invalid_message_roles(self):
        response = self.client.post(
            "/assistant/chat",
            json={"messages": [{"role": ["user"], "content": "Hi"}]},
        )

        self.assertEqual(response.status_code, 400)

    def test_chat_endpoint_requires_server_key(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post(
                "/assistant/chat",
                json={"messages": [{"role": "user", "content": "Hi"}]},
            )

        self.assertEqual(response.status_code, 503)

    def test_chat_endpoint_limits_requests_per_client(self):
        provider = Mock()
        provider.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Hello."))]
        )
        payload = {"messages": [{"role": "user", "content": "Hi"}]}
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "server-secret"}),
            patch.object(assistant_app, "OpenAI", return_value=provider),
            patch.object(assistant_app, "ASSISTANT_REQUESTS_PER_MINUTE", 1),
        ):
            first_response = self.client.post("/assistant/chat", json=payload)
            second_response = self.client.post("/assistant/chat", json=payload)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)


class AssistantClientTests(unittest.TestCase):
    def test_desktop_client_defaults_to_deployed_server(self):
        self.assertEqual(
            dashhome.ASSISTANT_API_URL, "https://cura-assistant-api.onrender.com"
        )

    def test_desktop_client_posts_chat_to_configured_server(self):
        response = Mock()
        response.json.return_value = {"reply": "Hello there."}

        with (
            patch.object(dashhome, "ASSISTANT_API_URL", "https://cura.example"),
            patch.object(dashhome.requests, "post", return_value=response) as post,
        ):
            reply = dashhome._request_assistant_reply(
                [{"role": "user", "content": "Hi"}]
            )

        self.assertEqual(reply, "Hello there.")
        post.assert_called_once_with(
            "https://cura.example/assistant/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
            timeout=35,
        )

    def test_desktop_client_requires_configured_server_url(self):
        with patch.object(dashhome, "ASSISTANT_API_URL", ""):
            with self.assertRaises(RuntimeError):
                dashhome._request_assistant_reply([])

    def test_client_reports_rate_limit_errors_clearly(self):
        error = dashhome.requests.HTTPError(
            response=SimpleNamespace(status_code=429)
        )

        self.assertIn("busy", dashhome._assistant_failure_message(error))
        self.assertIn("try again", dashhome._assistant_failure_message(error))

    def test_client_reports_unavailable_service_errors_clearly(self):
        error = dashhome.requests.HTTPError(
            response=SimpleNamespace(status_code=503)
        )

        self.assertIn(
            "temporarily unavailable", dashhome._assistant_failure_message(error)
        )

    def test_client_distinguishes_connection_and_timeout_errors(self):
        connection_message = dashhome._assistant_failure_message(
            dashhome.requests.ConnectionError()
        )
        timeout_message = dashhome._assistant_failure_message(
            dashhome.requests.Timeout()
        )

        self.assertIn("internet connection", connection_message)
        self.assertIn("too long to respond", timeout_message)


if __name__ == "__main__":
    unittest.main()
