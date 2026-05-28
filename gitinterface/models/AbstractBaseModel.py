from django.db import models
from gitinterface.models import User
class AbstractBaseModel(models.Model):
    last_modified_date = models.DateTimeField(auto_now=True)
    created_date = models.DateTimeField(auto_now_add=True)

    created_user = models.ForeignKey(to='gitinterface.User', on_delete=models.CASCADE, related_name='+')
    last_modified_user = models.ForeignKey(to='gitinterface.User', on_delete=models.CASCADE, related_name='+')

    class Meta:
        abstract = True