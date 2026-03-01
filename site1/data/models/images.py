from django.db import models

class ImagesRef(models.Model):
    ImageId = models.AutoField(primary_key=True)
    ImageName = models.CharField(max_length=100, unique=True)  # Identifier e.g. 'food-1'
    ImageData = models.BinaryField()  # Stores VARBINARY(MAX)
    ImageContentType = models.CharField(max_length=50, default='image/jpeg')

    class Meta:
        db_table = 'ImagesRef'
        managed = False  # This table already exists in SQL Server
