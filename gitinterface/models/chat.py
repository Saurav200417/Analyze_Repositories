from django.db import models
from gitinterface.models import User,AbstractBaseModel
from pgvector.django import VectorField

class Chat(AbstractBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    # messages = models.TextField()
    # message_embeddings = VectorField(
    #     dimensions=1536,
    #     null=True,
    #     blank=True
    # )
    class Meta:
        ordering = ['-created_date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_chat_name'  
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.name}"