from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentTeam, CurrentTeamOwner, CurrentUser
from app.auth_repositories import TeamRepository
from app.auth_schemas import TeamCreate, TeamJoin, TeamMemberRead, TeamRead, TeamUpdate
from app.db import DatabaseUnavailable

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
async def list_teams(auth: CurrentUser) -> list[TeamRead]:
    return await TeamRepository().list_for_user(auth.user.id)


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(payload: TeamCreate, auth: CurrentUser) -> TeamRead:
    if not auth.user.profile_completed:
        raise HTTPException(status_code=409, detail="프로필 설정을 먼저 완료해 주세요.")
    try:
        return await TeamRepository().create(payload.name, auth.user.id)
    except (DatabaseUnavailable, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/join", response_model=TeamRead)
async def join_team(payload: TeamJoin, auth: CurrentUser) -> TeamRead:
    if not auth.user.profile_completed:
        raise HTTPException(status_code=409, detail="프로필 설정을 먼저 완료해 주세요.")
    team = await TeamRepository().join(payload.invite_code, auth.user.id)
    if team is None:
        raise HTTPException(status_code=404, detail="유효하지 않거나 만료된 초대 코드입니다.")
    return team


@router.get("/{team_id}/members", response_model=list[TeamMemberRead])
async def list_members(team_id: str, context: CurrentTeam) -> list[TeamMemberRead]:
    if team_id != context.team_id:
        raise HTTPException(status_code=403, detail="현재 팀과 요청한 팀이 다릅니다.")
    return await TeamRepository().list_members(team_id)


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(team_id: str, payload: TeamUpdate, context: CurrentTeamOwner) -> TeamRead:
    if team_id != context.team_id:
        raise HTTPException(status_code=403, detail="현재 팀과 요청한 팀이 다릅니다.")
    return await TeamRepository().update_name(team_id, payload.name)


@router.post("/{team_id}/invite-code/rotate", response_model=TeamRead)
async def rotate_invite_code(team_id: str, context: CurrentTeamOwner) -> TeamRead:
    if team_id != context.team_id:
        raise HTTPException(status_code=403, detail="현재 팀과 요청한 팀이 다릅니다.")
    try:
        return await TeamRepository().rotate_invite_code(team_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
