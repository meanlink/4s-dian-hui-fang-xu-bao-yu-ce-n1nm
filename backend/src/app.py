import json
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .db import db, one, all_rows
from .middleware import request_context
from .modeling import predict
from .security import current_user, make_token, require_roles

app = FastAPI(title="dealer-renewal-score")
app.middleware("http")(request_context)

class LoginIn(BaseModel):
    email: str
    password: str

class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: str = ""

class ScheduleIn(BaseModel):
    scheduled_for: str
    channel: str = Field(pattern="^(phone|wechat|sms)$")

class OutcomeIn(BaseModel):
    status: str = Field(pattern="^(contacted|declined|completed)$")
    note: str = ""


def audit(cur, user_id, action, entity_type, entity_id, detail=None):
    cur.execute("INSERT INTO audit_logs(user_id,action,entity_type,entity_id,detail) VALUES(%s,%s,%s,%s,%s)", (user_id, action, entity_type, entity_id, json.dumps(detail or {}, ensure_ascii=False)))


def owner_bundle(cur, owner_id):
    owner = one(cur, "SELECT * FROM owners WHERE id=%s", (owner_id,))
    events = all_rows(cur, "SELECT * FROM service_events WHERE owner_id=%s ORDER BY service_date DESC", (owner_id,))
    return owner, events

@app.get("/health")
def health():
    with db() as conn:
        with conn.cursor() as cur:
            one(cur, "SELECT 1")
    return {"status": "ok", "service": "dealer-renewal-score"}

@app.post("/api/auth/login")
def login(payload: LoginIn):
    with db() as conn:
        with conn.cursor() as cur:
            user = one(cur, "SELECT id,email,name,role,active FROM users WHERE email=%s AND password=%s", (payload.email, payload.password))
    if not user or not user["active"]:
        raise HTTPException(401, "账号或密码错误")
    return {"token": make_token(user), "user": user}

@app.get("/api/session")
def session(user=Depends(current_user)):
    return user

@app.get("/api/owners")
def owners(search: str = "", user=Depends(current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            term = f"%{search}%"
            rows = all_rows(cur, "SELECT o.*, l.score, l.status AS lead_status FROM owners o LEFT JOIN renewal_leads l ON l.owner_id=o.id WHERE o.name LIKE %s OR o.owner_code LIKE %s OR o.plate_no LIKE %s ORDER BY o.id", (term, term, term))
    return rows

@app.get("/api/owners/{owner_id}")
def owner_detail(owner_id: int, user=Depends(current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            owner, events = owner_bundle(cur, owner_id)
    if not owner:
        raise HTTPException(404, "车主不存在")
    return {"owner": owner, "events": events}

@app.get("/api/service-events")
def service_events(user=Depends(current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            return all_rows(cur, "SELECT s.*, o.name AS owner_name, o.plate_no FROM service_events s JOIN owners o ON o.id=s.owner_id ORDER BY s.service_date DESC, s.id DESC")

@app.get("/api/leads")
def leads(user=Depends(current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            rows = all_rows(cur, "SELECT l.*, o.owner_code, o.name AS owner_name, o.phone, o.vehicle_model, o.plate_no, o.policy_expires, o.contact_status FROM renewal_leads l JOIN owners o ON o.id=l.owner_id ORDER BY l.score DESC, l.id")
    for row in rows:
        row["feature_contrib"] = json.loads(row["feature_contrib"] or "[]")
    return rows

@app.get("/api/followups")
def followups(user=Depends(current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            return all_rows(cur, "SELECT f.*, o.name AS owner_name, o.phone, o.plate_no, o.vehicle_model, u.name AS assignee_name, l.score, l.status AS lead_status FROM followups f JOIN owners o ON o.id=f.owner_id JOIN users u ON u.id=f.assignee_id JOIN renewal_leads l ON l.id=f.lead_id ORDER BY f.scheduled_for, f.id")

@app.get("/api/dashboard")
def dashboard(user=Depends(current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            stats = one(cur, "SELECT COUNT(*) AS owners, SUM(policy_expires >= CURDATE()) AS active_policies, SUM(contact_status='rejected') AS frozen_contacts FROM owners")
            leads_stats = all_rows(cur, "SELECT status, COUNT(*) AS count FROM renewal_leads GROUP BY status")
            upcoming = all_rows(cur, "SELECT f.id, o.name AS owner_name, f.scheduled_for, f.status, l.score FROM followups f JOIN owners o ON o.id=f.owner_id JOIN renewal_leads l ON l.id=f.lead_id WHERE f.scheduled_for >= NOW() AND f.status='scheduled' ORDER BY f.scheduled_for LIMIT 5")
    return {"stats": stats, "leads": leads_stats, "upcoming": upcoming}

@app.post("/api/predictions/run")
def run_predictions(user=Depends(require_roles("manager", "admin"))):
    today = date(2026, 11, 21)
    count = 0
    with db() as conn:
        with conn.cursor() as cur:
            owners_rows = all_rows(cur, "SELECT * FROM owners")
            for owner in owners_rows:
                events = all_rows(cur, "SELECT * FROM service_events WHERE owner_id=%s", (owner["id"],))
                existing = one(cur, "SELECT id FROM renewal_leads WHERE owner_id=%s", (owner["id"],))
                if owner["policy_expires"] < today:
                    status = "expired"
                    score = 0
                    explanation = []
                elif owner["contact_status"] == "rejected":
                    status = "frozen"
                    score, explanation = predict(owner, events)
                else:
                    status = "predicted"
                    score, explanation = predict(owner, events)
                data = json.dumps(explanation, ensure_ascii=False)
                if existing:
                    cur.execute("UPDATE renewal_leads SET score=%s,status=%s,last_prediction_at=NOW(),feature_contrib=%s WHERE owner_id=%s", (score, status, data, owner["id"]))
                    lead_id = existing["id"]
                else:
                    cur.execute("INSERT INTO renewal_leads(owner_id,score,status,last_prediction_at,feature_contrib) VALUES(%s,%s,%s,NOW(),%s)", (owner["id"], score, status, data))
                    lead_id = cur.lastrowid
                audit(cur, user["id"], "run_prediction", "renewal_lead", lead_id, {"status": status, "score": score})
                count += 1
    return {"updated": count, "message": "预测已完成，过期保单已排除，拒绝联系客户已冻结触达"}

@app.post("/api/leads/{lead_id}/review")
def review_lead(lead_id: int, payload: ReviewIn, user=Depends(require_roles("manager", "admin"))):
    with db() as conn:
        with conn.cursor() as cur:
            lead = one(cur, "SELECT l.*, o.policy_expires, o.contact_status, o.name FROM renewal_leads l JOIN owners o ON o.id=l.owner_id WHERE l.id=%s FOR UPDATE", (lead_id,))
            if not lead:
                raise HTTPException(404, "线索不存在")
            if lead["status"] != "predicted":
                raise HTTPException(409, "只有预测中的线索可以审核")
            if lead["policy_expires"] < date(2026, 11, 21):
                raise HTTPException(409, "保单已过期，不能审核触达")
            if lead["contact_status"] == "rejected":
                raise HTTPException(409, "客户已拒绝联系，触达已冻结")
            status = "reviewed" if payload.decision == "approve" else "rejected"
            cur.execute("UPDATE renewal_leads SET status=%s,reviewed_by=%s,reviewed_at=NOW(),review_note=%s WHERE id=%s", (status, user["id"], payload.note, lead_id))
            audit(cur, user["id"], "review_lead", "renewal_lead", lead_id, {"decision": payload.decision, "note": payload.note})
    return {"id": lead_id, "status": status}

@app.post("/api/leads/{lead_id}/schedule")
def schedule(lead_id: int, payload: ScheduleIn, user=Depends(require_roles("advisor", "manager", "admin"))):
    try:
        scheduled = datetime.fromisoformat(payload.scheduled_for)
    except ValueError:
        raise HTTPException(422, "回访时间格式错误")
    with db() as conn:
        with conn.cursor() as cur:
            lead = one(cur, "SELECT l.*, o.policy_expires, o.contact_status, o.preferred_channel FROM renewal_leads l JOIN owners o ON o.id=l.owner_id WHERE l.id=%s FOR UPDATE", (lead_id,))
            if not lead:
                raise HTTPException(404, "线索不存在")
            if lead["status"] != "reviewed":
                raise HTTPException(409, "只有审核通过的线索可以安排回访")
            if lead["policy_expires"] < date(2026, 11, 21):
                raise HTTPException(409, "保单已过期，不能入队")
            if lead["contact_status"] == "rejected":
                raise HTTPException(409, "客户已拒绝联系，触达已冻结")
            cur.execute("INSERT INTO followups(lead_id,owner_id,assignee_id,scheduled_for,channel) VALUES(%s,%s,%s,%s,%s)", (lead_id, lead["owner_id"], user["id"], scheduled, payload.channel))
            followup_id = cur.lastrowid
            cur.execute("UPDATE renewal_leads SET status='queued' WHERE id=%s", (lead_id,))
            audit(cur, user["id"], "schedule_followup", "followup", followup_id, {"lead_id": lead_id, "channel": payload.channel})
    return {"id": followup_id, "status": "scheduled"}

@app.post("/api/followups/{followup_id}/outcome")
def outcome(followup_id: int, payload: OutcomeIn, user=Depends(require_roles("advisor", "manager", "admin"))):
    with db() as conn:
        with conn.cursor() as cur:
            item = one(cur, "SELECT * FROM followups WHERE id=%s FOR UPDATE", (followup_id,))
            if not item:
                raise HTTPException(404, "回访任务不存在")
            cur.execute("UPDATE followups SET status=%s,outcome_note=%s WHERE id=%s", (payload.status, payload.note, followup_id))
            if payload.status == "declined":
                cur.execute("UPDATE owners SET contact_status='rejected' WHERE id=%s", (item["owner_id"],))
                cur.execute("UPDATE renewal_leads SET status='frozen' WHERE owner_id=%s", (item["owner_id"],))
            audit(cur, user["id"], "followup_outcome", "followup", followup_id, {"status": payload.status})
    return {"id": followup_id, "status": payload.status}

@app.post("/api/owners/{owner_id}/reject-contact")
def reject_contact(owner_id: int, user=Depends(require_roles("manager", "admin"))):
    with db() as conn:
        with conn.cursor() as cur:
            owner = one(cur, "SELECT id FROM owners WHERE id=%s FOR UPDATE", (owner_id,))
            if not owner:
                raise HTTPException(404, "车主不存在")
            cur.execute("UPDATE owners SET contact_status='rejected' WHERE id=%s", (owner_id,))
            cur.execute("UPDATE renewal_leads SET status='frozen' WHERE owner_id=%s AND status IN ('predicted','reviewed')", (owner_id,))
            audit(cur, user["id"], "freeze_contact", "owner", owner_id, {"reason": "customer_rejected"})
    return {"owner_id": owner_id, "contact_status": "rejected", "message": "已冻结预测触达"}

@app.get("/api/audit")
def audit_logs(user=Depends(require_roles("admin"))):
    with db() as conn:
        with conn.cursor() as cur:
            return all_rows(cur, "SELECT a.*, u.name AS user_name FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 80")
