from django.contrib.postgres.fields import ArrayField
from django.db import models

from .validators import validate_file_extension

class SnapPickle(models.Model):
    name = models.CharField(max_length=512)
    networks = ArrayField(models.CharField(max_length=512), default=list)
    onestop_ids = ArrayField(models.CharField(max_length=64), default=list)
    pub_date = models.DateTimeField('date published')
    pickleFileName = models.FilePathField(path="snapData/uploads", default="")
    snapFileName = models.FilePathField(path="snapData/uploads", default="")
    def __str__(self):
        return self.name

class Document(models.Model):
    name = models.CharField(max_length=255, blank=True, default='')
    document = models.FileField(upload_to='Data/zipFiles', validators=[validate_file_extension])
    onestop_id = models.CharField(max_length=64, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)