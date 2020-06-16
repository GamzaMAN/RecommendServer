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
from rest_framework import filters

from recommend.recommender import contentbase, collaborative, merge, route
from django.db.models import Q

@api_view(['GET', 'POST'])
def searchAreaByQuery(request):
	if request.method == 'GET':
		text = request.GET.get('search',None)
		areaCode = int(request.GET.get('areaCode',0))
		sigunguCode = int(request.GET.get('sigunguCode',0))

		if text is None:
			return Response(list())

		if areaCode == 0 and sigunguCode == 0:
			area = Area.objects.filter( Q(title__contains=text) | Q(overview__contains=text) )
		else:
			area = Area.objects.filter( Q(title__contains=text) | Q(overview__contains=text) )
			if areaCode != 0:
				area = area.filter(areaCode__exact=areaCode)
			if sigunguCode != 0:
				area = area.filter(sigunguCode__exact=sigunguCode)
			

		areaSerializer = AreaSerializer(area, many=True)

		return Response(areaSerializer.data)


@api_view(['GET', 'POST'])
def searchAreaById(request, cid):
	if request.method == 'GET':
		try:
			area = Area.objects.get(contentId=cid)
		except Area.DoesNotExist:
			return Response(status=status.HTTP_404_NOT_FOUND)

		serializer = AreaSerializer(area)
		return Response(serializer.data)

@api_view(['GET', 'POST'])
def getAllAreas(request):
    if request.method == 'GET':
        areas = Area.objects.all()
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)

@api_view(['GET', 'POST'])
def getRecommendsByUser(request):
	if request.method == 'GET':
		userId = request.GET.get('userId',None)
		areaCode = int(request.GET.get('areaCode',0))
		sigunguCode = int(request.GET.get('sigunguCode',0))

		print(userId)

		if userId is None:
			return Response(list())

		colRecommender = collaborative.CollaborativeRecommender()
		colRecommends = colRecommender.getRecommendedArea(userId,areaCode,sigunguCode)
		
		conRecommender = contentbase.ContentBaseRecommender()
		conRecommends = conRecommender.getRecommendedArea(userId,areaCode,sigunguCode)

		merger = merge.RecommendMerger()
		recommends = merger.merge(colRecommends, conRecommends)

		if areaCode != 0:
			routeOptimizer = route.RouteOptimizer()
			recommends = routeOptimizer.getOptimizedRoute(recommends)

		return Response(recommends)

	elif request.method == 'POST':
		return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def getTestSet(request):
	if request.method == 'GET':
		firstTesterManager = contentbase.FirstTesterManager()

		for i in range(5):
			try:
				result = firstTesterManager.getTestSet()
			except:
				result = "get recommend fail"

		return Response(result)


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

			similarityUpdater = contentbase.UserItemSimilarityAnalyzer()
			similarityUpdater.updateSimilarity()

			predictionUpdater = collaborative.UserRelationAnalyzer()
			predictionUpdater.updatePrediction()

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
		logs = data["log"]

		for dLog in logs:
			print(dLog)
			log = Log.objects.filter(userId__exact=data["userId"], areaId__exact=dLog)

			if not user.exists():
				return Response(status=status.HTTP_400_BAD_REQUEST)

			if log.exists():
				log = Log.objects.get(userId=data["userId"], areaId=dLog)
				log.count += 1
				log.save()

				logData = {'userId':data["userId"], 'areaId':dLog, 'count':log.count }
			else:
				logData = {'userId':data["userId"], 'areaId':dLog, 'count':1 }
				logSerializer = LogSerializer(data=logData)

				if logSerializer.is_valid():
					logSerializer.save()

		similarityUpdater = contentbase.UserItemSimilarityAnalyzer()
		similarityUpdater.updateSimilarity()

		predictionUpdater = collaborative.UserRelationAnalyzer()
		predictionUpdater.updatePrediction()

		return Response(logs, status=status.HTTP_201_CREATED)
