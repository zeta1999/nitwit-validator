import argparse
import os
import sys
import json
from typing import Union, List, Tuple
import multiprocessing
import subprocess

from common.utils import process_results

WITNESSES_BY_PROGRAM_HASH_DIR = "witnessListByProgramHashJSON"
WITNESS_INFO_BY_WITNESS_HASH_DIR = "witnessInfoByHash"
WITNESS_FILE_BY_HASH_DIR = "witnessFileByHash"
SV_BENCHMARK_DIR = ""
VALIDATOR_EXECUTABLE = ""
EXECUTION_TIMEOUT = 0


def setup_dirs(dir: str, sv_dir: str, executable: str, timeout: float) -> bool:
	if not os.path.exists(dir) or not os.path.isdir(dir):
		print(f"The directory {dir} doesn't exist or is not a directory.", file=sys.stderr)
		return False

	global WITNESS_INFO_BY_WITNESS_HASH_DIR, WITNESSES_BY_PROGRAM_HASH_DIR, WITNESS_FILE_BY_HASH_DIR, SV_BENCHMARK_DIR, VALIDATOR_EXECUTABLE, EXECUTION_TIMEOUT
	WITNESS_INFO_BY_WITNESS_HASH_DIR = os.path.join(dir, WITNESS_INFO_BY_WITNESS_HASH_DIR)
	WITNESSES_BY_PROGRAM_HASH_DIR = os.path.join(dir, WITNESSES_BY_PROGRAM_HASH_DIR)
	WITNESS_FILE_BY_HASH_DIR = os.path.join(dir, WITNESS_FILE_BY_HASH_DIR)
	SV_BENCHMARK_DIR = os.path.join(sv_dir, 'c')
	VALIDATOR_EXECUTABLE = executable
	EXECUTION_TIMEOUT = timeout

	if not (os.path.exists(WITNESS_INFO_BY_WITNESS_HASH_DIR) and os.path.isdir(WITNESS_INFO_BY_WITNESS_HASH_DIR) and
	        os.path.exists(WITNESS_FILE_BY_HASH_DIR) and os.path.isdir(WITNESS_FILE_BY_HASH_DIR) and
	        os.path.exists(WITNESSES_BY_PROGRAM_HASH_DIR) and os.path.isdir(WITNESSES_BY_PROGRAM_HASH_DIR)):
		print(f"The directory {dir} doesn't contain the necessary directories.", file=sys.stderr)
		return False
	if not (os.path.exists(SV_BENCHMARK_DIR) and os.path.isdir(SV_BENCHMARK_DIR)):
		print(f"The directory {sv_dir} doesn't exist or isn't a directory.", file=sys.stderr)
		return False
	if not (os.path.exists(VALIDATOR_EXECUTABLE) and os.path.isfile(VALIDATOR_EXECUTABLE)):
		print(f"The executable {executable} doesn't exist or isn't a file")
		return False
	print("Directories found!")
	return True


def run_validator(config: Tuple[str, str, str]) -> Tuple[int, str]:
	witness, source, info_file = config
	with subprocess.Popen(f"{VALIDATOR_EXECUTABLE} {witness} {source}", shell=True,
	                      stdout=subprocess.DEVNULL,
	                      stderr=subprocess.DEVNULL) as process:
		try:
			process.communicate(timeout=EXECUTION_TIMEOUT)
		except subprocess.TimeoutExpired:
			process.kill()
		# outs, errs = process.communicate()

		return process.returncode, info_file


def run_bench_parallel(configs: List[Tuple[str, str, str]]) -> List[Tuple[int, str]]:
	with multiprocessing.Pool() as pool:
		results = pool.map(run_validator, configs)
	return results


def get_bench_params(exec_limit: Union[int, None]) -> List[Tuple[str, str, str]]:
	erroneous = 0
	existent = 0
	sv_bench_files = 0
	sv_bench_not_found = 0
	configs_to_run = []

	with os.scandir(WITNESS_INFO_BY_WITNESS_HASH_DIR) as it:
		for entry in it:
			if entry.name.startswith('.') or not entry.is_file():
				print(f"{entry.name} is not a file.")
				continue
			with open(entry.path) as f:
				jObj = json.load(f)
				try:
					if 'witness-sha256' in jObj:
						# check if file in witnessFileByHash exists
						path_to_witness_file = \
							os.path.join(WITNESS_FILE_BY_HASH_DIR, f'{jObj["witness-sha256"]}.graphml')
						if not os.path.isfile(path_to_witness_file):
							print(f"{path_to_witness_file} did not exist")
							continue
						existent = existent + 1

						if 'programfile' in jObj and 'programhash' in jObj:
							programfile = str(jObj['programfile'])
							if not programfile.endswith(".c") \
									or not str(
								jObj['specification']) == "CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )":
								continue  # not a reachability C verification file

							sv_regexp_location = programfile.find("sv-benchmarks/c/")
							if not sv_regexp_location == -1:
								path_to_source_code = os.path.join(SV_BENCHMARK_DIR, programfile[
								                                                     sv_regexp_location + len(
									                                                     "sv-benchmarks/c/"):])
								if os.path.isfile(path_to_source_code):
									sv_bench_files = sv_bench_files + 1

									# run the validator with the found witness and source code
									configs_to_run.append((path_to_witness_file, path_to_source_code, entry.name))
								else:
									print(f"SV-COMP file {path_to_source_code} not found!")
									sv_bench_not_found = sv_bench_not_found + 1
							else:
								erroneous = erroneous + 1

					else:
						erroneous = erroneous + 1
				except Exception as e:
					print(f"Error while processing {entry.name}: {e}")
			if exec_limit is not None and sv_bench_files >= exec_limit:
				break

		print(f"Found {erroneous} erroneous files. {existent} witness files existed.")
		print(
			f"Prepared {sv_bench_files} SV-COMP files with safety properties checking. Not found {sv_bench_not_found}.")
		print("-------------------------------------------------------------------")
	return configs_to_run


def main():
	parser = argparse.ArgumentParser(description="Runs the CWValidator on SV-Benchmark")
	parser.add_argument("-w", "--witnesses", required=True, type=str, help="The directory with unzipped witnesses.")
	parser.add_argument("-e", "--exec", required=True, type=str, help="The CWValidator executable.")
	parser.add_argument("-sv", "--sv_benchmark", required=True, type=str, help="The SV-COMP benchmark source files.")
	parser.add_argument("-to", "--timeout", required=False, type=float, default=300, help="Timeout for a validation.")
	parser.add_argument("-l", "--limit", required=False, type=int, default=None,
	                    help="Limit of the number of executions")
	# parser.add_argument("-c", "--config", required=True, type=str, help="The verifier configuration file.")

	args = parser.parse_args()
	if not setup_dirs(args.witnesses, args.sv_benchmark, args.exec, args.timeout):
		return 1

	configs = get_bench_params(args.limit)
	results = run_bench_parallel(configs)
	process_results(results, True)


if __name__ == "__main__":
	main()