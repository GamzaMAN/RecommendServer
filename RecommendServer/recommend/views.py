from django.http import Http404, HttpResponse, JsonResponse, QueryDict
from .models import Area, User, Log
from .serializers import AreaSerializer, UserSerializer, LogSerializer
from rest_framework import status
from rest_framework import generics
from rest_framework.parsers import JSONParser
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.filterset import FilterSet

from recommend.contentbase import recommender

class SearchAreaByQuery(generics.ListAPIView):
	queryset = Area.objects.all()
	serializer_class = AreaSerializer
	filter_backends = [ DjangoFilterBackend ]
	filter_fields = ['readCount', 'contentId', 'contentTypeId', 'areaCode', 'sigunguCode', 'cat1', 'cat2', 'cat3', 'mapX', 'mapY', 'mLevel', 'title', 'firstImage', 'firstImage2', 'homepage', 'overview', 'tel', 'addr1', 'addr2', 'zipCode']

	def isValidQueryParams(self, queryParams):
		if len(queryParams.keys()) == 0:
			return False

		for query in queryParams.keys():
			if query not in self.filter_fields:
				return False
		return True

	def get(self, request, *args, **kwargs):
		if not self.isValidQueryParams(request.query_params):
			return Response(status=status.HTTP_204_NO_CONTENT)
		return super(SearchAreaByQuery, self).get(request, *args, **kwargs)


@api_view(['GET', 'PUT', 'DELETE'])
def searchAreaById(request, cid):
    try:
        area = Area.objects.get(contentId=cid)
    except Area.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = AreaSerializer(area)
        return Response(serializer.data)

    # elif request.method == 'PUT':
    #     serializer = AreaSerializer(area, data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # elif request.method == 'DELETE':
    #     area.delete()
    #     return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def getAllAreas(request):
    if request.method == 'GET':
        areas = Area.objects.all()
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)

    # elif request.method == 'POST':
    #     serializer = AreaSerializer(data=request.data)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def getRecommendsByUser(request):
	if request.method == 'GET':
		userId = request.GET.get('userId',None)
		areaCode = request.GET.get('areaCode',0)
		sigunguCode = request.GET.get('sigunguCode',0)

		areaRecommender = recommender.AreaRecommender()
		routeOptimizer = recommender.RouteOptimizer()

		result = areaRecommender.getRecommendedArea(userId, areaCode, sigunguCode)

		for i in range(5):
			try:
				result = areaRecommender.getRecommendedArea(userId, areaCode, sigunguCode)
				
				if areaCode != 0:
					resultList = routeOptimizer.getOptimizedRoute(result)
					return Response(resultList)
				else:
					return JsonResponse(result)
			except:
				result = "get recommends fail"
				continue

		return Response(result, status=status.HTTP_204_NO_CONTENT)

	elif request.method == 'POST':
		return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def getTestSet(request):
	if request.method == 'GET':
		firstTesterManager = recommender.FirstTesterManager()

		for i in range(5):
			try:
				result = firstTesterManager.getTestSet()
			except:
				result = "get recommend fail"

		return JsonResponse(result)

	# elif request.method == 'POST':
	# 	return Response(status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET', 'POST'])
def join(request):
	if request.method == 'GET':
		return Response(status=status.HTTP_400_BAD_REQUEST)

	elif request.method == 'POST':
		data = JSONParser().parse(request)

		user = User.objects.filter(userId__exact=data["userId"])

		userData = { 'userName':data["userName"], 'userId':data["userId"] }
		userSerializer = UserSerializer(data=userData)

		if userSerializer.is_valid() and not user.exists():
			userSerializer.save()
			for log in data["log"]:
				logData = {'userId':data["userId"], 'areaId':log, 'count':1 }
				logSerializer = LogSerializer(data=logData)
				if logSerializer.is_valid():
					logSerializer.save()

			userSimilarityAnalizer = recommender.UserSimilarityAnalizer()
			userSimilarityAnalizer.updateSimilarity()

			return Response(status=status.HTTP_201_CREATED)
		else:
			return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def log(request):
	if request.method == 'GET':
		return Response(status=status.HTTP_400_BAD_REQUEST)

	elif request.method == 'POST':
		data = JSONParser().parse(request)
		user = Log.objects.filter(userId__exact=data["userId"])
		log = Log.objects.filter(userId__exact=data["userId"], areaId__exact=data["log"])

		if not user.exists():
			return Response(status=status.HTTP_400_BAD_REQUEST)

		if log.exists():
			log = Log.objects.get(userId=data["userId"], areaId=data["log"])
			log.count += 1
			log.save()

			logData = {'userId':data["userId"], 'areaId':data["log"], 'count':log.count }
			return Response(logData, status=status.HTTP_201_CREATED)
		else:
			logData = {'userId':data["userId"], 'areaId':data["log"], 'count':1 }
			logSerializer = LogSerializer(data=logData)

			if logSerializer.is_valid():
				logSerializer.save()

			return Response(logSerializer, status=status.HTTP_201_CREATED)