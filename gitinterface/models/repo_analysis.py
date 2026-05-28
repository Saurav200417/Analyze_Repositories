from django.db import models
from pgvector.django import VectorField

from gitinterface.models import User,AbstractBaseModel

class Repo_Analysis(AbstractBaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repo_analyses')
    repo_name = models.CharField(max_length=100)
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True
    )
    tree_sha = models.CharField(max_length=100, null=True, blank=True)
    content = models.TextField(blank=True)
    class Meta:
        db_table = "repo_analysis"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "repo_name"],
                name="unique_user_repo"
            )
        ]