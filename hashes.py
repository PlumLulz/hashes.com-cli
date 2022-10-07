import os
import re
import sys
import bs4
import time
import shlex
import pickle
import requests
import readline
import argparse
from getpass import getpass
from datetime import datetime
from binascii import a2b_base64
from prettytable import PrettyTable
from inc.algorithms import validalgs
from inc.header import header

# Functions

# Returns json of current jobs in escrow
def get_jobs(sortby = 'createdAt', algid = None, reverse = True):
	url = "https://hashes.com/en/escrow/viewjson/"
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

# Converts data URI to binary and saves to jpeg
def save_captcha(uri):
	base64 = uri.split(",", 1)[1]
	binary = a2b_base64(base64)
	with open("captcha.jpg", "wb+") as img:
		img.write(binary)
	print("Downloaded captcha image to 'captcha.jpg'")

# Creates requests session for actions that require you to be logged into hashes.com
def login(email, password, rememberme):
	global session
	session = requests.Session()
	url = "https://hashes.com/en/login"
	get = session.get(url).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	csrf = bs.find('input', {'name': 'csrf_token'})['value']
	captchaid = bs.find('input', {'name': 'captchaIdentifier'})['value']
	uri = bs.findAll("div", {"class": "input-group mb-3"})[2].img.get('src')
	save_captcha(uri)
	print("Please open the captcha image saved to the current directory and enter it below.")
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
		os.remove("captcha.jpg") 
		if rememberme:
			with open("session.txt", "wb+") as sessionfile:
				pickle.dump(session.cookies, sessionfile)
			print("Wrote session data to: session.txt")

# Gets paid recovery history from escrow
def get_escrow_history(reverse, limit, stats):
	uploadurl = "https://hashes.com/escrow/upload/"
	get = session.get(uploadurl).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	history = bs.find("table", { "id" : "paidRecovery" })
	data = []
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
			data.append([str(cid), str(date), str(alg), str(status), str(total), str(lines), str(finds), str(earned)])
	if stats:
		totalsub = 0
		totalvalid = 0
		totalearnedbtc = 0
		totalearnedfiat = 0
		algorithms = {}
		for row in data:
			split = row[7].split(" ", 1)
			btc = split[0]
			fiat = split[1][3:].rstrip(" USD)")
			totalsub += int(row[4])
			totalvalid += int(row[6])
			totalearnedbtc += float(btc)
			totalearnedfiat += float(fiat)
			if row[2] not in algorithms:
				algorithms[row[2]] = [row[4], row[6], btc, fiat]
			else:
				algorithms[row[2]] = [int(algorithms[row[2]][0]) + int(row[4]), int(algorithms[row[2]][1]) + int(row[6]), float(algorithms[row[2]][2]) + float(btc), float(algorithms[row[2]][3]) + float(fiat)]
		table = PrettyTable()
		table.field_names = ["Algorithm", "Hashes Submitted", "Valid Hashes Submitted", "Earned"]
		table.align = "l"
		for k,v in algorithms.items():
			formatbtc = "{0:.7f}".format(float(v[2]))
			formatfiat = "{0:.3f}".format(float(v[3]))
			table.add_row([k] + v[:-2] + ["₿"+formatbtc+" / $"+formatfiat])
		table.sortby = "Earned"
		table.reversesort = True
		print("USD prices are based on BTCs current price.")
		print(table)
		print("Total hashes submitted: %s" % (totalsub))
		print("Total valid hashes submitted: %s" % (totalvalid))
		print("Total earned: ₿%s / $%s" % ("{0:.7f}".format(totalearnedbtc), "{0:.3f}".format(totalearnedfiat)))
	else:
		table = PrettyTable()
		table.field_names = ["ID", "Created", "Algorithm", "Status", "Total Hashes", "Lines Processed", "Valid Finds", "Earned"]
		table.align = "l"
		for row in data:
			table.add_row(row)
		if reverse:
			table = table[::-1]
		if limit:
			table = table[0:limit]
		print("USD prices are based on BTCs current price.")
		print(table)

# Gets current balance in escrow
def get_escrow_balance():
	get = session.get("https://hashes.com/profile").text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	history = bs.find("table", { "class" : "table text-center" })
	rows = history.findAll("td")
	balance = rows[4].find(text=True)
	conversion = btc_to_usd(balance)
	print("BTC: ₿%s" % (balance))
	print("USD: $%s" % (conversion["converted"]))
	print("\nCurrent BTC Price: $%s" % (conversion["currentprice"]))


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

# Withdraw funds from hashes.com to BTC address.
def withdraw():
	url = "https://hashes.com/en/billing/withdraw"
	get = session.get(url).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	csrf = bs.find('input', {'name': 'csrf_token'})['value']
	maxamount = re.sub("[^0-9^.]", "", bs.find('div', {'class': 'col'}).text.strip("\n"))
	fee = "0.0003"
	btcaddr = input("Bitcoin Address: ")
	amount = input("Bitcoin Amount(Max: %s / $%s): " % (maxamount, btc_to_usd(maxamount)["converted"]))
	conversion = btc_to_usd(amount)
	if confirm("Are you sure you want to withdraw %s / $%s to %s? There will be a %s fee." % (amount, conversion["converted"], btcaddr, fee)):
		data = {"csrf_token": csrf, "address": btcaddr, "amount": amount, "submitted": "true"}
		post = session.post(url, data=data).text
		bs2 = bs4.BeautifulSoup(post, features="html.parser")
		error = bs2.find('p', attrs={'class':'mb-0'})
		error2 = bs2.find("div", {"class": "my-center alert alert-dismissible alert-danger"})
		success = bs2.find("div", {"class": "my-center alert alert-dismissible alert-success"})
		if error is not None:
			print(error.text.strip())
		elif error2 is not None:
			text = error2.text.replace("Alert", "").replace("×", "")
			print(text.strip())
		elif success is not None:
			text = success.text.replace("Alert", "").replace("×", "")
			print(text.strip())
		else:
			print("Something happened during withdraw request.")
	else:
		print("You have canceled your withdraw request.")

# Shows all withdraw requests
def withdraw_requests():
	url = "https://hashes.com/en/billing/withdraw"
	get = session.get(url).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	history = bs.find("table", { "id" : "paidRecovery" })
	table = PrettyTable()
	table.field_names = ["Created", "Address", "Status", "Amount", "Fee", "Final", "Transaction Hash"]
	table.align = "l"
	for row in history.findAll("tr"):
		cells = row.findAll("td")
		if cells != []:
			date = cells[0].find(text=True)
			address = cells[1].find(text=True)
			status = cells[2].find(text=True)
			amount = cells[3].find(text=True)
			fee = cells[4].find(text=True)
			final = cells[5].find(text=True)
			thash = cells[6].find(text=True)
			table.add_row([str(date), str(address), str(status), str(amount), str(fee), str(final), str(thash)])
	print(table)

# Watch status of job
def watch(jobid, start, length):
    data = []
    bid =[]
    # This is used to count how many lines are going to be displayed
    # Starts at 4 to account for the 3 line header and 1 line bottom
    count = 4
    jobid = jobid.split(",")
    elapsed = time.time() - start
    if elapsed >=  60 * length:
    	print("\033[2F\033[J", end="")
    	print("Watch completed on job IDs: %s\n" % (",".join(jobid)), end="")
    	return False
    for j in get_jobs():
        if str(j["id"]) in jobid:
            data.append(j)
            count += 1
            jobid.remove(str(j["id"]))
    if data:
    	table = PrettyTable()
    	table.field_names = ["ID", "Hashes Cracked"]
    	table.align = "l"
    	for row in data:
    		table.add_row([row['id'], row['foundHashes']])
    	print(table)
    	if len(jobid) > 0:
    		count += 1
    		print("Job IDs %s are no longer valid." % (",".join(jobid)))
    	return count
    else:
        print("Job IDs %s are no longer valid." % (",".join(jobid)))
        return False

# Converts BTC to USD
def btc_to_usd(btc):
	# BTC information provided by https://blockchain.info/
	url = "https://blockchain.info/ticker"
	resp = requests.get(url).json()
	currentprice = resp["USD"]["15m"]
	converted = "{0:.3f}".format(float(btc) * currentprice)
	return {"currentprice": currentprice, "converted": converted}

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
				parser.add_argument("-r", help='Reverse display order.', action='store_false')
				parser.add_argument("-limit", help='Rows to limit results by.', default=None, type=int)
				g = parser.add_mutually_exclusive_group()
				g.add_argument("-algid", help='Algorithm to filter jobs by. Multiple can be given e.g. 20,300,220', default=None)
				g.add_argument("-jobid", help='Job ID to filter jobs by. Multiple can be given e.g. 1,2,3,4,5', default=None)
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
					elif parsed.jobid is not None:
						if "," in parsed.jobid:
							jids = parsed.jobid.split(",")
						else:
							jids = [parsed.jobid]
						jobs = get_jobs(validsort[parsed.sortby], None, parsed.r)
						temp = []
						for j in jobs:
							if str(j["id"]) in jids:
								temp.append(j)
								jids.remove(str(j["id"]))
						jobs = temp
						if jids:
							print("No valid jobs for ids: " + ",".join(jids))
					else:
					 	jobs = get_jobs(validsort[parsed.sortby], parsed.algid, parsed.r)
					limit = parsed.limit
				except SystemExit:
					jobs = False
					None
			else:
				jobs = get_jobs()
				limit = None
			if jobs:
				table = PrettyTable()
				table.field_names = ["Created", "ID", "Algorithm", "Total", "Found", "Left", "Max", "Price Per Hash"]
				table.align = "l"
				for rows in jobs[0:limit] if limit else jobs:
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
			table.add_row(["get jobs", "Get current jobs in escrow", "-algid, -jobid, -sortby, -r, -limit, --help"])
			table.add_row(["download", "Download to file or print jobs from escrow", "-jobid, -algid, -f, -p, --help"])
			table.add_row(["stats", "Get stats about hashes left in escrow", "-algid, --help"])
			table.add_row(["watch", "Watch status of jobs (updates every 10 seconds)", "-jobid, -length, --help"])
			table.add_row(["algs", "Get the algorithms hashes.com currently supports", "-algid, -search, --help"])
			table.add_row(["login", "Login to hashes.com", "-email, -rememberme"])
			table.add_row(["upload", "Upload cracks to hashes.com *", "-algid, -file, --help"])
			table.add_row(["history", "Show history of submitted cracks *", "-limit, -r, -stats, --help"])
			table.add_row(["withdraw", "Withdraw funds from hashes.com to BTC address *", "No flags"])
			table.add_row(["withdrawals", "Show all withdrawal requests *", "No flags"])
			table.add_row(["balance", "Show BTC balance *", "No flags"])
			table.add_row(["logout", "Clear logged in session *", "No flags"])
			table.add_row(["clear", "Clear console", "No flags"])
			table.add_row(["exit", "Exit console", "No flags"])
			print(table)
			print("* = Must be logged in")
		if cmd[0:5] == "stats":
			args = cmd[5:]
			parser = argparse.ArgumentParser(description='Get stats for hashes left in escrow from hashes.com', prog='stats')
			parser.add_argument("-algid", help='Algorithm ID to sort stats by. Multiple can be given e.g. 20,300,220', default=None)
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
			args = cmd[4:]
			parser = argparse.ArgumentParser(description='List of all algorithms that hashes.com supports', prog='algs')
			parser.add_argument("-algid", help='Algorithm ID to lookup. Multiple can be given e.g. 20,300,220', default=None)
			parser.add_argument("-search", help='Search algorithm by name.', default=None)

			try:
				parsed = parser.parse_args(shlex.split(args))
				if parsed.algid:
					ids = parsed.algid.split(",")
				table = PrettyTable()
				table.field_names = ["ID", "Algorithm"]
				table.align = "l"

				for aid, name in validalgs.items():
					if parsed.algid:
						if aid in ids:
							table.add_row([aid, name])
							ids.remove(aid)
					elif parsed.search:
						if parsed.search.upper() in name.upper():
							table.add_row([aid, name])
					else:
						table.add_row([aid, name])

				if len(table.get_string()) > 75:
					print(table)
				else:
					if parsed.search:
						print("No results found for '%s'" % (parsed.search))
				if parsed.algid:
					if len(ids) > 0:
						print("%s not currently supported." % (",".join(ids)))
			except SystemExit:
				None
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
				parser.add_argument("-stats", help='See history stats.', required=False, action='store_true')
				try:
					parsed = parser.parse_args(shlex.split(args))
					get_escrow_history(parsed.r, parsed.limit, parsed.stats)
				except SystemExit:
					None
			else:
				print("You are not logged in. Type 'help' for info.")
		if cmd[0:5] == "watch":
				args = cmd[5:]
				parser = argparse.ArgumentParser(description='Watch status of job ID.', prog='watch')
				parser.add_argument("-jobid", help='Job ID to watch. Multiple can be given e.g. 29374,29294,8', required=True)
				parser.add_argument("-length", help='Length in minutes to watch job.', required=False, default=5, type=int)
				try:
					parsed = parser.parse_args(shlex.split(args))
					stime = time.time()

					# In order to use ANSI escape codes on Windows they must be activated first.
					# The easiest way that I have found is to simply run the color command first
					if sys.platform == 'win32':
						os.system("color")

					print ("Watching job IDs: %s\n" % (parsed.jobid))
					while True:
						count = watch(parsed.jobid, stime, parsed.length)
						if count == False:
							break
						time.sleep(10)
						print("\033[%sF\033[J" % (count), end="")
				except SystemExit:
					None
		if cmd[0:7] == "balance":
			if session is not None:
				get_escrow_balance()
			else:
				print("You are not logged in. Type 'help' for info.")
		if cmd == "withdraw":
			if session is not None:
				withdraw()
			else:
				print("You are not logged in. Type 'help' for info.")
		if cmd == "withdrawals":
			if session is not None:
				withdraw_requests()
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