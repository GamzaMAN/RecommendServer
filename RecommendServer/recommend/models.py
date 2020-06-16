import base64

from django.db import models

# Create your models here.
class Area(models.Model):
    contentId = models.IntegerField(primary_key=True, default = -1)
    contentTypeId = models.IntegerField(default = -1)
    readCount = models.IntegerField(default = 0) 
    areaCode = models.IntegerField(default = -1)
    sigunguCode = models.IntegerField(default = -1)
    cat1 = models.CharField(max_length=3)
    cat2 = models.CharField(max_length=6)
    cat3 = models.CharField(max_length=12)

    mapX = models.CharField(max_length=20)
    mapY = models.CharField(max_length=20)
    mLevel = models.CharField(max_length=10)

    title = models.CharField(max_length=100)
    firstImage = models.CharField(max_length=100)
    firstImage2 = models.CharField(max_length=100)
    homepage = models.CharField(max_length=400)
    overview = models.TextField()

    tel = models.CharField(max_length=20)
    telName = models.CharField(max_length=30)
    addr1 = models.CharField(max_length=50)
    addr2 = models.CharField(max_length=50)
    zipCode = models.CharField(max_length=30)

    def __str__(self):
        return '%s' % (self.title)


class User(models.Model):
    userId = models.CharField(max_length=50, primary_key=True, default="global")
    userName = models.CharField(max_length=30)

    def __str__(self):
        return '%s' % (self.userName)

class Log(models.Model):
    d_id = models.AutoField(primary_key=True)
    userId = models.CharField(max_length=30, default="n")
    areaId = models.IntegerField(default=-1)
    count = models.IntegerField(default=0)
    logTime = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s: %s' % (self.userId, self.areaId)

