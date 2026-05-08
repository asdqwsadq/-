import json
import urllib.error
import urllib.request


def chat_completion(api_key: str, body: dict) -> str:
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek 调用失败: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"DeepSeek 调用异常: {exc}") from exc

    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("DeepSeek 返回内容为空")
    return content.strip()
