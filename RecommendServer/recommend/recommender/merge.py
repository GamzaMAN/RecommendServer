class RecommendMerger:
	def merge(self, contentbased, collaborated):
		mergedRecommends = contentbased

		for cid in collaborated['area']:
			if cid not in contentbased['area']:
				mergedRecommends['area'].append(cid)
				mergedRecommends['detail'][cid] = collaborated['detail'][cid]

		return mergedRecommends

if __name__ == "__main__":
	dict1 = {'area':[1,2,3], 'detail':{1:{'X':1}, 2:{'X':2}, 3:{'X':3}}}
	dict2 = {'area':[2,3,4], 'detail':{2:{'X':2}, 3:{'X':3}, 4:{'X':4}}}

	merger = RecommendMerger()
	rst = merger.merge(dict1,dict2)

	print(rst)