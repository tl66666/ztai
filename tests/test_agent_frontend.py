import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = (
            ROOT / "frontend" / "src" / "app" / "runtime.ts"
        ).read_text(encoding="utf-8")
        cls.workspace = (
            ROOT / "frontend" / "src" / "agent" / "agent-workspace.ts"
        ).read_text(encoding="utf-8")
        cls.contextual = (
            ROOT / "frontend" / "src" / "agent" / "contextual-agent.mjs"
        ).read_text(encoding="utf-8")
        cls.topbar = (
            ROOT / "frontend" / "src" / "shell" / "topbar-controller.ts"
        ).read_text(encoding="utf-8")
        cls.runtime_ui = (
            ROOT / "frontend" / "src" / "shared" / "runtime-ui.ts"
        ).read_text(encoding="utf-8")

    def test_agent_has_one_product_identity_and_a_separate_command_dashboard(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        navigation = (
            ROOT / "frontend" / "src" / "shell" / "navigation-model.ts"
        ).read_text(encoding="utf-8")
        sidebar = (
            ROOT / "frontend" / "src" / "shell" / "sidebar.tsx"
        ).read_text(encoding="utf-8")

        self.assertIn('label: "求职指挥台"', navigation)
        self.assertIn("<span>{label}</span>", sidebar)
        self.assertIn('id="reactAppRoot"', html)
        self.assertIn('Agent 运行看板', html)
        self.assertIn('这里不重复聊天', html)
        self.assertIn('打开求职 Agent', html)
        self.assertNotIn('<span>AI 教练</span>', html)
        self.assertIn('agent: "求职指挥台"', self.runtime)
        self.assertNotIn('AI 教练正在读取上下文并处理任务', self.runtime)

    def test_agent_page_has_conversation_controls(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="agentConversationSelect"', html)
        self.assertIn('id="newAgentConversation"', html)
        self.assertIn('id="clearAgentConversation"', html)

    def test_agent_chat_persists_conversation_and_restores_messages(self):
        self.assertIn("JOBHUNTER_AGENT_CONVERSATION", self.runtime)
        self.assertIn("loadAgentConversations", self.runtime)
        self.assertIn("restoreAgentMessages", self.workspace)
        self.assertIn("conversation_id: conversationId", self.workspace)
        self.assertIn("data.conversation_id !== conversationId", self.workspace)

    def test_agent_click_handlers_do_not_pass_browser_events_as_messages(self):
        self.assertIn(
            '$("sendAgentBtn").addEventListener("click", () => sendAgentMessage());',
            self.runtime,
        )
        self.assertIn(
            '$("newAgentConversation")?.addEventListener("click", '
            "() => createAgentConversation());",
            self.runtime,
        )
        self.assertIn("contextualAgent.outboundMessage", self.workspace)

    def test_agent_message_renderer_formats_common_markdown_without_exposing_markers(self):
        self.assertIn('"<strong>$1</strong>"', self.runtime_ui)
        self.assertIn('"<hr>"', self.runtime_ui)

    def test_agent_ui_does_not_label_events_as_private_reasoning(self):
        self.assertNotIn("Agent 自主决策过程", self.workspace)
        self.assertIn("renderAgentEvents", self.workspace)
        self.assertIn('status === "needs_input" ? "选择简历后继续"', self.workspace)
        self.assertNotIn('status === "needs_input" ? "等待补充"', self.workspace)

    def test_local_agent_welcome_and_business_tool_labels_are_user_facing(self):
        self.assertIn("无需 API Key", self.workspace)
        self.assertIn('get_career_profile: "读取职业目标"', self.workspace)
        self.assertIn('list_action_items: "读取行动项"', self.workspace)
        self.assertIn('get_training_insights: "汇总训练记录"', self.workspace)
        self.assertIn('prepare_resume_revision: "生成可编辑草稿"', self.workspace)

    def test_agent_drawer_exposes_resume_workflow_controls(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-prompt="选择一份简历进行诊断"', html)
        self.assertIn('data-prompt="选择一份简历生成优化草稿"', html)
        self.assertIn('data-prompt="我是新用户，带我开始使用这个求职系统"', html)
        self.assertIn('id="agentResumeUpload"', html)
        self.assertIn("本地智能求职助手", html)
        self.assertIn("renderAgentInputRequest", self.workspace)
        self.assertIn("message.metadata?.suggested_actions", self.workspace)
        self.assertIn("/draft", self.workspace)
        self.assertIn("openResumeUploadFromAgent", self.runtime)
        self.assertIn("cancelResumeEdit();", self.runtime)

    def test_agent_drawer_exposes_the_current_model_mode(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="agentModeLabel"', html)
        self.assertIn('id="agentModeDetail"', html)
        self.assertIn("agentModeLabel", self.topbar)
        self.assertIn("本地任务优先执行", self.topbar)
        self.assertIn("开放问题由模型增强", self.topbar)


if __name__ == "__main__":
    unittest.main()
