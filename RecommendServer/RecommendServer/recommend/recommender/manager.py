import collaborative, contentbase, merge, route
import time

LOCAL_PATH = "./_cache_data/"

def recommendTest():
	start = time.time()

	colRecommender = collaborative.CollaborativeRecommender()
	colRecommends = colRecommender.getRecommendedArea("jn8121@naver.com", 32,1, LOCAL_PATH)
	conRecommender = contentbase.ContentBaseRecommender()
	conRecommends = conRecommender.getRecommendedArea("jn8121@naver.com", 32,1, LOCAL_PATH)

	merger = merge.RecommendMerger()

	recommends = merger.merge(colRecommends, conRecommends)
	print(recommends[0]['contentId'])

	rOpt = route.RouteOptimizer()
	rst = rOpt.getOptimizedRoute(recommends)
	print(rst[0][0]['contentId'])

	print("total: ", time.time() - start)

def update():
	colUpdater = collaborative.UserRelationAnalyzer()
	colUpdater.updatePrediction(LOCAL_PATH)
	conUpdater = contentbase.UserItemSimilarityAnalyzer()
	conUpdater.updateSimilarity(LOCAL_PATH)

if __name__ == "__main__":
	update()