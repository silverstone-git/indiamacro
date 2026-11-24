"""A fake OpenAI-compatible chat server, for testing the terminal's LLM path without a key.

    uv run python -m indiamacro.monitor.fake_llm            # serves http://127.0.0.1:8799/v1
    # .env:  LLM_ENDPOINT=http://127.0.0.1:8799/v1   LLM_API_KEY=fake   LLM_MODEL=fake-analyst

It speaks just enough of ``POST /v1/chat/completions``: on the first turn it answers with
``tool_calls`` chosen by the same keyword planner the mock analyst uses; once tool results
are in the conversation it replies with a short write-up quoting them. The responses are
canned, not intelligent: the point is to exercise the real request/tool-loop code.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .assistant import plan


def _reply(messages: list[dict], tools: bool) -> dict:
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    question = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    if tools and not tool_msgs:
        calls = [{"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function",
                  "function": {"name": n, "arguments": json.dumps(a)}} for n, a in plan(question)]
        return {"role": "assistant", "content": None, "tool_calls": calls}
    evidence = "\n\n".join(m["content"] for m in tool_msgs) or question
    first = [ln.strip() for ln in evidence.splitlines() if ln.strip()][:6]
    body = "\n".join(f"- {ln}" for ln in first)
    return {"role": "assistant", "content": f"**Fake LLM answer** (canned, for testing the tool loop).\n\n{body}\n\n"
                                            "_Caveat:_ this text was produced by `fake_llm`, not a language model."}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self.send_error(404)
            return
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        msg = _reply(req.get("messages", []), bool(req.get("tools")))
        out = json.dumps({"id": f"chatcmpl-{uuid.uuid4().hex[:10]}", "object": "chat.completion", "created": int(time.time()),
                          "model": req.get("model", "fake"), "choices": [{"index": 0, "message": msg,
                          "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="fake OpenAI-compatible endpoint for testing")
    ap.add_argument("--port", type=int, default=8799)
    args = ap.parse_args(argv)
    print(f"fake LLM at http://127.0.0.1:{args.port}/v1  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
