from .general import GeneralAgent
from .coder import CoderAgent

AGENT_REGISTRY = {
    "general": GeneralAgent(),
    "coder": CoderAgent()
}