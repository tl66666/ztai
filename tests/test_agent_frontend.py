from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgentFrontendContractTests(unittest.TestCase):
    def test_agent_page_has_conversation_controls(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="agentConversationSelect"', html)
        self.assertIn('id="newAgentConversation"', html)
        self.assertIn('id="clearAgentConversation"', html)

    def test_agent_chat_persists_conversation_and_restores_messages(self):
        javascript = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("JOBHUNTER_AGENT_CONVERSATION", javascript)
        self.assertIn("loadAgentConversations", javascript)
        self.assertIn("restoreAgentMessages", javascript)
        self.assertIn("conversation_id: conversationId", javascript)
        self.assertIn("data.conversation_id !== conversationId", javascript)

    def test_agent_ui_does_not_label_events_as_private_reasoning(self):
        javascript = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("Agent 自主决策过程", javascript)
        self.assertIn("renderAgentEvents", javascript)

    def test_local_agent_welcome_and_business_tool_labels_are_user_facing(self):
        javascript = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("无需 API Key", javascript)
        self.assertIn('get_career_profile: "读取职业目标"', javascript)
        self.assertIn('list_action_items: "读取行动项"', javascript)
        self.assertIn('get_training_insights: "汇总训练记录"', javascript)


if __name__ == "__main__":
    unittest.main()
