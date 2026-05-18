import openai
from typing import Dict, Any, Optional
from ..config import settings
from ..utils.logger import create_module_logger

log = create_module_logger("llm-client")

# LLM 厂商配置
LLM_PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": {
            "fast": "gpt-4o-mini",
            "standard": "gpt-4o",
            "premium": "gpt-4-turbo"
        }
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1",
        "models": {
            "fast": "claude-3-haiku-20240307",
            "standard": "claude-3-sonnet-20240229",
            "premium": "claude-3-opus-20240229"
        }
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {
            "fast": "qwen-turbo",
            "standard": "qwen-plus",
            "premium": "qwen-max"
        }
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": {
            "fast": "glm-4-flash",
            "standard": "glm-4",
            "premium": "glm-4-plus"
        }
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": {
            "fast": "deepseek-chat",
            "standard": "deepseek-chat",
            "premium": "deepseek-reasoner"
        }
    },
    "local": {
        "base_url": "http://localhost:11434/v1",
        "models": {
            "fast": "qwen2.5:7b",
            "standard": "qwen2.5:14b",
            "premium": "qwen2.5:72b"
        }
    }
}

def get_llm_config() -> Dict[str, Any]:
    """获取 LLM 配置"""
    provider = settings.LLM_PROVIDER
    model_level = settings.LLM_MODEL_LEVEL
    
    provider_config = LLM_PROVIDERS.get(provider)
    if not provider_config:
        raise ValueError(f"不支持的LLM厂商: {provider}，支持的厂商: {', '.join(LLM_PROVIDERS.keys())}")
    
    base_url = settings.LLM_BASE_URL or provider_config["base_url"]
    api_key = settings.LLM_API_KEY
    
    if not api_key:
        raise ValueError("缺少LLM_API_KEY或OPENAI_API_KEY环境变量")
    
    model = settings.LLM_MODEL or provider_config["models"].get(model_level, provider_config["models"]["fast"])
    
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "temperature": settings.LLM_TEMPERATURE
    }

def create_openai_client() -> openai.OpenAI:
    """创建 OpenAI 兼容客户端"""
    config = get_llm_config()
    return openai.OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"]
    )

async def llm_chat_completion(
    system_prompt: str,
    user_prompt: str,
    response_format: Optional[Dict[str, str]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """统一的 LLM 调用接口"""
    config = get_llm_config()
    client = create_openai_client()
    
    try:
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=response_format,
            temperature=temperature or config["temperature"],
            max_tokens=max_tokens or config["max_tokens"]
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM返回空内容")
        
        return content
    except Exception as e:
        log.error(f"LLM调用失败: {e}")
        raise

async def llm_json_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """JSON 格式输出的 LLM 调用"""
    import json
    
    content = await llm_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format={"type": "json_object"},
        temperature=temperature or 0.3
    )
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        log.error(f"JSON解析失败: {e}")
        raise

def get_llm_info() -> Dict[str, str]:
    """获取当前 LLM 配置信息"""
    config = get_llm_config()
    return {
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config["base_url"]
    }

def validate_llm_config() -> Dict[str, Any]:
    """验证 LLM 配置"""
    errors = []
    
    try:
        config = get_llm_config()
        if not config["api_key"]:
            errors.append("缺少LLM_API_KEY或OPENAI_API_KEY环境变量")
    except ValueError as e:
        errors.append(str(e))
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }