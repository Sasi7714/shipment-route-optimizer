"""FastAPI endpoints for shipment route comparison and recommendation."""
from contextlib import asynccontextmanager
import os
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import FeatureFlags
from app.database import get_session, initialise_database
from app.errors import ApplicationError, FeatureDisabledError, ResourceNotFoundError
from app.explanation import pareto_explanation, recommendation_explanation
from app.logging_config import logger
from app.models import OptimizationRequest, Route
from app.optimizer import annotate_pareto, pareto_routes
from app.scoring import score_routes

FLAGS = FeatureFlags.from_environment()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        initialise_database()
        logger.info("application_started")
        yield
    except Exception:
        # Do not surface database paths, SQL, or source details to callers.
        logger.error("startup_failed")
        raise
    finally:
        logger.info("application_stopped")


app = FastAPI(
    title="Shipment Route Optimization System",
    version="1.1.0",
    description="Synthetic-data route decision support with explainable weighted scoring.",
    lifespan=lifespan,
)

# The dashboard runs on Vite's local origin by default. Override with a
# comma-separated ALLOWED_ORIGINS list when deploying the frontend elsewhere.
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def sanitized_request_log(request: Request, call_next):
    """Log only method, status, duration and an opaque ID--never headers or body."""
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        logger.error("request_failed request_id=%s method=%s duration_ms=%s", request_id, request.method, elapsed_ms)
        raise
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_completed request_id=%s method=%s status=%s duration_ms=%s", request_id, request.method, response.status_code, elapsed_ms)
    return response


@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, error: ApplicationError):
    logger.warning("handled_error code=%s status=%s", error.code, error.status_code)
    return JSONResponse(status_code=error.status_code, content={"error": {"code": error.code, "message": error.message}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError):
    # Return field locations only; this avoids echoing invalid values back to a client or log.
    fields = [".".join(str(part) for part in item["loc"]) for item in error.errors()]
    logger.warning("validation_failed fields=%s", ",".join(fields))
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed.", "fields": fields}},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception):
    error_id = uuid.uuid4().hex
    logger.error("unexpected_error error_id=%s", error_id)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred.", "error_id": error_id}},
    )


def _routes_for(shipment_id: str, session: Session) -> list[dict]:
    normalized_id = shipment_id.strip().upper()
    records = session.query(Route).filter(Route.shipment_id == normalized_id).all()
    if not records:
        raise ResourceNotFoundError("The requested shipment was not found.")
    return [{column.name: getattr(record, column.name) for column in Route.__table__.columns if column.name != "id"} for record in records]


def _require_optimization() -> None:
    if not FLAGS.optimization_enabled:
        raise FeatureDisabledError("Route optimization is temporarily disabled.")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "shipment-route-optimizer"}


@app.get("/shipments")
def list_shipments(session: Session = Depends(get_session)):
    records = session.query(Route).order_by(Route.shipment_id).all()
    seen = set()
    return [
        {"shipment_id": record.shipment_id, "origin": record.origin, "destination": record.destination}
        for record in records
        if not (record.shipment_id in seen or seen.add(record.shipment_id))
    ]


@app.get("/shipments/{shipment_id}")
def shipment_details(shipment_id: str, session: Session = Depends(get_session)):
    first = _routes_for(shipment_id, session)[0]
    return {"shipment_id": first["shipment_id"], "origin": first["origin"], "destination": first["destination"], "simulated_data": True}


@app.get("/shipments/{shipment_id}/routes")
def available_routes(shipment_id: str, session: Session = Depends(get_session)):
    return {"shipment_id": shipment_id.strip().upper(), "routes": _routes_for(shipment_id, session), "currency": "INR"}


def _optimise(shipment_id: str, request: OptimizationRequest, session: Session) -> dict:
    _require_optimization()
    routes = _routes_for(shipment_id, session)
    weights = {"cost": request.cost_weight, "time": request.time_weight, "risk": request.risk_weight}
    scored = score_routes(routes, weights)
    annotated = annotate_pareto(scored) if FLAGS.pareto_analysis_enabled else scored
    pareto = pareto_routes(routes) if FLAGS.pareto_analysis_enabled else []
    pareto_ids = {route["route_id"] for route in pareto}
    recommended = next(route for route in annotated if route["rank"] == 1)
    first = routes[0]
    response = {
        "shipment": {key: first[key] for key in ("shipment_id", "origin", "destination")},
        "simulated_data": True,
        "currency": "INR",
        "weights_used": weights,
        "routes_ranked": annotated,
        "recommended_route": recommended,
        "explanation": recommendation_explanation(recommended, annotated, pareto_ids),
    }
    if FLAGS.pareto_analysis_enabled:
        response["pareto_optimal_routes"] = [route for route in annotated if route["pareto_optimal"]]
        response["pareto_tradeoff_explanation"] = pareto_explanation(pareto)
    return response


@app.post("/optimize/{shipment_id}")
def optimize(shipment_id: str, request: OptimizationRequest | None = None, session: Session = Depends(get_session)):
    return _optimise(shipment_id, request or OptimizationRequest(), session)


@app.get("/optimize/{shipment_id}/comparison")
def comparison(shipment_id: str, session: Session = Depends(get_session)):
    return _optimise(shipment_id, OptimizationRequest(), session)
