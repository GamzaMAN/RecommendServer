import pandas as pd
import numpy as np
import sklearn
from sklearn.neighbors import NearestNeighbors

import pymysql
from secretInfo import mysqlInfo

GLOBAL_PATH = "./recommend/recommender/_cache_data/"
LOCAL_PATH = "./_cache_data/"

class UserRelationAnalyzer:
	def updatePrediction(self, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		sql = "select userId, areaId, count from recommend_log;"

		cursor.execute(sql)
		result = cursor.fetchall()

		logs = pd.DataFrame(result)
		logs.columns = ["userId", "areaId", "count"]

		users = logs['userId'].unique().shape[0]
		areas = logs['areaId'].unique().shape[0]

		userAreaCounts = pd.DataFrame(np.zeros((users, areas)))
		userAreaCounts.index = logs['userId'].unique()
		userAreaCounts.columns = logs['areaId'].unique()

		for log in logs.itertuples():
			userAreaCounts.loc[log[1]][log[2]] = log[3]

		userAreaCountsMat = userAreaCounts.to_numpy()

		K = min(5, users)
		neighModel = NearestNeighbors(K,'cosine')
		neighModel.fit(userAreaCountsMat)

		nearestDistance, nearestUsers = neighModel.kneighbors(userAreaCountsMat, return_distance = True)

		userPredCountMat = np.zeros(userAreaCountsMat.shape)

		for i in range(userAreaCountsMat.shape[0]):
		    userPredCountMat[i,:] = nearestDistance[i].T.dot(userAreaCountsMat[nearestUsers][i])
		    userPredCountMat[i,:] /= np.array(np.abs(nearestDistance[i].T).sum(axis=0)).T

		userPredCount = pd.DataFrame(userPredCountMat)
		userPredCount.index = logs['userId'].unique()
		userPredCount.columns = logs['areaId'].unique()

		userPredCount.to_pickle(path + "userPrediction.df")

class CollaborativeRecommender:
	def getRecommendedArea(self, userId="jn8121@naver.com", areaCode=0, sigunguCode=0, path=GLOBAL_PATH):
		db = pymysql.connect(host='127.0.0.1', port=3306, user=mysqlInfo.DB_ID,passwd=mysqlInfo.DB_PW, db=mysqlInfo.DB_NAME, charset='utf8')
		cursor = db.cursor()

		userPredCount = pd.read_pickle(path + "userPrediction.df")

		recommends = self.makeRecommends(cursor, userPredCount, userId, areaCode, sigunguCode)

		return recommends

	def makeRecommends(self, cursor, userPredCount, userId, areaCode, sigunguCode):
		tend = userPredCount.loc[userId].to_numpy().mean()

		maxAreas = 40
		if areaCode == 0:
			maxAreas = 80
		elif sigunguCode==0:
			maxAreas = 60

		recommends = dict()
		recommends['area'] = list()
		recommends['detail'] = dict()

		# 해당 사용자에 대한 여행지 contentId 추출

		itemIdPred = list()

		for cid in userPredCount.columns:
			if userPredCount.loc[userId][cid] > tend:
				itemIdPred.append((cid, userPredCount.loc[userId][cid]))

		itemIdPred.sort(key = lambda element : element[1], reverse=True)

		# 지역에 따른 필터링
		count = 0
		for item in itemIdPred:
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

if __name__ == "__main__":
	userRelationAnalyzer = UserRelationAnalyzer()
	userRelationAnalyzer.updatePrediction(LOCAL_PATH)
	# areaRecommender = AreaRecommender()
	# recommends = areaRecommender.getRecommendedArea("jn8121@naver.com", 32, 0, LOCAL_PATH)
