from django.db import models

class ImagesRef(models.Model):
    ImageId = models.AutoField(primary_key=True)
    ImageData = models.BinaryField()  # Stores VARBINARY(MAX)

    class Meta:
        db_table = 'ImagesRef'
        managed = False  # This table already exists in SQL Server
