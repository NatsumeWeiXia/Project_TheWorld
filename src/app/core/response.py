from fastapi import Request


def build_response(request: Request, data=None, code: int = 0, message: str = "ok"):
    return {
        "code": code,
        "message": message,
        "data": data if data is not None else {},
        "trace_id": getattr(request.state, "trace_id", ""),
    }
