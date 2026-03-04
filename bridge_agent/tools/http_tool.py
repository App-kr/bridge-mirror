"""HTTP request tool for API testing."""

import json

from .base import BaseTool, ToolResult


class HTTPTool(BaseTool):
    """Make HTTP requests for API testing."""

    def name(self) -> str:
        return "http_request"

    def description(self) -> str:
        return "Make HTTP requests (GET, POST, PUT, DELETE) for testing APIs."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method.",
                },
                "url": {"type": "string", "description": "Full URL to request."},
                "headers": {
                    "type": "object",
                    "description": "Request headers as key-value pairs.",
                    "default": {},
                },
                "body": {"type": "string", "description": "Request body (JSON string)."},
                "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 30},
            },
            "required": ["method", "url"],
        }

    def execute(self, method: str = "GET", url: str = "",
                headers: dict | None = None, body: str = "",
                timeout: int = 30, **kwargs) -> ToolResult:
        if not url:
            return ToolResult(success=False, output="", error="No URL provided")

        try:
            import httpx
        except ImportError:
            return ToolResult(success=False, output="", error="httpx not installed. Run: pip install httpx")

        try:
            req_headers = headers or {}
            req_body = None

            if body:
                try:
                    req_body = json.loads(body)
                    if "Content-Type" not in req_headers:
                        req_headers["Content-Type"] = "application/json"
                except json.JSONDecodeError:
                    req_body = body

            with httpx.Client(timeout=timeout) as client:
                if isinstance(req_body, dict):
                    response = client.request(method, url, headers=req_headers, json=req_body)
                elif req_body:
                    response = client.request(method, url, headers=req_headers, content=req_body)
                else:
                    response = client.request(method, url, headers=req_headers)

            # Format response
            lines = [
                f"HTTP {response.status_code} {response.reason_phrase}",
                "",
            ]
            # Response headers (selected)
            for h in ["content-type", "content-length", "x-request-id"]:
                if h in response.headers:
                    lines.append(f"{h}: {response.headers[h]}")
            lines.append("")

            # Body
            try:
                body_json = response.json()
                lines.append(json.dumps(body_json, indent=2, ensure_ascii=False)[:10000])
            except Exception:
                lines.append(response.text[:10000])

            return ToolResult(
                success=200 <= response.status_code < 400,
                output="\n".join(lines),
            )
        except httpx.TimeoutException:
            return ToolResult(success=False, output="", error=f"Request timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
