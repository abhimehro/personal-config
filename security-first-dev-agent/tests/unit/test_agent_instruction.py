# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests to verify the agent's system instruction template."""

from app.agent import root_agent


def test_agent_instruction_contains_template_keywords() -> None:
    """Verifies that the root agent's system instruction contains key template contents."""
    instruction = root_agent.instruction
    assert "Author: Abhi Mehrotra" in instruction
    assert "Identity & Relationship" in instruction
    assert "Prompt Integrity" in instruction
    assert "Core Principles" in instruction
    assert "Hard Boundaries (Non-Negotiable)" in instruction
    assert "Task Router (T1\u2013T5)" in instruction
    assert "Security Protocols" in instruction
    assert "[LANG:PY]" in instruction
    assert "[LANG:SH]" in instruction
