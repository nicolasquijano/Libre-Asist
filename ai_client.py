"""Multi-provider AI client.

Adapts request/response format based on the API URL pattern. Supports:
- OpenAI-compatible (OpenAI, MiniMax, Ollama /v1, localAI, Groq, Together, etc.)
- Ollama native (/api/generate, /api/chat)
- Anthropic Messages API (/v1/messages)
- MiniMax native (/v1/text/chatcompletion_v2)

Optional web-search tool:
    When cfg["enable_web_search"] is True, the client exposes a `web_search`
    function to chat-completion style providers (OpenAI, Anthropic, Ollama
    chat, MiniMax native) and runs a tool-calling loop so the model can fetch
    current information from the web.

Usage:
    cfg = config.load()
    client = AIClient(cfg)
    response_text = client.ask("hola")
"""

import json
import urllib.request
import urllib.error
from i18n import _

try:
    import web_search
except Exception:
    web_search = None


WEB_SEARCH_TOOL_OPENAI = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the public web and return up to a few relevant results "
                       "(title, URL, snippet). Use for current events, recent facts, "
                       "prices, or anything that may be newer than your training data.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Concise web search query.",
                }
            },
            "required": ["query"],
        },
    },
}

WEB_SEARCH_TOOL_ANTHROPIC = {
    "name": "web_search",
    "description": WEB_SEARCH_TOOL_OPENAI["function"]["description"],
    "input_schema": WEB_SEARCH_TOOL_OPENAI["function"]["parameters"],
}

MAX_TOOL_ITERATIONS = 3


class AIError(Exception):
    pass


class AIClient:
    def __init__(self, cfg):
        self.url = cfg.get("api_url", "").strip()
        self.key = cfg.get("api_key", "").strip()
        self.model = cfg.get("model", "").strip()
        self.system = cfg.get("system_prompt", "").strip()
        self.system_preset = cfg.get("system_preset", "General")
        self.temperature = float(cfg.get("temperature", 0.7))
        self.max_tokens = int(cfg.get("max_tokens", 2048))
        self.timeout = int(cfg.get("timeout", 180))
        self.enable_web_search = bool(cfg.get("enable_web_search", False))
        self.search_max_results = int(cfg.get("search_max_results", 5))

    def _language_instruction(self):
        """Get a strong language matching instruction."""
        return (
            "CRITICAL LANGUAGE RULE: You MUST respond in the EXACT same language "
            "as the user's request. If the user writes in Spanish, respond in Spanish. "
            "If the user writes in English, respond in English. "
            "If the user writes in Chinese, respond in Chinese. "
            "Match the language of the user's input throughout your entire response, "
            "including any explanations, summaries, JSON values, and field content like "
            "'summary', 'title', etc. This is the highest priority instruction."
        )

    def _format(self):
        u = self.url.lower()
        if "/v1/messages" in u:
            return "anthropic"
        if "/api/generate" in u:
            return "ollama_generate"
        if "/api/chat" in u:
            return "ollama_chat"
        if "/v1/text/chatcompletion_v2" in u:
            return "minimax_native"
        if "/chat/completions" in u or "/v1/chat" in u:
            return "openai"
        return "openai"

    def _supports_tools(self, fmt):
        return fmt in ("openai", "ollama_chat", "anthropic", "minimax_native")

    def ask(self, user_prompt):
        if not self.url:
            raise AIError(_("ai.error.no_url"))
        if not self.model:
            raise AIError(_("ai.error.no_model"))
        if not user_prompt or not user_prompt.strip():
            raise AIError(_("ai.error.empty_prompt"))

        fmt = self._format()
        if not (self.enable_web_search and self._supports_tools(fmt)):
            return self._ask_plain(user_prompt, fmt)
        try:
            return self._ask_with_tools(user_prompt, fmt)
        except AIError:
            raise
        except Exception as e:
            return self._ask_plain(user_prompt, fmt) + \
                "\n\n" + _("ai.web_search_note", str(e))

    def _ask_plain(self, user_prompt, fmt):
        if fmt == "openai":
            return self._ask_openai(user_prompt)
        if fmt == "ollama_generate":
            return self._ask_ollama_generate(user_prompt)
        if fmt == "ollama_chat":
            return self._ask_ollama_chat(user_prompt)
        if fmt == "anthropic":
            return self._ask_anthropic(user_prompt)
        if fmt == "minimax_native":
            return self._ask_minimax_native(user_prompt)
        return self._ask_openai(user_prompt)

    def _post(self, url, headers, body_bytes):
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                result = json.loads(r.read().decode("utf-8"))
                return self._check_api_error(result)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise AIError(_("ai.error.http", str(e.code), detail[:500]))
        except urllib.error.URLError as e:
            raise AIError(_("ai.error.connection", str(e.reason)))
        except AIError:
            raise
        except Exception as e:
            raise AIError(_("ai.error.network", str(e)))

    def _check_api_error(self, result):
        # MiniMax error format
        if isinstance(result, dict) and "base_resp" in result:
            br = result["base_resp"]
            sc = br.get("status_code", 0)
            if sc != 0 and sc != 200:
                raise AIError(_("ai.error.api_status", str(sc), br.get("status_msg", "unknown")))
        # OpenAI error format
        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            raise AIError(_("ai.error.api", err.get("message", json.dumps(err))))
        return result

    def _ask_openai(self, prompt):
        messages = []
        lang_instr = self._language_instruction()
        full_system = lang_instr + "\n\n" + self.system if self.system else lang_instr
        messages.append({"role": "system", "content": full_system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))
        return self._extract_openai(result)

    def _extract_openai(self, result):
        if "choices" in result and result["choices"]:
            ch = result["choices"][0]
            if "message" in ch:
                return ch["message"].get("content", "") or ""
            if "text" in ch:
                return ch.get("text", "") or ""
        if "reply" in result:
            return result["reply"]
        if "content" in result and isinstance(result["content"], str):
            return result["content"]
        raise AIError("Respuesta no reconocida: " + json.dumps(result)[:300])

    def _ask_ollama_generate(self, prompt):
        lang_instr = self._language_instruction()
        full = (lang_instr + "\n\n" + self.system + "\n\n" if self.system else lang_instr + "\n\n") + prompt
        body = {
            "model": self.model,
            "prompt": full,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        headers = {"Content-Type": "application/json"}
        result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))
        return result.get("response", "") or ""

    def _ask_ollama_chat(self, prompt):
        messages = []
        lang_instr = self._language_instruction()
        full_system = lang_instr + "\n\n" + self.system if self.system else lang_instr
        messages.append({"role": "system", "content": full_system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        headers = {"Content-Type": "application/json"}
        result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))
        if "message" in result and "content" in result["message"]:
            return result["message"]["content"]
        raise AIError(_("ai.error.ollama_unrecognized", json.dumps(result)[:300]))

    def _ask_anthropic(self, prompt):
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        lang_instr = self._language_instruction()
        if self.system:
            body["system"] = lang_instr + "\n\n" + self.system
        else:
            body["system"] = lang_instr
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.key:
            headers["x-api-key"] = self.key
        result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))
        if "content" in result and result["content"]:
            for block in result["content"]:
                if block.get("type") == "text" or "text" in block:
                    text = block.get("text", "")
                    if text:
                        return text
        raise AIError(_("ai.error.anthropic_unrecognized", json.dumps(result)[:300]))

    def _ask_minimax_native(self, prompt):
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        lang_instr = self._language_instruction()
        full_system = lang_instr + "\n\n" + self.system if self.system else lang_instr
        body["messages"].insert(0, {"role": "system", "content": full_system})
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))
        return self._extract_openai(result)

    def _system_with_search_hint(self):
        base = self.system
        hint = (
            "You have access to a `web_search` tool. Use it whenever the user asks "
            "about current events, recent facts, prices, releases, or anything that "
            "may be newer than your training data. When you use it, cite the source "
            "URLs you got from the results."
        )
        if not base:
            return hint
        return base + "\n\n" + hint

    def _execute_web_search(self, arguments_json):
        if web_search is None:
            return "Web search is not available in this build."
        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except Exception:
            args = {}
        query = args.get("query", "")
        if not query:
            return "web_search: missing 'query' argument."
        try:
            results = web_search.search(
                query, max_results=self.search_max_results, timeout=self.timeout
            )
        except Exception as e:
            return _("ai.error.web_search_failed", str(e))
        return web_search.format_results(results)

    def _ask_with_tools(self, user_prompt, fmt):
        if fmt == "anthropic":
            return self._ask_with_tools_anthropic(user_prompt)
        return self._ask_with_tools_openai_family(user_prompt, fmt)

    def _ask_with_tools_openai_family(self, user_prompt, fmt):
        messages = []
        messages.append({"role": "system", "content": self._system_with_search_hint()})
        messages.append({"role": "user", "content": user_prompt})

        for _ in range(MAX_TOOL_ITERATIONS):
            body = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "tools": [WEB_SEARCH_TOOL_OPENAI],
                "tool_choice": "auto",
            }
            headers = {"Content-Type": "application/json"}
            if self.key:
                headers["Authorization"] = "Bearer " + self.key
            try:
                result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))
            except AIError:
                raise

            choice = None
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
            if choice is None:
                raise AIError(_("ai.error.unrecognized", json.dumps(result)[:300]))

            msg = choice.get("message", {}) or {}
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content") or ""

            if not tool_calls:
                return content

            asst = {"role": "assistant", "content": content if content else None}
            asst["tool_calls"] = []
            for tc in tool_calls:
                fn = tc.get("function", {}) or {}
                asst["tool_calls"].append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": fn.get("arguments", ""),
                    },
                })
            messages.append(asst)

            for tc in tool_calls:
                fn = tc.get("function", {}) or {}
                name = fn.get("name", "")
                args_json = fn.get("arguments", "")
                if name != "web_search":
                    out = _("ai.error.unsupported_tool", name)
                else:
                    out = self._execute_web_search(args_json)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": out,
                })

        return content if content else ""

    def _ask_with_tools_anthropic(self, user_prompt):
        messages = [{"role": "user", "content": user_prompt}]
        last_text = ""
        for _ in range(MAX_TOOL_ITERATIONS):
            body = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": self._system_with_search_hint(),
                "messages": messages,
                "tools": [WEB_SEARCH_TOOL_ANTHROPIC],
            }
            headers = {
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
            if self.key:
                headers["x-api-key"] = self.key
            result = self._post(self.url, headers, json.dumps(body).encode("utf-8"))

            content = result.get("content") or []
            stop_reason = result.get("stop_reason", "")
            text_parts = []
            tool_uses = []
            for block in content:
                btype = block.get("type")
                if btype == "text" or "text" in block:
                    t = block.get("text", "")
                    if t:
                        text_parts.append(t)
                elif btype == "tool_use":
                    tool_uses.append(block)

            last_text = "\n".join(text_parts).strip()

            if stop_reason != "tool_use" or not tool_uses:
                return last_text

            messages.append({"role": "assistant", "content": content})

            tool_results = []
            for tu in tool_uses:
                name = tu.get("name", "")
                tu_id = tu.get("id", "")
                input_obj = tu.get("input", {}) or {}
                if name != "web_search":
                    out = _("ai.error.unsupported_tool", name)
                else:
                    out = self._execute_web_search(json.dumps(input_obj))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": out,
                })
            messages.append({"role": "user", "content": tool_results})

        return last_text


if __name__ == "__main__":
    import sys
    import os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import config as _config
    cfg = _config.load()
    if not cfg.get("api_key"):
        print("ERROR: setea api_key en", _config.CONFIG_PATH)
        sys.exit(1)
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Decime 'hola' en una palabra"
    client = AIClient(cfg)
    try:
        out = client.ask(prompt)
        print(out)
    except AIError as e:
        print("ERROR:", e)
        sys.exit(1)
