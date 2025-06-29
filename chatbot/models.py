from django.db import models
from django.db.models import JSONField

class Conversation(models.Model):
    email = models.EmailField()
    time_spent = models.IntegerField(help_text="Time spent in conversation, in seconds")
    chat_log = JSONField(help_text="JSON structure containing the chat log")
    message_type_log = JSONField(help_text="JSON structure containing the message type log")
    created_at = models.DateTimeField(auto_now_add=True)
    test_type = models.TextField()

    def __str__(self):
        return f"Conversation with {self.email} on {self.created_at}"
