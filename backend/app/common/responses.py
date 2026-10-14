import time

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def payload(data=None, message="操作成功", code=200):
    return {"code": code, "message": message, "data": data,
            "timestamp": int(time.time())}


def error_response(status: int, message: str, request_id: str, data=None):
    return JSONResponse(status_code=status,
                        content=jsonable_encoder(payload(data, message, status)),
                        headers={"X-Request-ID": request_id})
