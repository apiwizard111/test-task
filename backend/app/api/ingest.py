from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.models.chat import GithubIngestRequest
from app.models.manifest import IngestManifest
from app.services.ingest import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/sample")
async def ingest_sample(request: Request) -> dict:
    manifest = await _ingest_service(request).ingest_sample()
    return _payload(manifest)


@router.post("/github")
async def ingest_github(payload: GithubIngestRequest, request: Request) -> dict:
    manifest = await _ingest_service(request).ingest_github(payload.url)
    return _payload(manifest)


@router.post("/zip")
async def ingest_zip(request: Request, file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip archive")
    payload = await file.read()
    name = file.filename.removesuffix(".zip")
    manifest = await _ingest_service(request).ingest_zip_bytes(payload, name=name)
    return _payload(manifest)


def _ingest_service(request: Request) -> IngestService:
    service = request.app.state.ingest
    if service is None:
        raise HTTPException(status_code=503, detail="Set OPENAI_API_KEY before ingesting a repository")
    return service


def _payload(manifest: IngestManifest) -> dict:
    return {
        "name": manifest.name,
        "source": manifest.source,
        "file_count": manifest.file_count,
        "chunk_count": manifest.chunk_count,
        "skipped_count": manifest.skipped_count,
    }
