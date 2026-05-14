from .general import GeneralAgent
from .coder import CoderAgent
from .gen_image import GenImageAgent

AGENT_REGISTRY = {
    "general": GeneralAgent(),
    "coder": CoderAgent(),
    "gen_image": GenImageAgent()
}