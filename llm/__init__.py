import os
import yaml
from llm.llm_reasoner import LLMReasoner, create_reasoner


def _load_config() -> dict:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "configs", "config.yaml",
    )
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


config = _load_config()

_reasoner_instance = None


def get_shared_reasoner() -> LLMReasoner:
    global _reasoner_instance
    if _reasoner_instance is None:
        _reasoner_instance = create_reasoner(
            base_url=config["llm"]["api_base"],
            model_name=config["llm"]["model_name"],
            api_key=config["llm"].get("api_key", "not-needed"),
            temperature=config["llm"].get("temperature", 0.1),
        )
    return _reasoner_instance
