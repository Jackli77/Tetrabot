from detectors.prefix.base_command import BaseCommand


# The !chat command: forwards the user's message to the local Ollama LLM
# (qwen3:4b) and replies in the channel with the generated answer.
# The shared logic lives in controllers.commands.cmd_chat (it also serves /chat).
# Usage: !chat <message>
class Chat(BaseCommand):

    def __init__(self):
        # Short description shown in the help embed.
        description = "Envoie ton message au chatbot local (Ollama) et affiche sa réponse dans le salon"
        # The command takes at least one argument (the message to chat with).
        params = ["message"]
        super().__init__(description, params)