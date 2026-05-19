_reasoner_instance = None

def get_shared_reasoner() -> LLMReasoner:
    global _reasoner_instance
    if _reasoner_instance is None:
        _reasoner_instance = create_reasoner(
            model_dir=config["llm"]["model_path"],
        )
    return _reasoner_instance