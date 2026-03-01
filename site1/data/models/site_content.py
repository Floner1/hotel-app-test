from django.db import models


class SiteContent(models.Model):
    content_key   = models.CharField(max_length=100, unique=True)
    content_value = models.TextField()
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'site_content'
        managed = False  # Create the table manually in SQL Server

    def __str__(self):
        return self.content_key
