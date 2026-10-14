import asyncio
import subprocess

import httpx

from app.core.config import PROJECT_ROOT


async def test_real_start_script_ignores_forged_proxy_ip(authenticated_client):
    start = PROJECT_ROOT / "scripts" / "start.ps1"
    stop = PROJECT_ROOT / "scripts" / "stop.ps1"
    await asyncio.to_thread(
        subprocess.run,
        ["pwsh", "-NoProfile", "-File", str(start), "-TestMode"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    try:
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8001", timeout=5, headers={"Origin": "http://127.0.0.1:5174"}
        ) as client:
            for _ in range(50):
                try:
                    if (await client.get("/api/v1/health/ready")).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
            responses = []
            for attempt in range(6):
                result = await client.post(
                    "/api/v1/auth/login",
                    headers={"X-Forwarded-For": f"198.51.100.{attempt + 1}"},
                    json={"username": "tester", "password": "wrong-password"},
                )
                responses.append(result.status_code)
            assert responses == [401, 401, 401, 401, 401, 429]
    finally:
        await asyncio.to_thread(
            subprocess.run,
            ["pwsh", "-NoProfile", "-File", str(stop), "-TestMode"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
