import os
import sys
import bs4
import shlex
import pickle
import requests
import readline
import argparse
from getpass import getpass
from datetime import datetime
from prettytable import PrettyTable
from inc.algorithms import validalgs
from inc.header import header

# Functions

# Returns json of current jobs in escrow
def get_jobs(sortby = 'createdAt', algid = None, reverse = True):
	url = "https://hashes.com/escrow/viewjson/"
	json = requests.get(url).json()
	if algid is not None:
		json2 = []
		for rows in json:
			if str(rows['algorithmId']) in algid:
				json2.append(rows)
		json = json2
	json = sorted(json, key=lambda x : x[sortby], reverse=reverse)
	return json

# Downloads or prints jobs in escrow
def download(jobid, algid, file, printr):
	urls = []
	jobs = get_jobs()
	if jobid is not None:
		if "," in str(jobid):
			jobid = jobid.split(",")
		else:
			jobid = [jobid]
		for rows in jobs:
			if str(rows['id']) in jobid:
				urls.append(rows['leftList'])
				jobid.remove(str(rows['id']))
		if jobid:
			print (",".join(jobid) + " not valid jobs")
	if algid is not None:
		for rows in jobs:
			if str(rows['algorithmId']) == algid:
				urls.append(rows['leftList'])
		if not urls:
			print ("No jobs for " + validalgs[algid])
	if urls:
		if printr:
			for url in urls:
				req = requests.get("http://hashes.com"+url).text.rstrip()
				print(req)
		if file:
			try:
				with open(file, "ab+") as outfile:
					for url in urls:
						req = requests.get("http://hashes.com"+url, stream=True)
						for chunk in req.iter_content(1024):
							outfile.write(chunk)
					print ("Wrote hashes to: "+file)
			except OSError as e:
				print(e)

# Gets stats about hashes that are left in escrow
def get_stats(json):
	stats = {}
	for rows in json:
		algid = rows['algorithmId']
		neededleft = float(rows['maxCracksNeeded']) - float(rows['foundHashes']) if rows['foundHashes'] > 0 else rows['maxCracksNeeded']
		if algid in stats:
			found = stats[algid]['totalFound'] + rows['foundHashes']
			left = stats[algid]['totalLeft'] + rows['leftHashes']
			usd = float(stats[algid]['totalUSD']) + float(rows['pricePerHashUsd']) * neededleft
			btc = float(stats[algid]['totalBTC']) + float(rows['pricePerHash']) * neededleft
		else:
			found = rows['foundHashes']
			left = rows['leftHashes']
			usd = float(rows['pricePerHashUsd']) * neededleft
			btc = float(rows['pricePerHash']) * neededleft
		stats[algid] = {"totalFound": found, "totalLeft": left, "totalUSD": "{0:.3f}".format(float(usd)), "totalBTC": "{0:.7f}".format(float(btc))}
	table = PrettyTable()
	table.field_names = ["ID", "Algorithm", "Left", "Found", "Total Value"]
	table.align = "l"
	escrowleft = 0
	escrowfound = 0
	escrowbtcvalue = 0
	escrowusdvalue = 0
	for aid in stats:
		value = "₿"+stats[aid]['totalBTC'] + " / $" + stats[aid]['totalUSD']
		escrowleft += stats[aid]['totalLeft']
		escrowfound += stats[aid]['totalFound']
		escrowbtcvalue += float(stats[aid]['totalBTC'])
		escrowusdvalue += float(stats[aid]['totalUSD'])
		table.add_row([aid, validalgs[str(aid)], stats[aid]['totalLeft'], stats[aid]['totalFound'], value])
	print(table)
	print("Hashes left: "+str(escrowleft))
	print("Hashes found: "+str(escrowfound))
	print("Total value in escrow: ₿"+"{0:.7f}".format(escrowbtcvalue)+" / $"+"{0:.3f}".format(escrowusdvalue))

# Creates requests session for actions that require you to be logged into hashes.com
def login(email, password, rememberme):
	global session
	session = requests.Session()
	url = "https://hashes.com/en/login"
	get = session.get(url).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	csrf = bs.find('input', {'name': 'csrf_token'})['value']
	captchaid = bs.find('input', {'name': 'captchaIdentifier'})['value']
	captchaurl = bs.find(id="captcha").get("src")
	print("Please open the following link and enter the captcha. https://hashes.com"+captchaurl)
	captcha = input("Captcha Code: ")
	data = {"email": email, "password": password, "csrf_token": csrf, "captcha": captcha, "captchaIdentifier": captchaid, "ddos": "fi", "submitted": "1"}
	post = session.post(url, data=data).text
	bs2 = bs4.BeautifulSoup(post, features="html.parser")
	error = bs2.find("div", {"class": "my-center alert alert-dismissible alert-danger"})
	error2 = bs2.find('p', attrs={'class':'mb-0'})
	if error is not None:
		print("".join([t for t in error.contents if type(t)==bs4.element.NavigableString]).strip())
		session = None
	elif error2 is not None:
		print(error2.text.strip())
		session = None
	else:
		print("Login successful.")
		if rememberme:
			with open("session.txt", "wb+") as sessionfile:
				pickle.dump(session.cookies, sessionfile)
			print("Wrote session data to: session.txt")

# Gets paid recovery history from escrow
def get_escrow_history(reverse, limit):
	uploadurl = "https://hashes.com/escrow/upload/"
	get = session.get(uploadurl).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	history = bs.find("table", { "id" : "paidRecovery" })
	table = PrettyTable()
	table.field_names = ["ID", "Created", "Algorithm", "Status", "Total Hashes", "Lines Processed", "Valid Finds", "Earned"]
	table.align = "l"
	for row in history.findAll("tr"):
		cells = row.findAll("td")
		if cells != []:
			cid = cells[0].find(text=True)
			date = cells[1].find(text=True)
			alg = cells[2].find(text=True)
			status = cells[3].find(text=True)
			total = cells[4].find(text=True)
			lines = cells[5].find(text=True)
			finds = cells[6].find(text=True)
			earned = cells[7].find(text=True)
			table.add_row([str(cid), str(date), str(alg), str(status), str(total), str(lines), str(finds), str(earned)])
	if reverse:
		table = table[::-1]
	if limit:
		table = table[0:limit]
	print(table)

# Upload found hashes to hashes.com
def upload(algid, file):
	uploadurl = "https://hashes.com/en/escrow/upload"
	get = session.get(uploadurl).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	csrf = bs.find('input', {'name': 'csrf_token'})['value']
	data = {"csrf_token": csrf, "algo": algid, "submitted": "true"}
	file = {"userfile": open(file, "rb")}
	post = session.post(uploadurl, files=file, data=data).text
	bs2 = bs4.BeautifulSoup(post, features="html.parser")
	success = bs2.find("div", {"class": "my-center alert alert-dismissible alert-success"})
	if success is not None:
		print("".join([t for t in success.contents if type(t)==bs4.element.NavigableString]).strip())
		print("Type 'history' to check progress.")
	else:
		print("Something happened while uploading file.")

# Confirm function
def confirm(message):
    c = input(message+" [y/n] ")
    if c == "y":
        return True
    if c == "n":
        return False

# Print header at start of script
print(header)

# Check if there is an exisiting session saved
if os.path.exists("session.txt"):
	if confirm("Load saved session?"):
		session = requests.session()
		with open("session.txt", "rb") as sessionfile:
			session.cookies.update(pickle.load(sessionfile))
		print("Loaded existing session from session.txt")
	else:
		session = None
else:
	session = None

# Start console
try:
	while True:
		cmd = input("hashes.com:~$ ")

		if cmd[0:8] == "get jobs":
			if len(cmd) > 8:
				args = cmd[8:]
				validsort = {"price": "pricePerHash", "total": "totalHashes", "left": "leftHashes", "found": "foundHashes", "lastcrack": "lastUpdate", "created": "createdAt"}
				parser = argparse.ArgumentParser(description='Get escrow jobs from hashes.com', prog='get jobs')
				parser.add_argument("-sortby", help='Parameter to sort jobs by.', default='created', choices=validsort)
				parser.add_argument("-algid", help='Algorithm to filter jobs by. Multiple can be give e.g. 20,300,220', default=None)
				parser.add_argument("-r", help='Reverse display order.', action='store_false')
				try:
					parsed = parser.parse_args(shlex.split(args))
					if parsed.algid is not None:
						if "," in parsed.algid:
							s = set(parsed.algid.split(","))
							d = s.difference(validalgs)
							s.intersection_update(validalgs)
							if s is not None:
								if len(d) > 0:
									print (",".join(d)+" are not valid algorithm IDs.")
								jobs = get_jobs(validsort[parsed.sortby], s, parsed.r)
							else:
								jobs = False
								print (",".join(d)+ " are not valid algorithm IDs.")
						else:
							if parsed.algid not in validalgs:
								jobs = False
								print (parsed.algid+" not a valid algorithm ID.")
							else:
						 		jobs = get_jobs(validsort[parsed.sortby], [parsed.algid], parsed.r)
					else:
						jobs = get_jobs(validsort[parsed.sortby], parsed.algid, parsed.r)
				except SystemExit:
					jobs = False
					None
			else:
				jobs = get_jobs()
			if jobs:
				table = PrettyTable()
				table.field_names = ["Created", "ID", "Algorithm", "Total", "Found", "Left", "Max", "Price Per Hash"]
				table.align = "l"
				for rows in jobs:
					ids = rows['id']
					created = datetime.strptime(rows['createdAt'], '%Y-%m-%d %H:%M:%S').strftime("%m/%d/%y")
					algorithm = rows['algorithmName']
					total = rows['totalHashes']
					found = rows['foundHashes']
					left = rows['leftHashes']
					maxcracks = rows['maxCracksNeeded']
					price = "₿"+rows['pricePerHash'] + " / $" + rows['pricePerHashUsd']
					table.add_row([created, ids, algorithm, total, found, left, maxcracks, price])
				print(table)
			else:
				print ("No jobs found.")
		if cmd[0:8] == "download":
				args = cmd[8:]
				parser = argparse.ArgumentParser(description='Download escrow jobs from hashes.com', prog='download')
				g1 = parser.add_mutually_exclusive_group(required=True)
				g1.add_argument("-jobid", help='Job ID to download. Multiple IDs can be seperated with a comma. e.g. 3,4,5.')
				g1.add_argument("-algid", help='Algorithm ID to download')
				g2 = parser.add_mutually_exclusive_group(required=True)
				g2.add_argument("-f", help='Download to file.')
				g2.add_argument("-p", help='Print to screen', action='store_true')
				try:
					parsed = parser.parse_args(shlex.split(args))
					if parsed.algid is not None:
						if parsed.algid not in validalgs:	
							print(parsed.algid+" is not a valid algorithm.")
						else:
							download(parsed.jobid, parsed.algid, parsed.f, parsed.p)
					else:
						download(parsed.jobid, parsed.algid, parsed.f, parsed.p)
				except SystemExit:
					None
		if cmd[0:4] == "help":
			table = PrettyTable()
			table.field_names = ["Command", "Description", "Flags"]
			table.align = "l"
			table.add_row(["get jobs", "Gets current jobs in escrow", "-algid, -sortby, -r, --help"])
			table.add_row(["download", "Download or print jobs from escrow", "-jobid, -algid, -f, -p, --help"])
			table.add_row(["stats", "Gets stats about hashes left in escrow", "-algid, --help"])
			table.add_row(["upload", "Uploads founds to hashes.com. Must be logged in.", "-algid, -file, --help"])
			table.add_row(["login", "Login to hashes.com for certain features", "-email -rememberme"])
			table.add_row(["history", "Show your history with escrow. Must be logged in.", "No flags"])
			table.add_row(["algs", "Gets algorithms hashes.com currently supports", "No flags"])
			table.add_row(["logout", "Clears logged in session", "No flags"])
			table.add_row(["clear", "Clears console", "No flags"])
			table.add_row(["exit", "Exits console", "No flags"])
			print(table)
		if cmd[0:5] == "stats":
			args = cmd[5:]
			parser = argparse.ArgumentParser(description='Get stats for hashes left in escrow from hashes.com', prog='stats')
			parser.add_argument("-algid", help='Algorithm ID to sort stats by. Multiple can be give e.g. 20,300,220', default=None)
			try:
				parsed = parser.parse_args(shlex.split(args))
				if parsed.algid is not None:
					if "," in parsed.algid:
						s = set(parsed.algid.split(","))
						d = s.difference(validalgs)
						s.intersection_update(validalgs)
						if s is not None:
							if len(d) > 0:
								print (",".join(d)+" are not valid algorithm IDs.")
							get_stats(get_jobs("createdAt", s))
						else:
							print (",".join(d)+ " are not valid algorithm IDs.")
					else:
						if parsed.algid not in validalgs:
							print(parsed.algid+" is not a vlaid algorithm.")
						else:
							get_stats(get_jobs("createdAt", [parsed.algid]))
				else:
					get_stats(get_jobs())
			except SystemExit:
				None
		if cmd[0:4] == "algs":
			print("List of algorithms hashes.com currently supports.")
			table = PrettyTable()
			table.field_names = ["ID", "Algorithm"]
			table.align = "l"
			for aid, name in validalgs.items():
				table.add_row([aid, name])
			print(table)
		if cmd[0:5] == "login":
			args = cmd[5:]
			parser = argparse.ArgumentParser(description='Login to hashes.com', prog='login')
			parser.add_argument("-email", help='Email to hashes.com account.', required=True)
			parser.add_argument("-rememberme", help='Save session to reload after closing console.', action='store_true')
			try:
				parsed = parser.parse_args(shlex.split(args))
				email = parsed.email
				password = getpass()
				login(email, password, parsed.rememberme)
			except SystemExit:
				None
		if cmd[0:6] == "upload":
			if session is not None:
				uploadurl = "https://hashes.com/escrow/upload/"
				args = cmd[6:]
				parser = argparse.ArgumentParser(description='Upload cracked hashes to hashes.com', prog='upload')
				parser.add_argument("-algid", help='Algorithm ID of cracked hashes', required=True, default=None)
				parser.add_argument("-file", help='File of cracked hashes', required=True, default=None)
				try:
					parsed = parser.parse_args(shlex.split(args))
					if parsed.algid not in validalgs:
						print (parsed.algid+" is not a valid algorithm ID")
					elif os.path.exists(parsed.file) == False:
						print (parsed.file+" does not exist")
					elif not parsed.file.lower().endswith(".txt"):
						print ("File type must be .txt")
					else:
						upload(parsed.algid, parsed.file)
				except SystemExit:
					None
			else:
				print("You are not logged in. Type 'help' for for info.")
		if cmd[0:7] == "history":
			if session is not None:
				args = cmd[7:]
				parser = argparse.ArgumentParser(description='View history of submitted cracks.', prog='history')
				parser.add_argument("-r", help='Reverse order of history.', required=False, action='store_true')
				parser.add_argument("-limit", help='Number of rows to limit results.', required=False, type=int)
				try:
					parsed = parser.parse_args(shlex.split(args))
					get_escrow_history(parsed.r, parsed.limit)
				except SystemExit:
					None
			else:
				print("You are not logged in. Type 'help' for info.")
		if cmd[0:6] == "logout":
			if session is not None:
				session = None
				print("Logged out.")
			else:
				print("You are not logged in.")
		if cmd[0:5] == "clear":
			os.system('cls||clear');
		if cmd[0:4] == "exit":
			break
except KeyboardInterrupt:
	False