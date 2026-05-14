import json
import requests
from src.skills.base import BaseSkill
from src.config.settings import settings
from pydantic import BaseModel, Field


class WecomMessageArgs(BaseModel):
    touser: str = Field(description="接收人的企业微信 UserID，例如 'ZhangSan'。如果用户说'发给张三'，你需要推断出 UserID。")
    content: str = Field(description="要发送的消息文本内容")
    corpid: str = Field(default="", description="企业ID，默认使用系统配置")
    corpsecret: str = Field(default="", description="应用Secret，默认使用系统配置")
    agentid: int = Field(default=0, description="应用AgentID，默认使用系统配置")


class WecomMessageSkill(BaseSkill):
    name = "wecom_message"
    description = "通过企业微信自建应用发送私信消息给指定用户。传入接收人UserID和消息内容。"
    args_schema = WecomMessageArgs

    permissions = {
        "network": True,
        "filesystem": False,
        "max_cpu": 0.2,
        "max_memory": 64,
    }

    def execute(
        self,
        touser: str = "",
        content: str = "",
        corpid: str = "",
        corpsecret: str = "",
        agentid: int = 0,
    ) -> str:
        if not touser:
            return "❌ 请指定接收人的企业微信 UserID（touser）。"
        if not content:
            return "❌ 请提供要发送的消息内容。"

        corpid = corpid or settings.WECOM_CORP_ID
        corpsecret = corpsecret or settings.WECOM_CORP_SECRET
        agentid = agentid or settings.WECOM_AGENT_ID

        if not corpid or not corpsecret:
            return "❌ 企业微信未配置。请在 .env 中设置 WECOM_CORP_ID 和 WECOM_CORP_SECRET。"
        if not agentid:
            return "❌ 企业微信 AgentID 未配置。请在 .env 中设置 WECOM_AGENT_ID。"

        try:
            token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"
            token_resp = requests.get(token_url, timeout=10).json()

            if token_resp.get("errcode") != 0:
                return f"❌ 获取 Access Token 失败: {token_resp.get('errmsg', '未知错误')}"

            access_token = token_resp.get("access_token")
        except requests.RequestException as e:
            return f"❌ 请求 Token 网络错误: {str(e)}"

        try:
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

            data = {
                "touser": touser,
                "msgtype": "text",
                "agentid": agentid,
                "text": {
                    "content": content
                },
            }

            response = requests.post(
                send_url,
                data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                timeout=10,
            ).json()

            if response.get("errcode") == 0:
                return f"✅ 消息已成功发送给 {touser}！\n📝 内容: {content}"
            else:
                return f"❌ 消息发送失败: {response.get('errmsg', '未知错误')}"

        except requests.RequestException as e:
            return f"❌ 发送消息网络错误: {str(e)}"