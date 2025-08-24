from django.db import models

class ImagesRef(models.Model):
    ImageId = models.AutoField(primary_key=True)
    ImageData = models.BinaryField()  # Stores VARBINARY(MAX)

    class Meta:
        db_table = 'ImagesRef'
        managed = False  # This table already exists in SQL Server

class Hotel(models.Model):
    hotel_id = models.AutoField(primary_key=True)
    hotel_name = models.CharField(max_length=255)
    star_rating = models.IntegerField()
    hotel_address = models.CharField(max_length=255)
    established_date = models.DateField()
    phone = models.CharField(max_length=50)
    email = models.CharField(max_length=100)

    class Meta:
        db_table = 'hotel'
        managed = False  # This table already exists in SQL Server
