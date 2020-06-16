class RecommendMerger:
	def merge(self, contentbased, collaborated):
		mergedRecommends = contentbased

		for colAreaObj in collaborated:
			isExist = False
			for mgAreaObj in mergedRecommends:
				if colAreaObj['contentId'] == mgAreaObj['contentId']:
					isExist = True

			if isExist:
				continue
			else:
				mergedRecommends.append(colAreaObj);

		return mergedRecommends

if __name__ == "__main__":
	list1 = [{'contentId':1}, {'contentId':2}, {'contentId':3}, {'contentId':4}, {'contentId':5}]
	list2 = [{'contentId':3}, {'contentId':4}, {'contentId':5}, {'contentId':6}, {'contentId':7}]

	merger = RecommendMerger()
	rst = merger.merge(list1,list2)

	print(rst)