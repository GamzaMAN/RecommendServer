import pandas as pd
import numpy as np
import scipy
import sklearn
import json
import pymysql
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
import sklearn.metrics
from scipy import linalg, dot

from secretInfo import mysqlInfo

GLOBAL_PATH = "./recommend/recommender/_cache_data/"
LOCAL_PATH = "./_cache_data/"

import time

class UserItemSimilarityAnalyzer:
	def updateSimilarity(self, path=GLOBAL_PATH, isItemUpdated = False):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		# 아이템 속성 정
		if isItemUpdated:
			itemResult = self.makeItemProf(cursor, path)
		else:		
			try:
				file = open(path + "itemProf.tp", "rb")
				itemResult = pickle.load(file)
				file.close()
			except:
				itemResult = self.makeItemProf(cursor, path)

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

	def makeItemProf(self, cursor, path=GLOBAL_PATH, areaCode=0, sigunguCode=0, maxFeatures=50):
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

		file = open(path + "itemProf.tp", "wb")
		pickle.dump((itemProf, itemProfMat), file)
		file.close()
		
		return (itemProf, itemProfMat)

	def makeUserLog(self, cursor, itemProf):
		userLogs = self.getUserLog(cursor)

		# userLogs = pd.DataFrame(list(userLogs))
		userLogs = pd.DataFrame(userLogs)
		print(userLogs)
		userLogs.columns = ['userId', 'areaId', 'count']

		# 행렬화
		userAreaCount = userLogs.pivot(index='userId', columns='areaId', values='count').fillna(0)

		# userAreaCount Sparse화 : 
		# userAreaCount = userAreaCount.astype("Sparse[int]")

		# 추가되지 않은 아이템 리스트 생성
		toAddList = list()
		itemList = itemProf.index
		usersItemList = userAreaCount.columns

		for item in itemList:
			if item not in usersItemList:
				toAddList.append(item)

		# numpy로 더 필요한 크기 만큼 0*0 생성
		addX = userAreaCount.shape[0]
		addY = itemProf.shape[0] - userAreaCount.shape[1]

		# toAddDataFrame = pd.DataFrame(np.zeros((addX, addY)), columns=toAddList, index=userAreaCount.index, dtype="Sparse[int]")

		# ㅋㅋㅋㅋ어차피 np.zeros에서 에러남ㅋㅋㅋ Sparse는 나중에 사용자 늘어날때나 신경쓰고 지금은 걍 속도나 올ㄹ지ㅏ
		toAddDataFrame = pd.DataFrame(np.zeros((addX, addY)), columns=toAddList, index=userAreaCount.index)
		userAreaCount = pd.concat([userAreaCount, toAddDataFrame], axis=1)

		# userAreaCountMat = userAreaCount.sparse.to_dense().to_numpy()
		userAreaCountMat = userAreaCount.to_numpy()

		return (userAreaCount, userAreaCountMat)


	def getAreaInfo(self, cursor, areaCode=0, sigunguCode=0, removeFood = True):
		sql = "select contentId, overview, title from recommend_area"

		if removeFood:
			sql += " where cat1 not in (select cat1 from recommend_area where cat1=\"A05\")"

		if areaCode != 0:
			if removeFood:
				areaCond = " and areaCode=" + str(areaCode)
			else:
				areaCond = " where areaCode=" + str(areaCode)
			
			sql += areaCond

		if sigunguCode != 0:
			sggCond = " and sigunguCode=" + str(sigunguCode)
			sql += sggCond

		sql += ";"

		cursor.execute(sql)
		data = cursor.fetchall()
		return data

	def getUserLog(self, cursor, removeFood=True):
		sql = "select userId, areaId, count from recommend_log;"
		cursor.execute(sql)
		data = cursor.fetchall()

		if removeFood:
			sql = "select contentId from recommend_area where cat1=\"A05\";"
			cursor.execute(sql)
			excludes = cursor.fetchall()

			data = list(data)
			excludes = list(excludes)

			excludesFilter = list()

			for i in excludes:
				excludesFilter.append(i[0])

			data2 = list()

			for row in data:
				if row[1] not in excludesFilter:
					data2.append(row)

			return data2

		else:
			return list(data)


class ContentBaseRecommender:
	def getRecommendedArea(self, userId="jn8121@naver.com", areaCode=0, sigunguCode=0, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		userItemSim = pd.read_pickle(path + "userItemSimilarity.df")

		recommends = self.makeRecommends(cursor, userItemSim, userId, areaCode, sigunguCode)

		return recommends

	def makeRecommends(self, cursor, userItemSim, userId, areaCode, sigunguCode):
		tend = 0.65
		maxAreas = 20
		if areaCode == 0:
			maxAreas = 80
		elif sigunguCode==0:
			maxAreas = 40

		recommends = list()

		# 해당 사용자에 대한 여행지 contentId 추출

		itemIdSim = list()

		# get user Count 
		userIdNum = 0
		for uid in userItemSim.index:
			if uid == userId:
				break
			userIdNum += 1

		userItemSimMat = userItemSim.to_numpy()

		for i, cid in enumerate(userItemSim.columns):
			userTend = userItemSimMat[userIdNum][i]
			# userTend = userItemSim.loc[userId][cid]
			if userTend > tend:
				itemIdSim.append((cid, userTend))

		itemIdSim.sort(key = lambda element : element[1], reverse=True)

		# 지역에 따른 필터링

		toRecommendList = list()
		if areaCode != 0:
			sql = "select contentId from recommend_area where areaCode=" + str(areaCode)
			if sigunguCode != 0:
				sql += " and sigunguCode=" + str(sigunguCode)

			sql += ";"
			cursor.execute(sql)
			areasInAreaCode = cursor.fetchall()

			count = 0
			for area in areasInAreaCode:
				if count >= maxAreas:
					break

				for item in itemIdSim:
					if area[0] == item[0]:
						toRecommendList.append(area[0])
						count += 1
						break
		else:
			count = 0
			for item in itemIdSim:
				if count >= maxAreas:
					break

				toRecommendList.append(item[0])
				count +=1

		count = 0
		for cid in toRecommendList:
			itemDetail = self.getAreaDetails(cursor, cid)
			recommends.append(itemDetail)

			count +=1
			if count >= maxAreas:
				break

		return recommends

	def getAreaDetails(self, cursor, contentId):
		sql = "select * from recommend_area where contentId="
		sql += str(contentId)
		sql += ";"

		rst = cursor.execute(sql)
		data = cursor.fetchall()

		detail = self.makeDict(data[0])

		return detail

	def makeDict(self, data):
		result = dict()

		fields = ['contentId', 'contentTypeId', 'readCount', 'areaCode', 'sigunguCode', 'cat1', 'cat2', 'cat3', 'mapX', 'mapY', 'mLevel', 'title', 'firstImage', 'firstImage2', 'homepage', 'overview', 'tel', 'telName', 'addr1', 'addr2', 'zipCode']

		for i, field in enumerate(fields):
			result[field] = data[i]

		return result


class FirstTesterManager:
	def makeTestSet(self, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		categories = list()

		for i in range(3):
		    file = open(path + "cat"+str(i+1)+"Dict.dict","rb")
		    categories.append(pickle.load(file))
		    file.close()

		testSet = list()

		for c1 in range(categories[0]['area']['size']):
		    cat1Id=categories[0]['area']['items'][c1]
		    for c2 in range(categories[1][cat1Id]['size']):
		        cat2Id=categories[1][cat1Id]['items'][c2]
		        for c3 in range(categories[2][cat2Id]['size']):
		            cat3Id=categories[2][cat2Id]['items'][c3]

		            sql = "select * from recommend_area where cat3="
		            sql += "\"" + cat3Id +"\" "
		            sql += "and readCount = (select max(readCount) from recommend_area where cat3="
		            sql += "\"" + cat3Id +"\" );"

		            qResult = cursor.execute(sql)

		            if qResult > 0:
		            	areas = cursor.fetchall()
		            	# 2가 readCount

		            	testArea = self.makeDict(areas[0])

		            	testSet.append(testArea)

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
	start = time.time()
	analyzer = UserItemSimilarityAnalyzer()
	analyzer.updateSimilarity(LOCAL_PATH)
	print("makeUpdateTime: ", time.time() - start)
	
	# start = time.time()
	
	# recommender = ContentBaseRecommender()
	# recommends = recommender.getRecommendedArea("5ee0cb7494b9c82efaff9d67", 38, 13, LOCAL_PATH)
	# print("user1")
	# for area in recommends:
	# 	print(area['title'])

	# print("user2")
	# recommends = recommender.getRecommendedArea("5ee4d1626ade7e66eee5ed82", 38, 13, LOCAL_PATH)
	# for area in recommends:
	# 	print(area['title'])

	# print("getRecommendTime: ", time.time() - start)

	# start = time.time()
	
	# recommender = ContentBaseRecommender()
	# recommends = recommender.getRecommendedArea("jn8121@naver.com", 32, 0, LOCAL_PATH)
	# print(len(recommends))
	
	# print(time.time() - start)

	# start = time.time()
	
	# recommender = ContentBaseRecommender()
	# recommends = recommender.getRecommendedArea("jn8121@naver.com", 0, 0, LOCAL_PATH)
	# print(len(recommends))
	
	# print(time.time() - start)

	# userItemSim = pd.read_pickle(LOCAL_PATH + "userItemSimilarity.df")
	# print(userItemSim[1758000])
	

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
	# print(test_dict)