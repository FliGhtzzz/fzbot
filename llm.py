import json
import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 載入 .env 環境變數
load_dotenv()
nvtoken = os.getenv("NV_TOKEN")

# 全域初始化 NVIDIA AsyncOpenAI Client
client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=nvtoken
)

# RPM 限流：每分鐘最多 40 個請求
class RateLimiter:
    """滑動窗口 rate limiter，限制每分鐘最多 N 個請求"""
    def __init__(self, max_per_minute: int = 40):
        self.max_per_minute = max_per_minute
        self.requests: list[float] = []  # 儲存每次請求的時間戳
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """取得許可，如有需要則等待。返回需要等待的秒數"""
        async with self._lock:
            now = asyncio.get_event_loop().time()

            # 清理超過 60 秒的舊請求
            self.requests = [t for t in self.requests if now - t < 60]

            # 如果已達上限，等待一段時間
            if len(self.requests) >= self.max_per_minute:
                oldest = self.requests[0]
                wait_time = 60 - (now - oldest) + 0.1  # 多加 0.1 秒確保安全
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # 重新檢查並清理
                    now = asyncio.get_event_loop().time()
                    self.requests = [t for t in self.requests if now - t < 60]

            # 記錄這次請求
            self.requests.append(asyncio.get_event_loop().time())
            return 0

# 全域 rate limiter 實例
rate_limiter = RateLimiter(max_per_minute=40)

async def call_llm_api(question: str, use_rate_limit: bool = True, max_tokens: int = 1024) -> str:
    """
    呼叫 LLM API，並套用 RPM 限制

    Args:
        question: 要傳給 LLM 的問題/提示
        use_rate_limit: 是否啟用 rate limiting（預設 True）
        max_tokens: 最大回應 token 數（預設 1024）

    Returns:
        LLM 的回覆文字，或錯誤訊息
    """
    try:
        # 先取得 rate limit許可
        if use_rate_limit:
            await rate_limiter.acquire()

        completion = await client.chat.completions.create(
            model="moonshotai/kimi-k2.6",
            messages=[
                {"role": "user", "content": question}
            ],
            temperature=0.5,
            top_p=0.7,
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error calling LLM API: {str(e)}"
    