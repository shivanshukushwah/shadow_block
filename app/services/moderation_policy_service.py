class ModerationPolicyService:
    MODES = {
        "strict": {
            "toxicity_threshold": 0.2,
            "block_on_anger": True,
            "block_on_abuse": True,
            "block_on_nsfw": True,
        },
        "medium": {
            "toxicity_threshold": 0.5,
            "block_on_anger": True,
            "block_on_abuse": True,
            "block_on_nsfw": False,
        },
        "lenient": {
            "toxicity_threshold": 0.8,
            "block_on_anger": False,
            "block_on_abuse": True,
            "block_on_nsfw": False,
        }
    }

    def get_policy(self, mode: str):
        return self.MODES.get(mode, self.MODES["medium"])