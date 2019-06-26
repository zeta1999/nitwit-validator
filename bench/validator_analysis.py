import argparse

import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from common.utils import *

sns.set()

STATUSES = {
	'false(unreach-call)': 0,
	'unknown': 1,
	'true': 2,
	'timeout': 3,
	'timeout (true)': 3,
	'timeout (error (7))': 3,
	'timeout (false(unreach-call))': 3,
	'exception': 4,
	'error (1)': 4,
	'error (2)': 4,
	'error (7)': 4,
	'error (invalid witness file)': 4,
	'assertion': 4,
	'out of memory': 5,
	'-': 6,
	0: 0,  # false
	245: 0,  # false, but not totally correct witness
	4: 1,  # parse error
	246: 1,  #
	244: 1,  # identifier undefined
	5: 2,  # error not reached
	250: 2,  # error not reached, witness in violation state
	9: 3,  # timeout
	241: 4,  # error, witness in sink
	242: 5,  # program finished, witness not in violation state
}
col_names = ['false', 'unknown', 'true', 't/o', 'error', 'o/m', 'not run']

RESULT_CODES = {
}
row_names = ['false', 'unknown', 'not reached', 't/o', 'sink', 'not in violation state']

VALIDATORS = {
	0: "CPAChecker",
	1: "Ultimate Automizer",
	2: "CPA-witness2test",
	3: "CProver",
	4: "CWValidator"
}
VALIDATORS_LIST = ["CPAChecker",
                   "Ultimate Automizer",
                   "CPA-witness2test",
                   "CProver",
                   "CWValidator"]

CPU_MULTIPLIER = 1.8 / 3.4


def adjust_to_cpu(time: float) -> float:
	return time * CPU_MULTIPLIER


def get_matching(all_results: List, validators: dict, outputmatched: str = None) -> Dict[str, dict]:
	by_witness = validators.keys()
	# witness_keys = [hash['witnessSHA'].lower() for key in by_witness for hash in validators[key]['results']]
	witness_keys = set(by_witness)

	matched = list(filter(lambda r: str(r[1]).partition('.json')[0] in witness_keys, all_results))
	matched_keys = list(map(lambda r: str(r[1]).partition('.json')[0], matched))
	if outputmatched is not None:
		with open(outputmatched, 'w') as fp:
			json.dump(matched, fp)
	for w in matched:
		validators[w[1].partition('.json')[0]]['results'] \
			.insert(4, dict({'cpu': adjust_to_cpu(w[3]), 'tool': 'CWValidator', 'status': w[0]}))
	print(f"I could match {len(matched)} out of {len(all_results)} witnesses")
	return {k: v for k, v in validators.items() if k in matched_keys}


def analyze_output_messages(matching: Dict[str, dict]):
	print(f"Analyze {len(matching)}")
	fig, axs = plt.subplots(nrows=2, ncols=2)
	for i in range(4):
		heatmap = np.zeros((6, 7), dtype=int)
		for w, c in matching.items():
			heatmap[STATUSES[c['results'][4]['status']], STATUSES[c['results'][i]['status']]] += 1
		dataframe = pd.DataFrame(data=heatmap, index=row_names, columns=col_names)
		ax = sns.heatmap(dataframe, annot=True, fmt="d", ax=axs[math.floor(i / 2)][i % 2], cmap="BuGn")
		ax.set_title(VALIDATORS[i])


def join_val_non_val(validated: dict, nonvalidated: dict) -> dict:
	result = {}
	for k in list(validated.keys()) + list(nonvalidated.keys()):
		val, nval = 0, 0
		if k in nonvalidated:
			nval = nonvalidated[k]
		if k in validated:
			val = validated[k]
		result[k] = (val, nval)
	# sorted_vals = sorted(list(result.keys()))
	# return sorted_vals, [[result[k][0], result[k][1]] for k in sorted_vals]
	return result


def analyze_by_producer(matching: Dict[str, dict]):
	print(f"Analyze by producer {len(matching)} witnesses")
	mux = pd.MultiIndex.from_product([VALIDATORS_LIST, ['val', 'nval']])
	df = pd.DataFrame(columns=mux)
	data = []
	for i in range(5):
		validated = {}
		nonvalidated = {}
		for w, c in matching.items():
			if STATUSES[c['results'][i]['status']] == 0:
				increase_count_in_dict(validated, c['creator'])
			else:
				increase_count_in_dict(nonvalidated, c['creator'])
		data.append(join_val_non_val(validated, nonvalidated))
	rows = set(np.asarray(list(map(lambda x: list(x.keys()), data))).flatten())
	for producer in rows:
		df.loc[producer] = [float('nan')] * len(VALIDATORS_LIST) * 2
	for i, d in enumerate(data):
		for k, v in d.items():
			df.at[k, (VALIDATORS_LIST[i], 'val')] = v[0]
			df.at[k, (VALIDATORS_LIST[i], 'nval')] = v[1]
	df.loc["Total"] = df.sum()
	print(df.to_latex())


def validator_result_selector(results: list, predicate_others, predicate_cwv) -> bool:
	for i in range(4):
		if not predicate_others(STATUSES[results[i]['status']]):
			return False
	if predicate_cwv(STATUSES[results[4]['status']]):
		return True


def analyze_unique_by_producer(matching: Dict[str, dict], diff_matching: Dict[str, dict] = None) -> Tuple[set, set, set, set]:
	print(f"Analyze unique results by producer for {len(matching)} witnesses")
	others_uval = set()
	cwv_uval = set()
	none_val = set()
	all_val = set()
	for w, c in matching.items():
		if validator_result_selector(c['results'], lambda x: x == 0, lambda x: x != 0):
			others_uval.add(w + '.json')
		if validator_result_selector(c['results'], lambda x: x != 0, lambda x: x == 0):
			cwv_uval.add(w + '.json')
		if validator_result_selector(c['results'], lambda x: x == 0, lambda x: x == 0):
			all_val.add(w + '.json')
		if validator_result_selector(c['results'], lambda x: x != 0, lambda x: x != 0):
			none_val.add(w + '.json')

	print(f"Uniquely validated by *others*: {len(others_uval)}")
	print(f"Uniquely validated by *CWValidator*: {len(cwv_uval)}")
	print(f"Validated by all: {len(all_val)}")
	print(f"Validated by none: {len(none_val)}\n")

	if diff_matching is not None:
		print(f"\nResults for diff:")
		diff_others, diff_cwv, diff_none, diff_all = analyze_unique_by_producer(diff_matching)
		print('-' * 40)
		print('Not in diff')
		print(f"Others: {others_uval.difference(diff_others)}")
		print(f"CWV: {cwv_uval.difference(diff_cwv)}")
		print(f"None: {none_val.difference(diff_none)}")
		print(f"All: {all_val.difference(diff_all)}")
		print()
		print('Not in original')
		print(f"Others: {diff_others.difference(others_uval)}")
		print(f"CWV: {diff_cwv.difference(cwv_uval)}")
		print(f"None: {diff_none.difference(none_val)}")
		print(f"All: {diff_all.difference(all_val)}")

	return others_uval, cwv_uval, none_val, all_val


def reject_outliers(data, m=2):
	return data[abs(data - np.mean(data)) < m * np.std(data)]


def analyze_times(matching: Dict[str, dict]):
	fig, axs = plt.subplots(nrows=2, ncols=3)
	# take just the successful ones
	for i in range(5):
		times = np.asarray(list(map(lambda x: float(x['results'][i]['cpu']),
		                            filter(lambda x: STATUSES[x['results'][i]['status']] == 0, matching.values()))))
		print(f"Validator {VALIDATORS[i]}:")
		print_stats(times)
		print("-" * 40)
		ax = sns.distplot(reject_outliers(times), kde=False, rug=True, ax=axs[i % 2][math.floor(i / 2)], color="green")
		ax.set_title(VALIDATORS[i])
		ax.set_xlabel("Time [s]")

	fig.delaxes(axs[1, 2])  # The indexing is zero-based here


def print_stats(times):
	print(f"Mean: {np.mean(times)}")
	print(f"Median: {np.median(times)}")
	print(f"Std dev: {np.std(times)}")
	print(f"In total: {np.sum(times)}")


def main():
	parser = argparse.ArgumentParser(description="Analyzes results of CWValidator and SV-COMP validators")
	parser.add_argument("-v", "--validators", required=True, type=str,
	                    help="The JSON file with results about SV-COMP validator runs.")
	parser.add_argument("-r", "--results", required=True, type=str,
	                    help="The directory with validation results of CWValidator.")
	parser.add_argument("-om", "--outputmatched", required=False, type=str,
	                    help="File where to write the matched files config.")
	parser.add_argument("-df", "--diff", required=False, type=str,
	                    help="Directory with other results to compare.")

	args = parser.parse_args()

	results = load_result_files(args.results)
	val, nval, bpar = results
	all = val + nval + bpar

	validators = load_validators_result_file(args.validators)
	if results is None or validators is None:
		return 1

	matching = get_matching(all, validators['byWitnessHash'], args.outputmatched)
	diff_matching = None
	if args.diff is not None:
		diff_results = load_result_files(args.diff)
		dfval, dfnval, dfbpar = diff_results
		diff_all = dfval + dfnval + dfbpar
		diff_validators = load_validators_result_file(args.validators)
		diff_matching = get_matching(diff_all, diff_validators['byWitnessHash'], args.outputmatched)

	######### ANALYSES ###########

	# analyze_output_messages(matching)

	# analyze_by_producer(matching)

	# analyze_times(matching)

	analyze_unique_by_producer(matching, diff_matching)

	plt.show()


if __name__ == "__main__":
	main()
