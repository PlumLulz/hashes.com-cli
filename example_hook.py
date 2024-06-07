# This is an example hook file for the hashes.com-cli websocket API implementation
# The code within the proccess_message function will be ran everytime a new job is added
# The message variable that is passed to the function is a dict with the results of new jobs
# Example of message result:
"""
{
	'success': True,
	'new': [
		{
			'id': 47338,
			'createdAt': '2024-01-19 01:22:58',
			'lastUpdate': '2024-01-19 01:22:58',
			'algorithmName': 'NTLM',
			'algorithmId': 1000,
			'totalHashes': 13,
			'foundHashes': 0,
			'leftHashes': 13,
			'currency': 'BTC',
			'pricePerHash': '0.00000241',
			'pricePerHashUsd': '0.1033',
			'maxCracksNeeded': 13,
			'leftList': '/unfound/47338-1705648981-75d62409-unfound.txt',
			'hints': ''
		}
	]
}
"""

import time

# Import any modules needed
import requests


def process_message(message):
	# Your code to process results here
	# This is a simple example to download the left list of new jobs that are posted
	# If your usergroup has access to hints and they are available it will also print hints of new jobs to the console

	if len(message['new']) > 0:
		for job in message['new']:
			jobid = job['id']
			filename = f"{jobid}_left.txt"

			with open(filename, "ab+") as leftfile:
				req = requests.get("http://hashes.com" + job['leftList'], stream=True)

				for chunk in req.iter_content(1024):
					leftfile.write(chunk)

			print(f"Left list for job id {jobid} downloaded to {filename}.")

			if hint := job.get('hints', None):
				print(f"Hint for job id {jobid}:\n{hint}")

			time.sleep(5)
