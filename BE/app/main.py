import os
import time
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
load_dotenv()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"]      = os.environ.get("GCP_PROJECT_ID", "")
os.environ["GOOGLE_CLOUD_LOCATION"]     = os.environ.get("GCP_REGION", "us-central1")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

from app.router.auth_router        import router as auth_router
from app.router.chat_router        import router as chat_router
from app.router.appointment_router import router as appointment_router
from app.router.dashboard_router   import router as dashboard_router

from app.fhir.bootstrap                    import load_fhir_repository
from app.services.fhir_schedule_service    import FHIRScheduleService
from app.services.fhir_appointment_service import FHIRAppointmentService
from app.services.appointment_service      import AppointmentService
from app.services.memory_service           import load_member_memory
from app.services.calendar_service         import check_provider_availability

logger = logging.getLogger("app")

app = FastAPI(title="Provider Search Agentic Platform", version="6.0.0")

_cors_origins = os.getenv("CORS_ORIGINS", "*")
_allow_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    ms       = (time.perf_counter() - start) * 1000
    logger.info("%s %s  →  %d  (%.0fms)", request.method, request.url.path, response.status_code, ms)
    return response

# ── FHIR in-memory provider directory ────────────────────────────────────────
repo                 = load_fhir_repository()
schedule_service     = FHIRScheduleService(repo)
appointment_fhir_svc = FHIRAppointmentService(repo)
appointment_service  = AppointmentService(
    schedule_service   = schedule_service,
    appointment_service= appointment_fhir_svc,
)
app.state.fhir_repo           = repo
app.state.appointment_service = appointment_service

# ── FastAPI routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(appointment_router)
app.include_router(dashboard_router)

# ── Memory endpoint (frontend calls /memory/{member_id}) ─────────────────────
@app.get("/memory/{member_id}")
def get_memory(member_id: str):
    return load_member_memory(member_id)

# ── Availability endpoint (frontend calls /availability) ─────────────────────
@app.post("/availability")
async def get_availability(request: Request):
    body = await request.json()
    npi               = body.get("npi", "")
    provider_name     = body.get("provider_name", "")
    city              = body.get("city", "")
    consultation_mode = body.get("consultation_mode", "Both")
    selected_date     = body.get("selected_date", "")

    if not npi:
        return JSONResponse({"error": "npi is required"}, status_code=400)

    result = check_provider_availability(
        npi=npi,
        provider_name=provider_name,
        city=city,
        consultation_mode=consultation_mode,
        appointment_date=selected_date,
    )
    # Flatten slots for frontend format
    all_slots = [
        {"time_display": s["time_display"], "type": consultation_mode, "booked": False}
        for s in result.get("available_slots", [])
    ]
    return {**result, "all_slots": all_slots}

# ── Static frontend (must be mounted BEFORE ADK catch-all) ──────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def root():
    index = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index):
        return JSONResponse({"status": "ok", "message": "API running"}, status_code=200)
    return FileResponse(index)

@app.get("/health")
def health():
    return {"status": "ok", "version": "6.0.0"}

# ── Dev endpoints — prior auth toggling ──────────────────────────────────────

class TogglePriorAuthRequest(BaseModel):
    member_id: str

@app.post("/dev/toggle-prior-auth")
def toggle_prior_auth(req: TogglePriorAuthRequest):
    from app.services.storage_service import storage
    from app.adk import agent
    new_status = storage.toggle_prior_auth_status(req.member_id)
    if hasattr(agent, "_runners"):
        for k in [k for k in list(agent._runners.keys()) if k.startswith(f"{req.member_id}|")]:
            agent._runners.pop(k, None)
    return {"member_id": req.member_id, "new_status": new_status}

@app.get("/dev/prior-auth-status/{member_id}")
def get_prior_auth_status(member_id: str):
    from app.services.storage_service import storage
    data = storage.get_prior_auth(member_id)
    if not data:
        return {"member_id": member_id, "status": "no_file"}
    return {"member_id": member_id, "status": data.get("status", "none"), "data": data}

# ── Mount ADK web server LAST (serves /run, /apps) ───────────────────────────
try:
    from google.adk.cli.fast_api import get_fast_api_app
    from app.adk.agent import APP_NAME

    adk_app = get_fast_api_app(
        agents_dir=os.path.join(os.path.dirname(__file__), "adk"),
        session_service_uri=None,
        artifact_service_uri=None,
        memory_service_uri=None,
        allow_origins=["*"],
        web=False,
    )
    app.mount("/adk", adk_app)
    logger.info("ADK web server mounted — /adk/run and /adk/apps endpoints active")
except Exception as e:
    logger.warning("ADK web server could not be mounted: %s", e)
