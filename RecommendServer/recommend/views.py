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

# class SearchAreaByQuery(generics.ListAPIView):
# 	queryset = Area.objects.all()
# 	serializer_class = AreaSerializer
# 	search_fields = ['title', 'overview']
# 	filter_backends = [filters.SearchFilter]
	
# 	# filter_backends = [ DjangoFilterBackend ]
# 	# filter_fields = ['readCount', 'contentId', 'contentTypeId', 'areaCode', 'sigunguCode', 'cat1', 'cat2', 'cat3', 'mapX', 'mapY', 'mLevel', 'title', 'firstImage', 'firstImage2', 'homepage', 'overview', 'tel', 'addr1', 'addr2', 'zipCode']

# 	# def isValidQueryParams(self, queryParams):
# 	# 	if len(queryParams.keys()) == 0:
# 	# 		return False

# 	# 	for query in queryParams.keys():
# 	# 		if query not in self.filter_fields:
# 	# 			return False
# 	# 	return True

# 	# def get(self, request, *args, **kwargs):
# 	# 	if not self.isValidQueryParams(request.query_params):
# 	# 		return Response(status=status.HTTP_204_NO_CONTENT)
# 	# 	return super(SearchAreaByQuery, self).get(request, *args, **kwargs)

@api_view(['GET'])
def searchAreaByQuery(request):
	if request.method == 'GET':
		text = request.GET.get('search',None)
		areaCode = int(request.GET.get('areaCode',0))

		area = Area.objects.filter(areaCode__exact=areaCode)
		area = area.filter( Q(title__contains=text) | Q(overview__contains=text) )

		areaSerializer = AreaSerializer(area, many=True)

		print(areaSerializer)

		return Response(areaSerializer.data)


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
		areaCode = int(request.GET.get('areaCode',0))
		sigunguCode = int(request.GET.get('sigunguCode',0))

		contentBaseRecommender = contentbase.ContentBaseRecommender()
		collaborativeRecommender = collaborative.CollaborativeRecommender()
		recommendMerger = merge.RecommendMerger()
		routeOptimizer = route.RouteOptimizer()

		contentBasedRecommends = contentBaseRecommender.getRecommendedArea(userId, areaCode, sigunguCode)
		predictedRecommends = collaborativeRecommender.getRecommendedArea(userId, areaCode, sigunguCode)


		recommends = recommendMerger.merge(contentBasedRecommends, predictedRecommends)

		for i in range(5):
			try:
				contentBasedRecommends = contentBaseRecommender.getRecommendedArea(userId, areaCode, sigunguCode)
				predictedRecommends = collaborativeRecommender.getRecommendedArea(userId, areaCode, sigunguCode)

				recommends = recommendMerger.merge(contentBasedRecommends, predictedRecommends)
				
				if areaCode != 0:
					resultList = routeOptimizer.getOptimizedRoute(recommends)
					return Response(resultList)
				else:
					return JsonResponse(recommends)
			except:
				recommends = "get recommends fail"
				continue

		return Response(recommends, status=status.HTTP_204_NO_CONTENT)

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

			predictionUpdater = collaborative.UserRelationAnalyzer()
			predictionUpdater.updatePrediction()

			similarityUpdater = contentbase.UserItemSimilarityAnalyzer()
			similarityUpdater.updateSimilarity()

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
