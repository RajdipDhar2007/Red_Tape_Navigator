"""Teams. A workspace groups people (a family business, a CA firm, a CSC centre). Sessions stay private to their owner until the owner
shares one into a workspace; every member of that workspace can then work on it. Invitations are links the inviter shares
themselves: this server never e-mails or messages anyone on a user's behalf."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit
from app.db.models import NavSession, User, Workspace, WorkspaceInvite, WorkspaceMember
from app.db.session import get_db

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
MAX_MEMBERS = 50
MAX_WORKSPACES_PER_USER = 10
INVITE_DAYS = 7
MANAGERS = ("owner", "admin")


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class InviteIn(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member)$")


class AcceptIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class RoleIn(BaseModel):
    role: str = Field(pattern="^(admin|member)$")


class ShareIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=32)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)


async def _membership(db: AsyncSession, wid: str, uid: str) -> WorkspaceMember | None:
    return await db.get(WorkspaceMember, (wid, uid))


async def _need_member(db: AsyncSession, wid: str, user: User) -> WorkspaceMember:
    m = await _membership(db, wid, user.id)
    if m is None:
        raise HTTPException(404, "Workspace not found")  # not a member: do not reveal that it exists
    return m


async def _need_manager(db: AsyncSession, wid: str, user: User) -> WorkspaceMember:
    m = await _need_member(db, wid, user)
    if m.role not in MANAGERS:
        raise HTTPException(403, "Only an owner or admin can do this")
    return m


@router.post("", status_code=201)
async def create_workspace(body: WorkspaceIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    owned = (await db.execute(select(func.count()).select_from(WorkspaceMember).where(
        WorkspaceMember.user_id == user.id, WorkspaceMember.role == "owner"))).scalar_one()
    if owned >= MAX_WORKSPACES_PER_USER:
        raise HTTPException(409, f"You can own at most {MAX_WORKSPACES_PER_USER} workspaces")
    ws = Workspace(name=body.name.strip(), created_by=user.id)
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner"))
    await db.commit()
    await audit.record(db, user.id, "workspace.created", {"workspace": ws.id})
    return {"id": ws.id, "name": ws.name, "role": "owner"}


@router.get("")
async def my_workspaces(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Workspace, WorkspaceMember.role).join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                             .where(WorkspaceMember.user_id == user.id).order_by(Workspace.created_at))).all()
    return [{"id": w.id, "name": w.name, "role": role} for w, role in rows]


@router.get("/{wid}")
async def workspace_detail(wid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    me = await _need_member(db, wid, user)
    ws = await db.get(Workspace, wid)
    if ws is None:
        raise HTTPException(404, "Workspace not found")
    members = (await db.execute(select(WorkspaceMember, User.email).join(User, User.id == WorkspaceMember.user_id)
                                .where(WorkspaceMember.workspace_id == wid).order_by(WorkspaceMember.joined_at))).all()
    return {"id": ws.id, "name": ws.name, "your_role": me.role,
            "members": [{"user_id": m.user_id, "email": email, "role": m.role} for m, email in members]}


@router.delete("/{wid}", status_code=204)
async def delete_workspace(wid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    me = await _need_member(db, wid, user)
    if me.role != "owner":
        raise HTTPException(403, "Only the owner can delete a workspace")
    for ns in (await db.execute(select(NavSession).where(NavSession.workspace_id == wid))).scalars():
        ns.workspace_id = None  # sessions go back to being private to their owners; none is deleted
    await db.execute(delete(WorkspaceInvite).where(WorkspaceInvite.workspace_id == wid))
    await db.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == wid))
    await db.execute(delete(Workspace).where(Workspace.id == wid))
    await db.commit()
    await audit.record(db, user.id, "workspace.deleted", {"workspace": wid})


@router.post("/{wid}/invites", status_code=201)
async def create_invite(wid: str, body: InviteIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _need_manager(db, wid, user)
    if user.email_verified_at is None:
        raise HTTPException(403, {"code": "email_not_verified", "message": "Confirm your email address before inviting people."})
    count = (await db.execute(select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == wid))).scalar_one()
    if count >= MAX_MEMBERS:
        raise HTTPException(409, f"A workspace can have at most {MAX_MEMBERS} members")
    email = body.email.lower()
    token = secrets.token_urlsafe(32)
    # a newer invite for the same address replaces the older unused one
    await db.execute(delete(WorkspaceInvite).where(WorkspaceInvite.workspace_id == wid, WorkspaceInvite.email == email,
                                                   WorkspaceInvite.accepted_at.is_(None)))
    inv = WorkspaceInvite(workspace_id=wid, email=email, role=body.role, token_hash=_hash(token), created_by=user.id,
                          expires_at=datetime.now(UTC) + timedelta(days=INVITE_DAYS))
    db.add(inv)
    await db.commit()
    await audit.record(db, user.id, "workspace.invite_created", {"workspace": wid, "role": body.role})
    # The token is shown once. The inviter sends the link to the invitee; nothing is sent from here.
    return {"id": inv.id, "email": email, "role": body.role, "expires_at": inv.expires_at.isoformat(), "token": token,
            "accept_path": f"/invite?token={token}"}


@router.get("/{wid}/invites")
async def list_invites(wid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _need_manager(db, wid, user)
    rows = (await db.execute(select(WorkspaceInvite).where(WorkspaceInvite.workspace_id == wid, WorkspaceInvite.accepted_at.is_(None))
                             .order_by(WorkspaceInvite.created_at))).scalars().all()
    now = datetime.now(UTC)
    return [{"id": r.id, "email": r.email, "role": r.role, "expires_at": r.expires_at.isoformat(), "expired": _aware(r.expires_at) < now} for r in rows]


@router.delete("/{wid}/invites/{iid}", status_code=204)
async def revoke_invite(wid: str, iid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _need_manager(db, wid, user)
    inv = await db.get(WorkspaceInvite, iid)
    if inv is None or inv.workspace_id != wid:
        raise HTTPException(404, "Unknown invite")
    await db.delete(inv)
    await db.commit()
    await audit.record(db, user.id, "workspace.invite_revoked", {"workspace": wid})


@router.post("/invites/accept")
async def accept_invite(body: AcceptIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    bad = HTTPException(400, "This invitation is invalid, expired or was sent to a different email address")
    inv = (await db.execute(select(WorkspaceInvite).where(WorkspaceInvite.token_hash == _hash(body.token)))).scalar_one_or_none()
    if inv is None or inv.accepted_at is not None or _aware(inv.expires_at) < datetime.now(UTC) or inv.email != user.email.lower():
        raise bad
    if user.email_verified_at is None:  # the invite is bound to an address, so the address must be proven to be theirs
        raise HTTPException(403, {"code": "email_not_verified", "message": "Confirm your email address, then open the invitation again."})
    if await _membership(db, inv.workspace_id, user.id) is None:
        db.add(WorkspaceMember(workspace_id=inv.workspace_id, user_id=user.id, role=inv.role))
    inv.accepted_at = datetime.now(UTC)
    await db.commit()
    await audit.record(db, user.id, "workspace.joined", {"workspace": inv.workspace_id, "role": inv.role})
    ws = await db.get(Workspace, inv.workspace_id)
    if ws is None:
        raise HTTPException(404, "Workspace not found")
    return {"id": ws.id, "name": ws.name, "role": inv.role}


@router.patch("/{wid}/members/{uid}")
async def change_role(wid: str, uid: str, body: RoleIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    me = await _need_member(db, wid, user)
    if me.role != "owner":
        raise HTTPException(403, "Only the owner can change roles")
    target = await _membership(db, wid, uid)
    if target is None:
        raise HTTPException(404, "Not a member")
    if target.role == "owner":
        raise HTTPException(409, "The owner's role cannot be changed")
    target.role = body.role
    await db.commit()
    await audit.record(db, user.id, "workspace.role_changed", {"workspace": wid, "role": body.role})
    return {"user_id": uid, "role": body.role}


@router.delete("/{wid}/members/{uid}", status_code=204)
async def remove_member(wid: str, uid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    me = await _need_member(db, wid, user)
    target = await _membership(db, wid, uid)
    if target is None:
        raise HTTPException(404, "Not a member")
    if target.role == "owner":
        raise HTTPException(409, "The owner cannot leave or be removed; delete the workspace instead")
    if uid != user.id and not (me.role == "owner" or (me.role == "admin" and target.role == "member")):
        raise HTTPException(403, "You cannot remove this member")
    for ns in (await db.execute(select(NavSession).where(NavSession.workspace_id == wid, NavSession.user_id == uid))).scalars():
        ns.workspace_id = None  # their sessions stop being shared; they are theirs, not the team's
    await db.delete(target)
    await db.commit()
    await audit.record(db, user.id, "workspace.member_removed", {"workspace": wid, "self": uid == user.id})


@router.get("/{wid}/sessions")
async def workspace_sessions(wid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _need_member(db, wid, user)
    rows = (await db.execute(select(NavSession, User.email).join(User, User.id == NavSession.user_id)
                             .where(NavSession.workspace_id == wid).order_by(NavSession.created_at.desc()).limit(100))).all()
    return [{"id": s.id, "goal": s.goal, "owner": email, "created_at": s.created_at.isoformat(), "reviewed": s.reviewed_at is not None,
             "activity": (s.parsed or {}).get("activity"), "city": (s.parsed or {}).get("city")} for s, email in rows]


@router.post("/{wid}/sessions", status_code=201)
async def share_session(wid: str, body: ShareIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _need_member(db, wid, user)
    ns = await db.get(NavSession, body.session_id)
    if ns is None or ns.user_id != user.id:
        raise HTTPException(404, "Session not found")  # only the owner can share their own session
    ns.workspace_id = wid
    await db.commit()
    await audit.record(db, user.id, "workspace.session_shared", {"workspace": wid}, ns.id)
    return {"session_id": ns.id, "workspace_id": wid}


@router.delete("/{wid}/sessions/{sid}", status_code=204)
async def unshare_session(wid: str, sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    me = await _need_member(db, wid, user)
    ns = await db.get(NavSession, sid)
    if ns is None or ns.workspace_id != wid:
        raise HTTPException(404, "Session not found")
    if ns.user_id != user.id and me.role not in MANAGERS:
        raise HTTPException(403, "Only the session owner or a workspace admin can stop sharing it")
    ns.workspace_id = None
    await db.commit()
    await audit.record(db, user.id, "workspace.session_unshared", {"workspace": wid}, ns.id)
