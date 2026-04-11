#!/usr/bin/env python3
# =====================================================
# AI外语学习系统 - 主应用入口
# 版本: 1.0.0
# 描述: FastAPI主应用，整合所有API路由
# =====================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import vocabulary_router, search_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时：
    1. 连接数据库
    2. 连接Redis
    3. 连接Elasticsearch
    4. 初始化索引
    
    关闭时：
    1. 关闭所有连接
    """
    logger.info("Starting up AI Language Learning API...")
    
    # 启动时的初始化
    # TODO: 初始化数据库连接池
    # TODO: 初始化Redis连接
    # TODO: 初始化Elasticsearch连接
    
    yield
    
    # 关闭时的清理
    logger.info("Shutting down AI Language Learning API...")
    # TODO: 关闭所有连接


# 创建FastAPI应用
app = FastAPI(
    title="AI外语学习系统 - 数据库搜索层API",
    description="""
    提供词汇搜索、同义词检索、全文检索等功能。
    
    ## 功能模块
    
    ### 词汇管理
    - 词汇CRUD操作
    - 批量导入导出
    - 标签管理
    
    ### 搜索功能
    - 全文搜索（Elasticsearch）
    - 模糊搜索（拼写纠错）
    - 同义词扩展搜索
    - 自动完成建议
    
    ### 多层搜索策略
    1. Redis缓存层 - 快速响应热点查询
    2. Elasticsearch层 - 全文检索、模糊搜索
    3. PostgreSQL层 - 精确查询、兜底查询
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查端点
@app.get("/health", tags=["health"])
async def health_check():
    """
    健康检查端点
    
    返回服务状态和各组件连接状态
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "api": "up",
            "postgresql": "unknown",  # TODO: 实际检查
            "redis": "unknown",       # TODO: 实际检查
            "elasticsearch": "unknown"  # TODO: 实际检查
        }
    }


# 根路径
@app.get("/", tags=["root"])
async def root():
    """
    根路径 - API信息
    """
    return {
        "name": "AI外语学习系统 - 数据库搜索层API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }


# 注册路由
app.include_router(vocabulary_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理
    """
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if app.debug else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
