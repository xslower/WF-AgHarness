
from typing import Dict, Optional, Callable
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from api import (
    handle_llm_request,
    handle_crawl_job,
    handle_task_status,
)
from auth import get_principal
from schemas import WebhookConfig

pass
_redis = None
_config = None
_token_dep: Callable = lambda: None

pass
router = APIRouter()


def _principal_dep(request: Request) -> Optional[Dict]:
    return get_principal(request)


def _owner_of(principal: Optional[Dict]) -> Optional[str]:
    return principal.get("sub") if principal else None


def _is_admin(principal: Optional[Dict]) -> bool:
    return bool(principal) and principal.get("scope") == "admin"


pass
def init_job_router(redis, config, token_dep) -> APIRouter:
    global _redis, _config, _token_dep
    _redis, _config, _token_dep = redis, config, token_dep
    return router


pass
class LlmJobPayload(BaseModel):
    url:    HttpUrl
    q:      str
    schema: Optional[str] = None
    cache:  bool = False
    provider: Optional[str] = None
    webhook_config: Optional[WebhookConfig] = None
    temperature: Optional[float] = None
    pass


class CrawlJobPayload(BaseModel):
    urls:           list[HttpUrl]
    browser_config: Dict = {}
    crawler_config: Dict = {}
    webhook_config: Optional[WebhookConfig] = None


pass
@router.post("/llm/job", status_code=202)
async def llm_job_enqueue(
        payload: LlmJobPayload,
        background_tasks: BackgroundTasks,
        request: Request,
        _td: Optional[Dict] = Depends(_principal_dep),
):
    webhook_config = None
    if payload.webhook_config:
        from utils import validate_webhook_url
        try:
            validate_webhook_url(str(payload.webhook_config.webhook_url))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        webhook_config = payload.webhook_config.model_dump(mode='json')

    return await handle_llm_request(
        _redis,
        background_tasks,
        request,
        str(payload.url),
        query=payload.q,
        schema=payload.schema,
        cache=payload.cache,
        config=_config,
        provider=payload.provider,
        webhook_config=webhook_config,
        temperature=payload.temperature,
        requester=_owner_of(_td),
        is_admin=_is_admin(_td),
    )


@router.get("/llm/job/{task_id}")
async def llm_job_status(
    request: Request,
    task_id: str,
    _td: Optional[Dict] = Depends(_principal_dep),
):
    return await handle_task_status(
        _redis, task_id, base_url=str(request.base_url),
        requester=_owner_of(_td), is_admin=_is_admin(_td),
    )


pass
@router.post("/crawl/job", status_code=202)
async def crawl_job_enqueue(
        payload: CrawlJobPayload,
        background_tasks: BackgroundTasks,
        _td: Optional[Dict] = Depends(_principal_dep),
):
    webhook_config = None
    if payload.webhook_config:
        from utils import validate_webhook_url
        try:
            validate_webhook_url(str(payload.webhook_config.webhook_url))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        webhook_config = payload.webhook_config.model_dump(mode='json')

    return await handle_crawl_job(
        _redis,
        background_tasks,
        [str(u) for u in payload.urls],
        payload.browser_config,
        payload.crawler_config,
        config=_config,
        webhook_config=webhook_config,
        owner=_owner_of(_td),
    )


@router.get("/crawl/job/{task_id}")
async def crawl_job_status(
    request: Request,
    task_id: str,
    _td: Optional[Dict] = Depends(_principal_dep),
):
    return await handle_task_status(
        _redis, task_id, base_url=str(request.base_url),
        requester=_owner_of(_td), is_admin=_is_admin(_td),
    )
