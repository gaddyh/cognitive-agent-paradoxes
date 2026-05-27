from tau2.agent.llm_agent import LLMAgent
from tau2.registry import registry


class MyLLMAgent(LLMAgent):
    """Custom agent scaffold.

    Currently identical to tau2's stock LLMAgent — subclasses it so tau2's
    run_task dispatcher routes it correctly (issubclass(MyLLMAgent, LLMAgent)).

    Override here as the decomposition evolves:
      - system_prompt property  → change instructions
      - generate_next_message   → multi-stage / decomposed reasoning
    """

    pass


registry.register_agent(MyLLMAgent, "my_llm_agent")
