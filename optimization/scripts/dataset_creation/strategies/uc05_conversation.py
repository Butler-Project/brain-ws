"""UC-5: Natural conversation — no command detected. Includes non-English."""

from .base_strategy import BaseStrategy


class UC05Conversation(BaseStrategy):
    use_case = "UC-5"
    dataset = "natural_language"

    CONVERSATION_PHRASES = [
        "Hello",
        "Hi there",
        "Good morning",
        "Good afternoon",
        "Good evening",
        "Hey",
        "What time is it?",
        "Tell me a joke",
        "What's your name?",
        "How are you?",
        "Thank you",
        "Thanks for the help",
        "Goodbye",
        "See you later",
        "What can you do?",
        "Who made you?",
        "What are you?",
        "How does this work?",
        "Nice to meet you",
        "What's the weather like?",
        "Can you sing a song?",
        "Do you like music?",
        "What is the meaning of life?",
        "Tell me something interesting",
        "Who are you?",
        "Are you a robot?",
        "How old are you?",
        "What's 2 plus 2?",
        "Who is the president?",
        "What day is today?",
        # Bad grammar conversation
        "helo",
        "how r u?",
        "wat can u do?",
        "thx for help",
        "wats ur name?",
        "who r u?",
        "goodby",
    ]

    NON_ENGLISH_PHRASES = [
        # Spanish
        "Llévame a la cocina",
        "Hola, ¿cómo estás?",
        "¿Dónde está el baño?",
        "Quiero ir a la oficina",
        "Muéstrame el edificio",
        "¿Qué lugares hay?",
        "Cancela la tarea",
        "Llévame de vuelta a casa",
        # French
        "Emmène-moi à la cuisine",
        "Bonjour, comment ça va?",
        "Où est la salle de bain?",
        # German
        "Bringe mich zur Küche",
        "Wo ist das Badezimmer?",
        "Hallo, wie geht es dir?",
        # Portuguese
        "Leve-me para a cozinha",
        "Onde fica o banheiro?",
        # Italian
        "Portami in cucina",
        "Dove si trova il bagno?",
        # Mixed English + other language
        "Take me to la cocina",
        "I want to go to el baño",
    ]

    def generate(self):
        entries = []
        expected = self.make_expected("model_response")

        for msg in self.CONVERSATION_PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "conversation",
            ))

        for msg in self.NON_ENGLISH_PHRASES:
            entries.append(self.entry(
                self.make_input(msg), expected, "non_english",
            ))

        return entries
