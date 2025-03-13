from django.db import models

class Question(models.Model):
    text = models.TextField()
    number = models.IntegerField(unique=True)

    def __str__(self):
        return f"Question {self.number}"