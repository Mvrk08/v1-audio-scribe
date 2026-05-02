import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jwt
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from starlette.middleware.cors import CORSMiddleware


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
DEMO_EMAIL = os.environ["DEMO_EMAIL"]
DEMO_PASSWORD = os.environ["DEMO_PASSWORD"]
MOCK_EXTERNAL_SERVICES = os.environ.get("MOCK_EXTERNAL_SERVICES", "true").lower() == "true"
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_AUDIO_SECONDS = 120
SUPPORTED_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "aac", "flac", "ogg", "mp4"}
LANGUAGE_CODES = {"auto": "Auto detect", "en": "English", "hi": "Hindi", "pa": "Punjabi"}
SARVAM_LANGUAGE_CODES = {"auto": "unknown", "en": "en-IN", "hi": "hi-IN", "pa": "pa-IN"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
security = HTTPBearer(auto_error=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(String, nullable=False)

    sessions = relationship("MedicalSession", back_populates="user")


class MedicalSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="created")
    source_language = Column(String, nullable=False, default="auto")
    target_language = Column(String, nullable=False, default="en")
    duration_seconds = Column(Float, default=0)
    original_filename = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    audio_mime = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    user = relationship("User", back_populates="sessions")
    transcript = relationship("Transcript", uselist=False, back_populates="session", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), unique=True, nullable=False)
    raw_transcript = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    structured_prescription = Column(Text, nullable=False)
    language_code = Column(String, nullable=False)
    confidence = Column(Float, nullable=False, default=0.9)
    sarvam_job_id = Column(String, nullable=True)
    warnings = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    session = relationship("MedicalSession", back_populates="transcript")


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: int
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class SessionCreateRequest(BaseModel):
    source_language: str = "auto"
    target_language: str = "en"


class SessionResponse(BaseModel):
    id: str
    status: str
    source_language: str
    target_language: str
    duration_seconds: float
    original_filename: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str
    has_result: bool = False


class StatusResponse(SessionResponse):
    current_step: str
    warning: Optional[str] = None


class Prescription(BaseModel):
    symptoms: List[str]
    diagnosis: str
    medications: List[str]
    advice: List[str]
    follow_up: str


class ResultResponse(BaseModel):
    session: SessionResponse
    raw_transcript: str
    translated_text: str
    structured_prescription: Prescription
    language_code: str
    confidence: float
    sarvam_job_id: Optional[str]
    warnings: List[str]


class ResultUpdateRequest(BaseModel):
    raw_transcript: str
    translated_text: str
    structured_prescription: Prescription


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_demo_user() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not existing:
            db.add(User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), created_at=now_iso()))
            db.commit()
            logger.info("Seeded demo doctor account")
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def session_to_response(session: MedicalSession) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        status=session.status,
        source_language=session.source_language,
        target_language=session.target_language,
        duration_seconds=session.duration_seconds or 0,
        original_filename=session.original_filename,
        error_message=session.error_message,
        created_at=session.created_at,
        updated_at=session.updated_at,
        has_result=session.transcript is not None,
    )


def validate_language(code: str, allow_auto: bool = False) -> str:
    allowed = set(LANGUAGE_CODES.keys()) if allow_auto else {"en", "hi", "pa"}
    if code not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {code}")
    return code


class SarvamService:
    """Sarvam wrapper with mock fallback and live batch STT/translation support."""

    def _client(self):
        if not SARVAM_API_KEY:
            raise RuntimeError("Sarvam API key is not configured")
        from sarvamai import SarvamAI

        return SarvamAI(api_subscription_key=SARVAM_API_KEY, timeout=120)

    def _language_code(self, language: Optional[str]) -> str:
        if not language:
            return "auto"
        normalized = language.strip()
        if normalized in SARVAM_LANGUAGE_CODES:
            return SARVAM_LANGUAGE_CODES[normalized]
        if normalized in {"unknown", "auto"}:
            return "auto"
        if normalized.endswith("-IN"):
            return normalized
        return SARVAM_LANGUAGE_CODES.get(normalized[:2], "auto")

    def _response_value(self, response: Any, key: str, default: str = "") -> str:
        if isinstance(response, dict):
            return response.get(key, default)
        return getattr(response, key, default)

    def _extract_text(self, file_results: Dict[str, List[Dict[str, Any]]]) -> str:
        successful = file_results.get("successful") or []
        pieces = []
        for item in successful:
            for key in ("transcript", "transcribed_text", "text", "output_text"):
                value = item.get(key)
                if value:
                    pieces.append(str(value).strip())
                    break
        return "\n".join(piece for piece in pieces if piece).strip()

    def transcribe(self, session: MedicalSession) -> Dict[str, Any]:
        if not MOCK_EXTERNAL_SERVICES:
            if not session.audio_path or not Path(session.audio_path).exists():
                raise RuntimeError("Temporary audio file is missing")
            client = self._client()
            language_code = self._language_code(session.source_language)
            create_kwargs = {
                "model": "saaras:v3",
                "mode": "transcribe",
                "with_diarization": False,
                "with_timestamps": False,
            }
            if language_code != "auto":
                create_kwargs["language_code"] = language_code
            job = client.speech_to_text_job.create_job(**create_kwargs)
            uploaded = job.upload_files(file_paths=[session.audio_path], timeout=90)
            if not uploaded:
                raise RuntimeError("Sarvam audio upload failed")
            job.start()
            job.wait_until_complete(poll_interval=3, timeout=300)
            if job.is_failed():
                raise RuntimeError("Sarvam speech-to-text job failed")
            file_results = job.get_file_results()
            text = self._extract_text(file_results)
            if not text:
                text = "No speech detected."
            return {
                "text": text,
                "language_code": language_code if language_code != "auto" else "unknown",
                "confidence": 0.9,
                "job_id": job.job_id,
                "warning": "",
            }
        transcript = (
            "Patient reports fever, sore throat, and dry cough for three days. "
            "Doctor advises paracetamol 500 mg twice daily after food, warm fluids, rest, "
            "and review in three days if symptoms persist. No allergy was mentioned."
        )
        return {
            "text": transcript,
            "language_code": "en" if session.source_language == "auto" else session.source_language,
            "confidence": 0.92,
            "job_id": f"mock-sarvam-{session.id[:8]}",
            "warning": "MOCKED Sarvam speech-to-text used because no Sarvam API key was provided.",
        }

    def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> Dict[str, str]:
        target_code = self._language_code(target_language)
        source_code = self._language_code(source_language)
        if not MOCK_EXTERNAL_SERVICES and target_code == source_code and target_code != "auto":
            return {"text": text, "warning": ""}
        if not MOCK_EXTERNAL_SERVICES:
            try:
                client = self._client()
                response = client.text.translate(
                    input=text,
                    source_language_code=source_code if source_code != "unknown" else "auto",
                    target_language_code=target_code,
                )
                translated_text = self._response_value(response, "translated_text") or text
                return {"text": translated_text, "warning": ""}
            except Exception as exc:
                logger.exception("Sarvam translation failed")
                return {
                    "text": text,
                    "warning": f"Sarvam translation failed, showing original transcript instead: {exc}",
                }
        if target_language == "en":
            return {"text": text, "warning": ""}
        translations = {
            "hi": (
                "मरीज़ को तीन दिनों से बुखार, गले में खराश और सूखी खांसी है। डॉक्टर ने भोजन के बाद "
                "दिन में दो बार पैरासिटामोल 500 mg, गर्म तरल पदार्थ, आराम और लक्षण बने रहने पर तीन दिनों "
                "में पुनः जांच की सलाह दी। कोई एलर्जी नहीं बताई गई।"
            ),
            "pa": (
                "ਮਰੀਜ਼ ਨੂੰ ਤਿੰਨ ਦਿਨਾਂ ਤੋਂ ਬੁਖਾਰ, ਗਲੇ ਵਿੱਚ ਦਰਦ ਅਤੇ ਸੁੱਕੀ ਖੰਘ ਹੈ। ਡਾਕਟਰ ਨੇ ਖਾਣੇ ਤੋਂ ਬਾਅਦ "
                "ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰੀ ਪੈਰਾਸੀਟਾਮੋਲ 500 mg, ਗਰਮ ਤਰਲ ਪਦਾਰਥ, ਆਰਾਮ ਅਤੇ ਲੱਛਣ ਰਹਿਣ 'ਤੇ ਤਿੰਨ ਦਿਨਾਂ "
                "ਵਿੱਚ ਮੁੜ ਜਾਂਚ ਦੀ ਸਲਾਹ ਦਿੱਤੀ। ਕੋਈ ਐਲਰਜੀ ਨਹੀਂ ਦੱਸੀ ਗਈ।"
            ),
        }
        return {
            "text": translations[target_language],
            "warning": "MOCKED Sarvam translation used because no Sarvam API key was provided.",
        }


class LLMService:
    """Gemini extraction placeholder. V1 intentionally returns deterministic mock output."""

    def extract_prescription(self, clean_transcript: str) -> Dict[str, Any]:
        return {
            "symptoms": ["Fever", "Sore throat", "Dry cough for three days"],
            "diagnosis": "Not specified",
            "medications": ["Paracetamol 500 mg twice daily after food"],
            "advice": ["Warm fluids", "Rest", "Monitor symptoms"],
            "follow_up": "Review in three days if symptoms persist",
        }


sarvam_service = SarvamService()
llm_service = LLMService()

app = FastAPI(title="Medical Audio Transcription MVP", version="1.0.0")
api_router = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    seed_demo_user()


@api_router.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "healthy", "mock_external_services": MOCK_EXTERNAL_SERVICES, "timestamp": now_iso()}


@api_router.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or user.password_hash != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResponse(token=create_token(user), user=UserResponse(id=user.id, email=user.email))


@api_router.post("/auth/logout")
async def logout(_: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"status": "logged_out"}


@api_router.get("/auth/session", response_model=UserResponse)
async def session(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email)


@api_router.post("/v1/sessions", response_model=SessionResponse)
async def create_session(
    payload: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    validate_language(payload.source_language, allow_auto=True)
    validate_language(payload.target_language)
    session_id = str(uuid.uuid4())
    created = now_iso()
    medical_session = MedicalSession(
        id=session_id,
        user_id=user.id,
        status="created",
        source_language=payload.source_language,
        target_language=payload.target_language,
        created_at=created,
        updated_at=created,
    )
    db.add(medical_session)
    db.commit()
    db.refresh(medical_session)
    return session_to_response(medical_session)


@api_router.get("/v1/sessions", response_model=List[SessionResponse])
async def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[SessionResponse]:
    sessions = (
        db.query(MedicalSession)
        .filter(MedicalSession.user_id == user.id)
        .order_by(MedicalSession.created_at.desc())
        .limit(50)
        .all()
    )
    return [session_to_response(item) for item in sessions]


@api_router.post("/v1/sessions/{session_id}/audio", response_model=SessionResponse)
async def upload_audio(
    session_id: str,
    file: UploadFile = File(...),
    duration_seconds: float = Form(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    medical_session = db.query(MedicalSession).filter_by(id=session_id, user_id=user.id).first()
    if not medical_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if duration_seconds and duration_seconds > MAX_AUDIO_SECONDS:
        raise HTTPException(status_code=413, detail="Audio exceeds the 2 minute limit")

    filename = file.filename or "recording.webm"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    temp_path = Path("/tmp") / f"medical-audio-{session_id}.{extension}"
    medical_session.status = "uploading"
    medical_session.updated_at = now_iso()
    db.commit()

    size = 0
    try:
        with temp_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_AUDIO_BYTES:
                    raise HTTPException(status_code=413, detail="Audio file is larger than 25MB")
                buffer.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        medical_session.status = "uploaded"
        medical_session.duration_seconds = min(duration_seconds or 0, MAX_AUDIO_SECONDS)
        medical_session.original_filename = filename
        medical_session.audio_path = str(temp_path)
        medical_session.audio_mime = file.content_type
        medical_session.error_message = None
        medical_session.updated_at = now_iso()
        db.commit()
        db.refresh(medical_session)
        return session_to_response(medical_session)
    except HTTPException:
        if temp_path.exists():
            temp_path.unlink()
        medical_session.status = "failed"
        medical_session.error_message = "Audio upload validation failed"
        medical_session.updated_at = now_iso()
        db.commit()
        raise
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        medical_session.status = "failed"
        medical_session.error_message = "Audio upload failed"
        medical_session.updated_at = now_iso()
        db.commit()
        raise HTTPException(status_code=500, detail="Audio upload failed") from exc


async def process_session_task(session_id: str) -> None:
    await asyncio.sleep(2)
    db = SessionLocal()
    try:
        medical_session = db.query(MedicalSession).filter(MedicalSession.id == session_id).first()
        if not medical_session:
            return
        try:
            stt = sarvam_service.transcribe(medical_session)
            translated = sarvam_service.translate(stt["text"], medical_session.target_language, stt.get("language_code"))
            prescription = llm_service.extract_prescription(translated["text"] if medical_session.target_language == "en" else stt["text"])
            warnings = [stt.get("warning", ""), translated.get("warning", ""), "MOCKED Gemini prescription extraction used for this preview build."]
            transcript = Transcript(
                id=str(uuid.uuid4()),
                session_id=session_id,
                raw_transcript=stt["text"],
                translated_text=translated["text"],
                structured_prescription=json.dumps(prescription),
                language_code=stt["language_code"],
                confidence=stt["confidence"],
                sarvam_job_id=stt["job_id"],
                warnings=json.dumps([warning for warning in warnings if warning]),
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            existing = db.query(Transcript).filter(Transcript.session_id == session_id).first()
            if existing:
                db.delete(existing)
                db.flush()
            db.add(transcript)
            medical_session.status = "completed"
            medical_session.error_message = None
            medical_session.updated_at = now_iso()
            db.commit()
        except Exception as exc:
            medical_session.status = "failed"
            medical_session.error_message = str(exc)
            medical_session.updated_at = now_iso()
            db.commit()
            logger.exception("Processing failed for session %s", session_id)
        finally:
            if medical_session.audio_path and Path(medical_session.audio_path).exists():
                Path(medical_session.audio_path).unlink()
                medical_session.audio_path = None
                db.commit()
    finally:
        db.close()


@api_router.post("/v1/sessions/{session_id}/process", response_model=StatusResponse)
async def start_processing(
    session_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    medical_session = db.query(MedicalSession).filter_by(id=session_id, user_id=user.id).first()
    if not medical_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if medical_session.status == "completed":
        return StatusResponse(**session_to_response(medical_session).model_dump(), current_step="completed")
    if medical_session.status == "running":
        return StatusResponse(**session_to_response(medical_session).model_dump(), current_step="running")
    if not medical_session.audio_path:
        raise HTTPException(status_code=400, detail="Upload audio before processing")

    medical_session.status = "running"
    medical_session.error_message = None
    medical_session.updated_at = now_iso()
    db.commit()
    db.refresh(medical_session)
    background_tasks.add_task(process_session_task, session_id)
    return StatusResponse(
        **session_to_response(medical_session).model_dump(),
        current_step="running",
        warning="MOCKED external AI services are active for this preview.",
    )


@api_router.get("/v1/sessions/{session_id}/status", response_model=StatusResponse)
async def get_status(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    medical_session = db.query(MedicalSession).filter_by(id=session_id, user_id=user.id).first()
    if not medical_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return StatusResponse(
        **session_to_response(medical_session).model_dump(),
        current_step=medical_session.status,
        warning="MOCKED external AI services are active." if MOCK_EXTERNAL_SERVICES else None,
    )


@api_router.get("/v1/sessions/{session_id}/result", response_model=ResultResponse)
async def get_result(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResultResponse:
    medical_session = db.query(MedicalSession).filter_by(id=session_id, user_id=user.id).first()
    if not medical_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not medical_session.transcript:
        raise HTTPException(status_code=404, detail="Result is not ready yet")
    transcript = medical_session.transcript
    return ResultResponse(
        session=session_to_response(medical_session),
        raw_transcript=transcript.raw_transcript,
        translated_text=transcript.translated_text,
        structured_prescription=json.loads(transcript.structured_prescription),
        language_code=transcript.language_code,
        confidence=transcript.confidence,
        sarvam_job_id=transcript.sarvam_job_id,
        warnings=json.loads(transcript.warnings or "[]"),
    )


@api_router.patch("/v1/sessions/{session_id}/result", response_model=ResultResponse)
async def update_result(
    session_id: str,
    payload: ResultUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResultResponse:
    medical_session = db.query(MedicalSession).filter_by(id=session_id, user_id=user.id).first()
    if not medical_session or not medical_session.transcript:
        raise HTTPException(status_code=404, detail="Result not found")
    transcript = medical_session.transcript
    transcript.raw_transcript = payload.raw_transcript
    transcript.translated_text = payload.translated_text
    transcript.structured_prescription = json.dumps(payload.structured_prescription.model_dump())
    transcript.updated_at = now_iso()
    medical_session.updated_at = now_iso()
    db.commit()
    db.refresh(medical_session)
    return await get_result(session_id, user, db)


@api_router.delete("/v1/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    medical_session = db.query(MedicalSession).filter_by(id=session_id, user_id=user.id).first()
    if not medical_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if medical_session.audio_path and Path(medical_session.audio_path).exists():
        Path(medical_session.audio_path).unlink()
    db.delete(medical_session)
    db.commit()
    return {"status": "deleted"}


app.include_router(api_router)