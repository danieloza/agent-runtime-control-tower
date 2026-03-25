from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse

from agent_runtime_control_tower.config import redis_url
from agent_runtime_control_tower.repository import ControlTowerRepository, SQLiteRepository, repository
from agent_runtime_control_tower.schemas import (
    AgentOut,
    ApprovalDecisionIn,
    ApprovalOut,
    HealthOut,
    IncidentOut,
    MCPServerOut,
    OrganizationOut,
    PolicyOut,
    ReplayRequestIn,
    RunOut,
    RunRequestIn,
    RunStateOut,
    ToolTraceOut,
    UserOut,
)
from agent_runtime_control_tower.services import AuthContext, RuntimeTowerService
from agent_runtime_control_tower.state import RuntimeStateStore, build_runtime_state_store


state_store = build_runtime_state_store(redis_url())


def get_repository() -> ControlTowerRepository:
    return repository


def get_state_store() -> RuntimeStateStore:
    return state_store


def get_service(
    repo: ControlTowerRepository = Depends(get_repository),
    runtime_state: RuntimeStateStore = Depends(get_state_store),
) -> RuntimeTowerService:
    return RuntimeTowerService(repo, runtime_state)


def get_current_auth(
    x_api_key: str | None = Header(default=None),
    service: RuntimeTowerService = Depends(get_service),
) -> AuthContext:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header.")
    auth = service.build_auth_context(x_api_key)
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
    return auth


def create_app(repo: SQLiteRepository | None = None, runtime_state: RuntimeStateStore | None = None) -> FastAPI:
    app = FastAPI(title="Agent Runtime Control Tower", version="0.1.0")

    if repo is not None:
        app.dependency_overrides[get_repository] = lambda: repo
    if runtime_state is not None:
        app.dependency_overrides[get_state_store] = lambda: runtime_state

    dashboard_path = Path(__file__).with_name("dashboard.html")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(dashboard_path)

    @app.get("/dashboard", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(dashboard_path)

    @app.get("/health", response_model=HealthOut)
    def health(service: RuntimeTowerService = Depends(get_service)) -> HealthOut:
        return HealthOut(**service.health_snapshot())

    @app.get("/me", response_model=UserOut)
    def me(auth: AuthContext = Depends(get_current_auth)) -> UserOut:
        return UserOut(**asdict(auth.user))

    @app.get("/organizations", response_model=list[OrganizationOut])
    def organizations(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[OrganizationOut]:
        return [OrganizationOut(**asdict(item)) for item in service.list_organizations(auth)]

    @app.get("/mcp-servers", response_model=list[MCPServerOut])
    def mcp_servers(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[MCPServerOut]:
        return [MCPServerOut(**asdict(item)) for item in service.list_mcp_servers(auth)]

    @app.get("/agents", response_model=list[AgentOut])
    def agents(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[AgentOut]:
        return [AgentOut(**asdict(item)) for item in service.list_agents(auth)]

    @app.get("/policies", response_model=list[PolicyOut])
    def policies(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[PolicyOut]:
        return [PolicyOut(**asdict(item)) for item in service.list_policies(auth)]

    @app.get("/runs", response_model=list[RunOut])
    def runs(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[RunOut]:
        return [RunOut(**asdict(item)) for item in service.list_runs(auth)]

    @app.post("/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
    def request_run(
        payload: RunRequestIn,
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> RunOut:
        try:
            run = service.request_run(auth, **payload.model_dump())
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return RunOut(**asdict(run))

    @app.get("/runs/{run_id}/traces", response_model=list[ToolTraceOut])
    def run_traces(
        run_id: str,
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[ToolTraceOut]:
        try:
            traces = service.get_run_traces(auth, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return [ToolTraceOut(**asdict(item)) for item in traces]

    @app.get("/runs/{run_id}/state", response_model=RunStateOut)
    def run_state(
        run_id: str,
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> RunStateOut:
        try:
            payload = service.get_run_state(auth, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return RunStateOut(**payload)

    @app.post("/runs/{run_id}/replay", response_model=RunOut, status_code=status.HTTP_201_CREATED)
    def replay_run(
        run_id: str,
        payload: ReplayRequestIn,
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> RunOut:
        try:
            run = service.replay_run(auth, run_id, **payload.model_dump())
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return RunOut(**asdict(run))

    @app.get("/approvals", response_model=list[ApprovalOut])
    def approvals(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[ApprovalOut]:
        return [ApprovalOut(**asdict(item)) for item in service.list_pending_approvals(auth)]

    @app.post("/approvals/{approval_id}/decision", response_model=ApprovalOut)
    def approval_decision(
        approval_id: str,
        payload: ApprovalDecisionIn,
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> ApprovalOut:
        try:
            approval = service.decide_approval(auth, approval_id, payload.decision)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return ApprovalOut(**asdict(approval))

    @app.get("/incidents", response_model=list[IncidentOut])
    def incidents(
        auth: AuthContext = Depends(get_current_auth),
        service: RuntimeTowerService = Depends(get_service),
    ) -> list[IncidentOut]:
        return [IncidentOut(**asdict(item)) for item in service.list_incidents(auth)]

    return app


app = create_app()
