from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages

class MasonState(TypedDict):
    """
    定义整个 Graph 流转的数据结构
    messages: 存储对话历史
    """
    messages: Annotated[list[AnyMessage], add_messages]
    # 记录当前活跃的Agent
    current_agent: Literal["router", "general", "coder", "gen_image"]

