import pandas as pd
import numpy as np
import scipy
import sklearn
import json
import pymysql
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import sklearn.metrics
from scipy import linalg, dot

from secretInfo import mysqlInfo

GLOBAL_PATH = "./recommend/contentbase/_cache_data/"
LOCAL_PATH = "./_cache_data/"

class UserSimilarityAnalizer:
	def updateSimilarity(self, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		file = open(path + "areaCode.dict","rb")
		areaSet=pickle.load(file)
		file.close()

		file = open(path + "sigunguCode.dict","rb")
		sigunguSet=pickle.load(file)
		file.close()

		# 아이템 속성 정
		itemResult = self.makeItemProf(cursor)

		itemProf = itemResult[0]
		itemProfMat = itemResult[1]

		# 사용자log 행렬 생
		userResult = self.makeUserLog(cursor, itemProf)

		userLog = userResult[0]
		userLogMat = userResult[1]

		# 사용자 프로필 생상
		userProfMat = dot(userLogMat, itemProfMat)/linalg.norm(itemProfMat)

		# 추천 행렬 생성
		userItemSimMat = sklearn.metrics.pairwise.cosine_similarity(userProfMat, itemProfMat, dense_output=True)
		userItemSim = pd.DataFrame(userItemSimMat, columns=itemProf.index, index=userLog.index)

		userItemSim.to_pickle(path + "userItemSimilarity.df")

	def makeItemProf(self, cursor, areaCode=0, sigunguCode=0, maxFeatures=50):
		data = self.getAreaInfo(cursor,areaCode, sigunguCode)
		# print("[", len(data), "] 개", end=" >> ")
		if len(data) == 0:
			# print("No Areas")
			return -1

		areaInfo = pd.DataFrame(list(data))
		areaInfo.columns = ['contentId', 'overview', 'title']

		areaInfo = areaInfo.sort_values('contentId', ascending=True)

		TfIdfModel = TfidfVectorizer(max_features = maxFeatures, ngram_range=(0,3), sublinear_tf=True)
		itemProfByTfIdf = TfIdfModel.fit_transform(areaInfo['overview'])

		itemProfMat = itemProfByTfIdf.todense()

		itemProf = pd.DataFrame(itemProfMat)
		itemProf.index = areaInfo['contentId']
		
		return (itemProf, itemProfMat)

	def makeUserLog(self, cursor, itemProf):
		userLogs = self.getUserLog(cursor)

		userLogs = pd.DataFrame(list(userLogs))
		userLogs.columns = ['userId', 'areaId', 'count']

		# itemprof 와 사이즈 맞추기
		count = userLogs.index.size
		for areaId in itemProf.index:
			userLogs.loc[count] = ["_", areaId, 0]
			count+=1

		# sparse 데이터로 변환
		userLogs['count'] = userLogs['count'].astype("Sparse[int]")

		# 행렬화
		userAreaCount = userLogs.pivot(index='userId', columns='areaId', values='count').fillna(0)
		userAreaCount = userAreaCount.drop('_')

		userAreaCountMat = userAreaCount.sparse.to_dense().to_numpy()

		return (userAreaCount, userAreaCountMat)

	def getAreaInfo(self, cursor, areaCode=0, sigunguCode=0):
		sql = "select contentId, overview, title from recommend_area"

		if areaCode != 0:
			areaCond = " where areaCode=" + str(areaCode)
			sql += areaCond

		if sigunguCode != 0:
			sggCond = " and sigunguCode=" + str(sigunguCode)
			sql += sggCond

		sql += ";"

		cursor.execute(sql)
		data = cursor.fetchall()
		return data

	def getUserLog(self, cursor):
		sql = "select userId, areaId, count from recommend_log;"
		cursor.execute(sql)
		data = cursor.fetchall()

		return data


class AreaRecommender:
	def getRecommendedArea(self, userId="jn8121@naver.com", areaCode=0, sigunguCode=0, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		file = open(path + "areaCode.dict","rb")
		areaSet=pickle.load(file)
		file.close()

		file = open(path + "sigunguCode.dict","rb")
		sigunguSet=pickle.load(file)
		file.close()

		userItemSim = pd.read_pickle(path + "userItemSimilarity.df")

		recommends = self.makeRecommends(cursor, userItemSim, userId, areaCode, sigunguCode)

		return recommends

	def makeRecommends(self, cursor, userItemSim, userId, areaCode, sigunguCode):
		tend = 0.5
		maxAreas = 40
		if areaCode == 0:
			maxAreas = 80
		elif sigunguCode==0:
			maxAreas = 60

		recommends = dict()
		recommends['area'] = list()
		recommends['detail'] = dict()

		# 해당 사용자에 대한 여행지 contentId 추출

		itemIdSim = list()

		for uid in userItemSim.index:
			if uid == userId:
				for cid in userItemSim.columns:
					if userItemSim.loc[uid][cid] > tend:
						itemIdSim.append((cid, userItemSim.loc[uid][cid]))
				break

		itemIdSim.sort(key = lambda element : element[1], reverse=True)

		# 지역에 따른 필터링
		count = 0
		for item in itemIdSim:
			itemDetail = self.getAreaDetails(cursor, item[0], areaCode, sigunguCode)

			if type(itemDetail) == dict:
			# 상위부터 순서대로 딕셔너리에 넣음
				recommends['area'].append(item[0])
				recommends['detail'][item[0]] = itemDetail

				count +=1
				if count >= maxAreas:
					break

		return recommends

	def getAreaDetails(self, cursor, contentId, areaCode, sigunguCode):
		sql = "select * from recommend_area where contentId="
		sql += str(contentId)

		if areaCode != 0:
			sql += " and areaCode="
			sql += str(areaCode)

			if sigunguCode !=0:
				sql += " and sigunguCode="
				sql += str(sigunguCode)

		sql += ";"

		rst = cursor.execute(sql)

		if rst > 0:
			data = cursor.fetchall()
			detail = self.makeDict(data[0])
			return detail
		else:
			return -1

	def makeDict(self, data):
		result = dict()

		fields = ['contentId', 'contentTypeId', 'readCount', 'areaCode', 'sigunguCode', 'cat1', 'cat2', 'cat3', 'mapX', 'mapY', 'mLevel', 'title', 'firstImage', 'firstImage2', 'homepage', 'overview', 'tel', 'telName', 'addr1', 'addr2', 'zipCode']

		for i, field in enumerate(fields):
			result[field] = data[i]

		return result


class RouteOptimizer:
	def __init__(self):
		self.INF = 987654321

	def getOptimizedRoute(self, recommends):
		recommendsList = self.clusterAreas(recommends)

		for clusteredRecommends in recommendsList:
			clusteredRecommends['area'] = self.sortAreasByTSP(clusteredRecommends)

		return recommendsList

	def clusterAreas(self, recommends, targetAreaNum=4):
		areaSize = len(recommends['area'])
		clusterSize = areaSize//targetAreaNum

		mapXY = list()

		for cid in recommends['area']:
			curInfo = recommends['detail'][cid]
			mapXY.append([curInfo['mapX'], curInfo['mapY']])


		routeSet = KMeans(n_clusters=clusterSize, random_state=0).fit(mapXY)


		numOfSet = [0 for _ in range(clusterSize)]

		for label in routeSet.labels_:
			numOfSet[label] += 1


		targetLabels = list()
		for i, n in enumerate(numOfSet):
			if n <= 16 and n >= targetAreaNum:
				targetLabels.append(i)


		recommendsList = list()

		for k in range(len(targetLabels)):
			clusteredRecommends = dict()
			clusteredRecommends['area'] = list()
			clusteredRecommends['detail'] = dict()

			for i, cid in enumerate(recommends['area']):
				if routeSet.labels_[i] == targetLabels[k]:
					clusteredRecommends['area'].append(cid)
					clusteredRecommends['detail'][cid] = recommends['detail'][cid]

			recommendsList.append(clusteredRecommends)

		return recommendsList


	def sortAreasByTSP(self, clusteredRecommends):
		N = len(clusteredRecommends['area'])
		board = np.zeros( (N,N) ) 

		for i, cid in enumerate(clusteredRecommends['area']):
			fromX = float(clusteredRecommends['detail'][cid]['mapX'])*1000
			fromY = float(clusteredRecommends['detail'][cid]['mapY'])*1000

			for j, tCid in enumerate(clusteredRecommends['area']):
				toX = float(clusteredRecommends['detail'][tCid]['mapX'])*1000
				toY = float(clusteredRecommends['detail'][tCid]['mapY'])*1000

				board[i][j] = ((fromX - toX)**2 + (fromY - toY)**2)**0.5

		route = list()
		minDist = self.INF
		start = -1

		for k in range(N):
			DP = [[None]*(1<<N) for _ in range(N)]
			route.append([[-1]*(1<<N) for _ in range(N)])

			c = self.TSP(k,(1<<k), route[k], DP, board, N)

			if c < minDist:
				minDist = c
				start = k

		minRoute = list()
		self.getRoute(start,(1<<start),route[start],minRoute)

		rstAreaList = list()

		for i in minRoute:
			rstAreaList.append(clusteredRecommends['area'][i])

		return rstAreaList

	def TSP(self, cur, visited, route, DP, board, N):
		if DP[cur][visited] is not None:
			return DP[cur][visited]

		if visited == (1 << N) - 1:
			return 0

		cost = self.INF
		for i in range(N):
			if visited & (1 << i) == 0 and board[cur][i] != 0:
				tmp = self.TSP(i, visited | (1<<i), route, DP, board, N)

				if (tmp+board[cur][i]) < cost:
					cost = tmp + board[cur][i]
					route[cur][visited] = i

		DP[cur][visited] = cost
		return cost

	def getRoute(self, cur, visited, route, minRoute):
		minRoute.append(cur)
		nextNode = route[cur][visited]
		if nextNode >= 0:
			self.getRoute(nextNode, visited | (1 << (nextNode)), route, minRoute)


class FirstTesterManager:
	def makeTestSet(self, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		categories = list()

		for i in range(3):
		    file = open(path + "cat"+str(i+1)+"Dict.dict","rb")
		    categories.append(pickle.load(file))
		    file.close()

		testSet = dict()
		testSet['area'] = list()
		testSet['detail'] = dict()

		for c1 in range(categories[0]['area']['size']):
		    cat1Id=categories[0]['area']['items'][c1]
		    for c2 in range(categories[1][cat1Id]['size']):
		        cat2Id=categories[1][cat1Id]['items'][c2]
		        for c3 in range(categories[2][cat2Id]['size']):
		            cat3Id=categories[2][cat2Id]['items'][c3]

		            sql = "select * from recommend_area where cat3="
		            sql += "\"" + cat3Id +"\";"

		            qResult = cursor.execute(sql)

		            if qResult > 0:
		            	areas = cursor.fetchall()
		            	testArea = self.makeDict(areas[0])

		            	testSet['area'].append(areas[0][0])
		            	testSet['detail'][areas[0][0]] = testArea

		file = open(path + "testSet.dict", "wb")
		pickle.dump(testSet,file)
		file.close()

	def getTestSet(self, path=GLOBAL_PATH):
		file = open(path + "testSet.dict","rb")
		testSet = pickle.load(file)
		file.close()

		return testSet

	def makeDict(self, data):
		result = dict()

		fields = ['contentId', 'contentTypeId', 'readCount', 'areaCode', 'sigunguCode', 'cat1', 'cat2', 'cat3', 'mapX', 'mapY', 'mLevel', 'title', 'firstImage', 'firstImage2', 'homepage', 'overview', 'tel', 'telName', 'addr1', 'addr2', 'zipCode']

		for i, field in enumerate(fields):
			result[field] = data[i]

		return result

if __name__ == '__main__':
	analyzer = UserSimilarityAnalizer()
	analyzer.updateSimilarity(LOCAL_PATH)
	
	# recommender = AreaRecommender()
	# recommends = recommender.getRecommendedArea("jn8121@naver.com", 32, 0, LOCAL_PATH)

	# print(recommends)

	# for cid in recommends['area']:
	# 	print(recommends['detail'][cid]['title'])
	
	# routeOptimizer = RouteOptimizer()
	# rtn_list = routeOptimizer.getOptimizedRoute(recommends)

	# for rtn_dict in rtn_list:
	# 	print("< SET >")
	# 	print(rtn_dict['area'])
	# 	for cid in rtn_dict['area']:
	# 		data = rtn_dict['detail'][cid]
	# 		print(data['mapX'], ", ", data['mapY'])

	# firstTesterManager = FirstTesterManager()
	# firstTesterManager.makeTestSet(LOCAL_PATH)
	# test_dict = firstTesterManager.getTestSet(LOCAL_PATH)
	# print("test")