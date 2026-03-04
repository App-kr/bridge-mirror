"""Orchestrator — routes messages and handles DELEGATE commands."""

import re
from typing import Callable

from bridge_agent.llm.base import LLMProvider
from bridge_agent.tools.base import BaseTool
from bridge_agent.tools.registry import create_tools_for_agent

from .base import BaseAgent
from .team_lead import create_team_lead
from .security_check import create_security_check
from .feature_dev import create_feature_dev
from .qa_test import create_qa_test

DELEGATE_PATTERN = re.compile(r"DELEGATE:(\S+):\s*(.+)", re.MULTILINE)

AGENT_FACTORIES = {
    "team-lead": create_team_lead,
    "security-check": create_security_check,
    "feature-dev": create_feature_dev,
    "qa-test": create_qa_test,
}


class Orchestrator:
    """Manages agent creation, message routing, and delegation."""

    def __init__(
        self,
        provider: LLMProvider,
        project_root,
        on_agent_switch: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_text: Callable[[str], None] | None = None,
        on_delegate: Callable[[str, str], None] | None = None,
    ):
        self._provider = provider
        self._project_root = project_root
        self._on_agent_switch = on_agent_switch
        self._on_tool_call = on_tool_call
        self._on_text = on_text
        self._on_delegate = on_delegate
        self._agents: dict[str, BaseAgent] = {}
        self._current_agent_name = "team-lead"

    @property
    def current_agent(self) -> BaseAgent:
        return self._get_or_create(self._current_agent_name)

    @property
    def current_agent_name(self) -> str:
        return self._current_agent_name

    def _get_or_create(self, agent_name: str) -> BaseAgent:
        """Get existing agent or create a new one."""
        if agent_name not in self._agents:
            factory = AGENT_FACTORIES.get(agent_name)
            if not factory:
                raise ValueError(f"Unknown agent: {agent_name}")

            tools = create_tools_for_agent(agent_name, self._project_root)
            self._agents[agent_name] = factory(
                provider=self._provider,
                tools=tools,
                on_tool_call=self._on_tool_call,
                on_text=None,  # orchestrator handles text
            )
        return self._agents[agent_name]

    def switch_agent(self, agent_name: str):
        """Switch to a different agent."""
        if agent_name not in AGENT_FACTORIES:
            raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_FACTORIES.keys())}")
        self._current_agent_name = agent_name
        if self._on_agent_switch:
            self._on_agent_switch(agent_name)

    def chat(self, user_input: str) -> str:
        """Send message to current agent, handle delegations."""
        agent = self.current_agent
        response = agent.chat(user_input)

        # Check for DELEGATE commands
        delegates = DELEGATE_PATTERN.findall(response)
        if delegates:
            results = []
            results.append(response)

            for agent_name, task in delegates:
                agent_name = agent_name.strip()
                task = task.strip()

                if agent_name not in AGENT_FACTORIES:
                    results.append(f"\n[Unknown agent: {agent_name}]")
                    continue

                if self._on_delegate:
                    self._on_delegate(agent_name, task)

                sub_agent = self._get_or_create(agent_name)
                sub_response = sub_agent.chat(task)
                results.append(
                    f"\n--- {agent_name} 결과 ---\n{sub_response}\n--- /{agent_name} ---"
                )

            # Feed results back to team-lead for synthesis
            combined = "\n\n".join(results)
            if self._current_agent_name == "team-lead" and len(delegates) > 0:
                synthesis = agent.chat(
                    f"팀원들의 작업 결과를 통합해서 보고해줘:\n{combined}"
                )
                return synthesis

            return combined

        return response

    def reset_agent(self, agent_name: str | None = None):
        """Reset an agent's conversation."""
        name = agent_name or self._current_agent_name
        if name in self._agents:
            self._agents[name].reset()

    def reset_all(self):
        """Reset all agents."""
        self._agents.clear()

    def list_agents(self) -> list[dict]:
        """List available agents with info."""
        result = []
        for name, factory in AGENT_FACTORIES.items():
            agent = self._agents.get(name)
            result.append({
                "name": name,
                "active": name == self._current_agent_name,
                "has_history": agent is not None and len(agent.conversation) > 0,
                "tokens": agent.total_tokens if agent else (0, 0),
            })
        return result

    def get_total_tokens(self) -> tuple[int, int]:
        """Get total token usage across all agents."""
        total_in = sum(a.total_tokens[0] for a in self._agents.values())
        total_out = sum(a.total_tokens[1] for a in self._agents.values())
        return total_in, total_out
