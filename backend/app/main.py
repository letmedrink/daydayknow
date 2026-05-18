from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import capture, daily_doc, batch, star_map, terms
from .config import settings

app = FastAPI(
    title="DayDayKnow API",
    description="知识捕获与学习 API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(capture.router)
app.include_router(daily_doc.router)
app.include_router(batch.router)
app.include_router(star_map.router)
app.include_router(terms.router)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "DayDayKnow API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "mock_mode": settings.MOCK_MODE,
        "timestamp": "2024-01-01T00:00:00Z"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)