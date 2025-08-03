from django.db import models
from django.db.models import JSONField

class Conversation(models.Model):
    
    

    email = models.EmailField()
    time_spent = models.IntegerField(help_text="Time spent in conversation, in seconds")
    chat_log = models.JSONField(help_text="JSON structure containing the chat log")
    message_type_log = models.JSONField(help_text="JSON structure containing the message type log")
    product_type_breakdown = models.JSONField(help_text="JSON structure containing confidence scores for all problem types (A, B, C, Other)", null=True, blank=True)

    # scenario information
    test_type = models.TextField(max_length=20, default='general') # general or lulu
    problem_type = models.CharField(max_length=10, default='A') # A, B, C from machine learning model
    think_level = models.CharField(max_length=10, default='High') # High or Low
    feel_level = models.CharField(max_length=10, default='High') # High or Low
    created_at = models.DateTimeField(auto_now_add=True)
    endpoint_type = models.TextField(max_length=20, default='general')

    def __str__(self):
        return f"Conversation with {self.email} on {self.created_at}"
