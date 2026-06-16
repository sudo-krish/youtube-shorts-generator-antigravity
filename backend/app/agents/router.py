from fastapi import APIRouter
from app.agents.schemas import (
    AgentResponse,
    ObserverRequest,
    ScriptwriterRequest,
    DirectorRequest,
    EditorRequest,
    SpecialistRequest,
    BuilderRequest
)
from app.agents.manager import (
    ObserverAgent,
    ScriptWriterAgent as ScriptwriterAgent,
    DirectorAgent,
    EditorAgent,
    SpecialistAgent,
    BuilderAgent
)

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.post("/observer", response_model=AgentResponse)
async def run_observer(req: ObserverRequest):
    agent = ObserverAgent()
    result = agent.execute(
        req.chunk_path,
        req.metadata,
        req.audio_spikes,
        req.ocr_dumps,
        req.semantic_matrix
    )
    return AgentResponse(output=result)

@router.post("/scriptwriter", response_model=AgentResponse)
async def run_scriptwriter(req: ScriptwriterRequest):
    agent = ScriptwriterAgent()
    result = agent.execute(
        req.context,
        req.metadata,
        req.web_trends
    )
    return AgentResponse(output=result)

@router.post("/director", response_model=AgentResponse)
async def run_director(req: DirectorRequest):
    agent = DirectorAgent()
    result = agent.execute(
        req.context,
        req.scripts,
        req.metadata,
        req.sfx_library,
        req.music_library
    )
    return AgentResponse(output=result)

@router.post("/editor", response_model=AgentResponse)
async def run_editor(req: EditorRequest):
    agent = EditorAgent()
    result = agent.execute(
        req.scripts,
        req.vision,
        req.metadata,
        req.yolo_tracking
    )
    return AgentResponse(output=result)

@router.post("/specialist", response_model=AgentResponse)
async def run_specialist(req: SpecialistRequest):
    agent = SpecialistAgent()
    result = agent.execute(
        req.breakdown,
        req.metadata,
        req.math_report,
        req.youtube_rules,
        req.capabilities
    )
    return AgentResponse(output=result)

@router.post("/builder", response_model=AgentResponse)
async def run_builder(req: BuilderRequest):
    agent = BuilderAgent()
    result = agent.execute(
        req.validated_plans,
        req.metadata
    )
    return AgentResponse(output=result)
