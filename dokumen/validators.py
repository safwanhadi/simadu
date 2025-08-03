from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files.base import File

def validate_file_size(value):
    filesize = value.size
    if filesize > 2621440:  # 2.5MB limit
        raise ValidationError("Ukuran maksimal file 2.5 MB")
    return value

class CustomFileField(models.FileField):
    def __init__(self, *args, **kwargs):
        self.validators.append(validate_file_size)
        super().__init__(*args, **kwargs)