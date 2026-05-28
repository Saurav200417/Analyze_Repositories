from django.db import models
from pgvector.django import VectorField
from gitinterface.models import Chat , AbstractBaseModel
from gitinterface.utils.choices import ROLE_CHOICES

class Messages(AbstractBaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()

    # Embedding of this message's content (for similarity search)
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True
    )

    # Token count helps you manage context window limits
    token_count = models.IntegerField(default=0)

    # Message order within the chat
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sequence']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
