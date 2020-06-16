import collaborative, contentbase, merge, route
import time

LOCAL_PATH = "./_cache_data/"

def recommendTest():
	colRecommender = collaborative.CollaborativeRecommender()
	colRecommends = colRecommender.getRecommendedArea("5ee0cb7494b9c82efaff9d67", 32,1, LOCAL_PATH)
	# colRecommends = colRecommender.getRecommendedArea("5ee4d1626ade7e66eee5ed82", 0,0, LOCAL_PATH)

	conRecommender = contentbase.ContentBaseRecommender()
	conRecommends = conRecommender.getRecommendedArea("5ee0cb7494b9c82efaff9d67", 32,1, LOCAL_PATH)
	# conRecommends = conRecommender.getRecommendedArea("5ee4d1626ade7e66eee5ed82", 0,0, LOCAL_PATH)
	# 5ee4d1626ade7e66eee5ed82

	merger = merge.RecommendMerger()

	recommends = merger.merge(colRecommends, conRecommends)

	# for area in recommends:
	# 	print(area['title'])

	rOpt = route.RouteOptimizer()
	rst = rOpt.getOptimizedRoute(recommends)

	for recommendSet in rst:
		print("<<< set >>>\n")
		for area in recommendSet:
			print(area['title'])



def update():
	colUpdater = collaborative.UserRelationAnalyzer()
	colUpdater.updatePrediction(LOCAL_PATH)
	conUpdater = contentbase.UserItemSimilarityAnalyzer()
	conUpdater.updateSimilarity(LOCAL_PATH)

if __name__ == "__main__":
	start = time.time()
	update()
	recommendTest()
	print("total: ", time.time() - start)