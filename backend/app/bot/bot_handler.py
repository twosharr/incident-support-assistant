"""
Microsoft Teams Bot Handler using Bot Framework SDK.
Processes incoming Teams messages and routes to the AI assistant.
"""
from botbuilder.core import ActivityHandler, TurnContext, CardFactory
from botbuilder.schema import Activity, ActivityTypes
from app.ai.assistant import AIAssistant
from app.models import ChatRequest
import json


assistant = AIAssistant()


class IncidentSupportBot(ActivityHandler):
    """Teams bot handler that processes messages and returns AI responses."""

    async def on_message_activity(self, turn_context: TurnContext):
        user_message = turn_context.activity.text or ""
        user_message = user_message.strip()

        if not user_message:
            await turn_context.send_activity("Please type a question or incident ID.")
            return

        # Get conversation ID from Teams context
        conversation_id = turn_context.activity.conversation.id

        # Send typing indicator
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        # Process with AI assistant
        request = ChatRequest(
            message=user_message,
            conversation_id=conversation_id,
            history=[]
        )
        ai_response = assistant.chat(request)

        # Send response as Adaptive Card if it has structured data, else as text
        if ai_response.sources:
            card = self._build_adaptive_card(ai_response.response, ai_response.sources, ai_response.tools_used)
            await turn_context.send_activity(Activity(
                type=ActivityTypes.message,
                attachments=[CardFactory.adaptive_card(card)]
            ))
        else:
            await turn_context.send_activity(ai_response.response)

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "👋 **Welcome to AI Incident Support Assistant!**\n\n"
                    "I can help you with incident status, outage information, "
                    "troubleshooting steps, and knowledge base articles.\n\n"
                    "Try asking: *'What is the status of INC12345?'*"
                )

    def _build_adaptive_card(self, response: str, sources: list, tools_used: list) -> dict:
        """Build an Adaptive Card for rich Teams rendering."""
        tool_name = tools_used[0] if tools_used else "search"
        tool_display = tool_name.replace("_", " ").title()

        body = [
            {
                "type": "TextBlock",
                "text": response[:1000],  # Truncate for card
                "wrap": True,
                "markdown": True
            }
        ]

        if sources:
            source_text = " · ".join([
                s.get("id") or s.get("service") or s.get("title", "")
                for s in sources[:3]
            ])
            body.append({
                "type": "TextBlock",
                "text": f"📎 Sources: {source_text}",
                "size": "Small",
                "color": "Accent",
                "wrap": True
            })

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": body,
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "🔄 Check for Updates",
                    "data": {"action": "refresh", "query": "check for updates"}
                }
            ]
        }
