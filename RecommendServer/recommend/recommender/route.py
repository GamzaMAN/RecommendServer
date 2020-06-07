from sklearn.cluster import KMeans
import numpy as np

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

if __name__ == "__main__":
	dict1 = {
		'area':[1,2,3,4],
		'detail':{
			1:{
				'mapX':10.152255,
				'mapY':10.212255
			},
			2:{
				'mapX':10.122255,
				'mapY':10.132255
			},
			3:{
				'mapX':10.112255,
				'mapY':10.112255
			},
			4:{
				'mapX':10.112255,
				'mapY':11.012255
			}
		}
	}

	routeOptimizer = RouteOptimizer()
	rst = routeOptimizer.getOptimizedRoute(dict1)
	print(rst)

