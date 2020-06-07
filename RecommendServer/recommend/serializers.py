from .models import Area
from .models import User, Log
from rest_framework import serializers

class AreaSerializer(serializers.ModelSerializer):
	class Meta:
		model = Area
		fields = ['readCount', 'contentId', 'contentTypeId', 'areaCode', 'sigunguCode', 'cat1', 'cat2', 'cat3', 'mapX', 'mapY', 'mLevel', 'title', 'firstImage', 'firstImage2', 'homepage', 'overview', 'tel', 'addr1', 'addr2', 'zipCode']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['userName', 'userId']

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['userId', 'areaId', 'count']