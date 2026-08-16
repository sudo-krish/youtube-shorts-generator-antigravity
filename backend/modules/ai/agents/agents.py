import logging
import json
from google.genai import types
from .llm.llm_client import get_llm_client

logger = logging.getLogger(__name__)

class BaseDynamicAgent:
    name: str = "generic"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, payload: dict) -> dict:
        raise NotImplementedError("execute method must be overridden by specific agents")


def get_all_agents():
    # Lazy imports to prevent circular dependencies
    from .roles.scriptwriter import ScriptWriterAgent
    from .roles.builder import BuilderAgent
    from .roles.editor import EditorAgent
    from .roles.director import DirectorAgent
    from .roles.specialist import SpecialistAgent
    from .roles.narrator import NarrativeInferenceNode
    from .roles.ideation import IdeationAgent

    return {
        "scriptwriter": ScriptWriterAgent(),
        "builder": BuilderAgent(),
        "editor": EditorAgent(),
        "director": DirectorAgent(),
        "specialist": SpecialistAgent(),
        "narrator": NarrativeInferenceNode(),
        "ideation": IdeationAgent(),
    }
