# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0005_conversation_endpoint_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='product_type_breakdown',
            field=models.JSONField(blank=True, help_text='JSON structure containing confidence scores for all problem types (A, B, C, Other)', null=True),
        ),
    ] 