from django.contrib import admin
from .models import Conversation

# Register your models here.
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('email', 'test_type', 'problem_type', 'think_level', 'feel_level', 'created_at')
    list_filter = ('test_type', 'problem_type', 'think_level', 'feel_level', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at',)
    
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ('created_at',)
