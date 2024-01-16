import os
import re
import sys
import bs4
import time
import json
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
def get_jobs(sortby = 'createdAt', algid = None, reverse = True, currency = None, self = False):
	if self == True:
		url = "https://hashes.com/en/api/jobs_self"
	else:
		url = "https://hashes.com/en/api/jobs?key=%s" % (apikey)
	json1 = requests.get(url).json()
	if json1["success"] == True:
		json1 = json1['list']
		if currency is not None:
			json3 = []
			for rows in json1:
				if str(rows['currency']) in currency.upper().split(","):
					json3.append(rows)
			json1 = json3
		if algid is not None:
			json2 = []
			for rows in json1:
				if str(rows['algorithmId']) in algid:
					json2.append(rows)
			json1 = json2
		json1 = sorted(json1, key=lambda x : x[sortby], reverse=reverse)
		return json1

# Downloads or prints jobs in escrow
def download(jobid, algid, file, printr, currency):
	urls = []
	jobs = get_jobs(currency = currency)
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
	elif algid is not None:
		for rows in jobs:
			if str(rows['algorithmId']) == algid:
				urls.append(rows['leftList'])
		if not urls:
			print ("No jobs for " + validalgs[algid])
	else:
		if currency is not None:
			for rows in jobs:
				urls.append(rows['leftList'])
	if urls:
		if printr:
			for url in urls:
				req = requests.get("http://hashes.com"+url).text.rstrip()
				print(req)
		if file:
			try:
				with open(file, "ab+") as outfile:
					for url in urls:
						req = requests.get("http://hashes.com"+url, stream=True, headers={'Accept-Encoding': None})
						total_size = int(req.headers.get('Content-Length'))
						downloaded = 0
						if total_size < 1048576:
							suffix = "KB"
							factor = float(1<<10)
						else:
							suffix = "MB"
							factor = float(1<<20)
						for chunk in req.iter_content(1024):
							outfile.write(chunk)
							downloaded += len(chunk)
							end = int(50 * downloaded / total_size)
							print("\r[%s%s]%s %s/%s %s   " % ('=' * end, ' ' * (50-end), "{0:.2f}".format(downloaded / factor), suffix, "{0:.2f}".format(total_size / factor), suffix), flush=True, end='')
					print ("\nWrote hashes to: "+file)
			except OSError as e:
				print(e)

# Gets stats about hashes that are left in escrow
def get_stats(json):
	stats = {}
	btc,xmr,ltc = 0,0,0
	for rows in json:
		algid = rows['algorithmId']
		currency = rows['currency']
		neededleft = float(rows['maxCracksNeeded']) - float(rows['foundHashes']) if rows['foundHashes'] > 0 else rows['maxCracksNeeded']
		if algid in stats:
			found = stats[algid]['totalFound'] + rows['foundHashes']
			left = stats[algid]['totalLeft'] + rows['leftHashes']
			usd = float(stats[algid]['totalUSD']) + float(rows['pricePerHashUsd']) * neededleft
			if currency == "BTC":
				btc = float(stats[algid]['totalBTC']) + float(rows['pricePerHash']) * neededleft
				xmr = float(stats[algid]['totalXMR'])
				ltc = float(stats[algid]['totalLTC'])
			elif currency == "XMR":
				xmr = float(stats[algid]['totalXMR']) + float(rows['pricePerHash']) * neededleft
				btc = float(stats[algid]['totalBTC'])
				ltc = float(stats[algid]['totalLTC'])
			elif currency == "LTC":
				ltc = float(stats[algid]['totalLTC']) + float(rows['pricePerHash']) * neededleft
				xmr = float(stats[algid]['totalXMR'])
				btc = float(stats[algid]['totalBTC'])
		else:
			found = rows['foundHashes']
			left = rows['leftHashes']
			usd = float(rows['pricePerHashUsd']) * neededleft
			if currency == "BTC":
				btc = float(rows['pricePerHash']) * neededleft
				xmr = 0
				ltc = 0
			elif currency == "XMR":
				xmr = float(rows['pricePerHash']) * neededleft
				btc = 0
				ltc = 0
			elif currency == "LTC":
				ltc = float(rows['pricePerHash']) * neededleft
				btc = 0
				xmr = 0
		stats[algid] = {"totalFound": found, "totalLeft": left, "totalUSD": "{0:.3f}".format(float(usd)), "totalBTC": "{0:.7f}".format(float(btc)), "totalXMR": "{0:.7f}".format(float(xmr)), "totalLTC": "{0:.7f}".format(float(ltc))}
	table = PrettyTable()
	table.field_names = ["ID", "Algorithm", "Left", "Found", "USD", "BTC", "XMR", "LTC"]
	table.align = "l"
	escrowleft,escrowfound,escrowusdvalue,escrowbtcvalue,escrowxmrvalue,escrowltcvalue = 0,0,0,0,0,0
	for aid in stats:
		escrowleft += stats[aid]['totalLeft']
		escrowfound += stats[aid]['totalFound']
		escrowusdvalue += float(stats[aid]['totalUSD'])
		escrowbtcvalue += float(stats[aid]['totalBTC'])
		escrowxmrvalue += float(stats[aid]['totalXMR'])
		escrowltcvalue += float(stats[aid]['totalLTC'])
		table.add_row([aid, validalgs[str(aid)], stats[aid]['totalLeft'], stats[aid]['totalFound'], "$"+stats[aid]['totalUSD'], stats[aid]['totalBTC'], stats[aid]['totalXMR'], stats[aid]['totalLTC']])
	print(table)
	print("Total hashes left: "+str(escrowleft))
	print("Total hashes found: "+str(escrowfound))
	print("Total USD value: $"+"{0:.3f}".format(escrowusdvalue))
	print("Total BTC value: %s / %s" % ("{0:.7f}".format(escrowbtcvalue), to_usd("{0:.7f}".format(escrowbtcvalue), "BTC")['converted'] if escrowbtcvalue > 0 else "$0.00"))
	print("Total XMR value: %s / %s" % ("{0:.7f}".format(escrowxmrvalue), to_usd("{0:.7f}".format(escrowxmrvalue), "XMR")['converted'] if escrowxmrvalue > 0 else "$0.00"))
	print("Total LTC value: %s / %s" % ("{0:.7f}".format(escrowltcvalue), to_usd("{0:.7f}".format(escrowltcvalue), "LTC")['converted'] if escrowltcvalue > 0 else "$0.00"))

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
	uri = bs.find("img", {"class": "img-fluid"}).get('src')
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
	uploadurl = "https://hashes.com/en/api/uploads?key=%s" % (apikey)
	get = requests.get(uploadurl).json()

	if get['success'] == True:
		data = []
		for row in get['list']:
			cid = row['id']
			date = row['date']
			alg = row['algorithm']
			status = row['status']
			total = row['totalHashes']
			finds = row['validHashes']
			btc = row['btc']
			xmr = row['xmr']
			ltc = row['ltc']
			data.append([str(cid), str(date), str(alg), str(status), str(total), str(finds), str(btc), str(xmr), str(ltc)])
		if stats:
			totalsub,totalvalid,totalearnedusd,totalearnedbtc,totalearnedxmr,totalearnedltc = 0,0,0,0,0,0
			algorithms = {}
			for row in data:
				usd = 0
				btc = row[6]
				xmr = row[7]
				ltc = row[8]
				totalsub += int(row[4])
				totalvalid += int(row[5])
				totalearnedusd += float(usd)
				totalearnedbtc += float(btc)
				totalearnedxmr += float(xmr)
				totalearnedltc += float(ltc)
				if row[2] not in algorithms:
					algorithms[row[2]] = [row[4], row[5], btc, xmr, ltc]
				else:
					algorithms[row[2]] = [int(algorithms[row[2]][0]) + int(row[4]), int(algorithms[row[2]][1]) + int(row[5]), float(algorithms[row[2]][2]) + float(btc), float(algorithms[row[2]][3]) + float(xmr), float(algorithms[row[2]][4]) + float(ltc)]
			table = PrettyTable()
			table.field_names = ["Algorithm", "Hashes Submitted", "Valid Hashes Submitted", "BTC", "XMR", "LTC"]
			table.align = "l"
			for k,v in algorithms.items():
				table.add_row([k, v[0], v[1], "{0:.7f}".format(float(v[2])), "{0:.7f}".format(float(v[3])), "{0:.7f}".format(float(v[4]))])
			table.sortby = "BTC"
			table.reversesort = True
			print("USD prices are based on BTCs current price.")
			print(table)
			print("Total hashes submitted: %s" % (totalsub))
			print("Total valid hashes submitted: %s" % (totalvalid))
			print("Total BTC value: %s / %s" % ("{0:.7f}".format(totalearnedbtc), to_usd("{0:.7f}".format(totalearnedbtc), "BTC")['converted'] if totalearnedbtc > 0 else "$0.00"))
			print("Total XMR value: %s / %s" % ("{0:.7f}".format(totalearnedxmr), to_usd("{0:.7f}".format(totalearnedxmr), "XMR")['converted'] if totalearnedxmr > 0 else "$0.00"))
			print("Total LTC value: %s / %s" % ("{0:.7f}".format(totalearnedltc), to_usd("{0:.7f}".format(totalearnedltc), "LTC")['converted'] if totalearnedltc > 0 else "$0.00"))

		else:
			table = PrettyTable()
			table.field_names = ["ID", "Created", "Algorithm", "Status", "Total Hashes", "Valid Finds", "BTC", "XMR", "LTC"]
			table.align = "l"
			for row in data:
				table.add_row(row)
			if reverse:
				table = table[::-1]
			if limit:
				table = table[0:limit]
			print(table)

# Gets current balance in escrow
def get_escrow_balance(p = True):
	get = requests.get("https://hashes.com/en/api/balance?key=%s" % (apikey)).json()
	if get['success'] == True:
		if p == True:
			table = PrettyTable()
			table.field_names = ["Currency", "Amount", "USD"]
			table.align = "l"
			get.pop('success')
			for currency,value in get.items():
				if float(value) > 0:
					usd  = to_usd(value, currency)["converted"]
				else:
					usd = "$0.00"
				table.add_row([currency, value, usd])
			print(table)
		elif p == False:
			return get


# Upload found hashes to hashes.com
def upload(algid, file):
	uploadurl =  "https://hashes.com/en/api/founds"
	data = {"key": apikey, "algo": algid}
	file = {"userfile": open(file, "rb")}
	post = requests.post(uploadurl, files=file, data=data).json()
	if post["success"] == True:
		print("File successfully uploaded.")
		print("Use the 'history' command to check the status.")
	else:
		print("Failed to upload file!")

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
	get = requests.get("https://hashes.com/en/api/withdrawals?key=%s" % (apikey)).json()
	table = PrettyTable()
	table.field_names = ["ID", "Created", "Status", "Currency", "Amount", "Final", "USD", "Transaction Hash"]
	table.align = "l"

	if get['success'] == True:
		for row in get['list']:
			wid = row['id']
			date = row['date']
			#address = row['']
			status = row['status']
			amount = "{0:.7f}".format(float(row['amount']))
			final = "{0:.7f}".format(float(row['afterFee']))
			thash = row['transaction']
			currency = row['currency']
			usd = to_usd(final, currency)['converted']
			table.add_row([wid, date, status, currency, amount, final, usd, thash])
	print(table)

# Watch status of job
def watch(jobid, start, length, prev):
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
    	if prev != None:
    		print("\033[2F\033[J", end="")
    	print("Job IDs %s are no longer valid." % (",".join(jobid)))
    	return False

# Check and update valid algorithm list
def update_algs():
	url = "https://hashes.com/en/algorithms/json"
	json2 = requests.get(url).json()
	if len(json2) > len(validalgs):
		temp = {}
		for alg in json2:
			temp[str(alg['id'])] = alg['algorithmName']
		new = set(temp) - set(validalgs)

		with open("./inc/algorithms.py", "w+") as test:
			test.write("validalgs = " + str(json.dumps(temp, indent=4)))
			print("\nNew algorithms added to list:")
			for nalg in new:
				print("%s: %s" % (nalg, temp[nalg]))
		print("\nIn order for update to be applied the script must be reloaded.")
		exit()

# Hash ID
def hashid(hashh, extended):
	url = "https://hashes.com/en/api/identifier?hash=%s&extended=%s" % (hashh, str(extended).lower())
	get = requests.get(url).json()
	if get['success'] == True:
		for algs in get['algorithms']:
			print(algs)
	elif get['success'] == False:
		print(get['message'])

# Hash lookup
def hash_lookup(hashes, outfile, printr, verbose):
	url = "https://hashes.com/en/api/search"
	data = {"key": apikey, "hashes[]": hashes}
	post = requests.post(url, data=data).json()
	if post['success'] == True:
		cost = post['cost']
		hcount = post['count']
		founds = post['founds']
		print("There were %s/%s hashes found." % (len(founds), hcount))
		print("Potential cost: %s" % (len(hashes) + 1))
		print("Actual cost: %s\n\n" % (cost))
		if len(founds) > 0:
			for found in founds:
				hashh = found['hash']
				salt = found['salt']
				plain = found['plaintext']
				alg = found['algorithm']
				if len(salt) == 0:
					line = "%s:%s" % (hashh, plain)
				else:
					line = "%s:%s:%s" % (hashh, salt, plain)
				if verbose == True:
					line += ":"+alg
				if printr == True:
					print(line)
				elif outfile is not None:
					with open(outfile, "a+") as ofile:
						ofile.write(line+"\n")
			if outfile is not None:
				print("Wrote search results to '%s'" % (outfile))
		else:
			print("No hashes found.")
	elif post['success'] == False:
		print(post['message'])


# Converts crypto to USD values
def to_usd(value, currency):
	if currency != "credits":
		url = "https://api.kraken.com/0/public/Ticker?pair=%susd" % (currency)
		resp = requests.get(url).json()
		#currentprice = resp['USD']
		if currency.upper() == "BTC":
			currentprice = resp['result']['XXBTZUSD']['a'][0]
		elif currency.upper() == "XMR":
			currentprice = resp['result']['XXMRZUSD']['a'][0]
		elif currency.upper() == "LTC":
			currentprice = resp['result']['XLTCZUSD']['a'][0]
		converted = "${0:.3f}".format(float(value) * float(currentprice))
		return {"currentprice": currentprice, "converted": converted}
	else:
		return {"currentprice": None, "converted": "N/A"}

# Get recent logins
def recent_logins(limit = None):
	url = "https://hashes.com/en/profile"
	get = session.get(url).text
	bs = bs4.BeautifulSoup(get, features="html.parser")
	loginhistory = bs.find("table", { "class" : "table table-hover table-striped" })
	loginhistory.find("thead", { "class": "fw-bolder"}).decompose()
	table = PrettyTable()
	table.field_names = ["Created", "Status", "IP Addres", "Location"]
	table.align = "l"
	for row in loginhistory.findAll("tr")[0:limit]:
		cells = row.findAll("td")
		if cells != []:
			date = cells[0].find(string=True)
			status = cells[1].find("span").text
			ipaddress = cells[2].find(string=True)
			location = cells[3].find(string=True)
			table.add_row([str(date), str(status), str(ipaddress), str(location)])
	print(table)

# Confirm function
def confirm(message):
    c = input(message+" [y/n] ")
    if c == "y":
        return True
    if c == "n":
        return False


## Initial checks and header


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

# Check if api key exists
if os.path.exists("api.txt"):
	with open("api.txt", "r") as apifile:
		apikey = apifile.read()
	print("Loaded API key from api.txt")
else:
	apikey = input("Enter API Key: ")
	with open("api.txt", "w+") as apifile:
		apifile.write(apikey)

# Check if valid algorithm list is updated
update_algs()

# If logged in display last 3 attempted logins
if session is not None:
	print("\nLast 3 login attempts:")
	recent_logins(3)

## Start command line
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
				parser.add_argument("-currency", help='Currenct to filter jobs by. Multiple can be given e.g. BTC,LTC', default=None)
				g = parser.add_mutually_exclusive_group()
				g.add_argument("-algid", help='Algorithm to filter jobs by. Multiple can be given e.g. 20,300,220', default=None)
				g.add_argument("-jobid", help='Job ID to filter jobs by. Multiple can be given e.g. 1,2,3,4,5', default=None)
				g.add_argument("-self", help='Search jobs you have created.', action='store_true')
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
								jobs = get_jobs(validsort[parsed.sortby], s, parsed.r, parsed.currency)
							else:
								jobs = False
								print (",".join(d)+ " are not valid algorithm IDs.")
						else:
							if parsed.algid not in validalgs:
								jobs = False
								print (parsed.algid+" not a valid algorithm ID.")
							else:
						 		jobs = get_jobs(validsort[parsed.sortby], [parsed.algid], parsed.r, parsed.currency)
					elif parsed.jobid is not None:
						if "," in parsed.jobid:
							jids = parsed.jobid.split(",")
						else:
							jids = [parsed.jobid]
						jobs = get_jobs(validsort[parsed.sortby], None, parsed.r, parsed.currency)
						temp = []
						for j in jobs:
							if str(j["id"]) in jids:
								temp.append(j)
								jids.remove(str(j["id"]))
						jobs = temp
						if jids:
							print("No valid jobs for ids: " + ",".join(jids))
					elif parsed.self == True:
						jobs = get_jobs(validsort[parsed.sortby], None, parsed.r, parsed.currency, parsed.self)
					else:
						jobs = get_jobs(validsort[parsed.sortby], None, parsed.r, parsed.currency)
					limit = parsed.limit
				except SystemExit:
					jobs = False
					None
			else:
				jobs = get_jobs()
				limit = None
			if jobs:
				table = PrettyTable()
				table.field_names = ["Created", "ID", "Algorithm", "Total", "Found", "Left", "Max", "Currency", "Price Per Hash", "Hints"]
				table.align = "l"
				for rows in jobs[0:limit] if limit else jobs:
					ids = rows['id']
					created = datetime.strptime(rows['createdAt'], '%Y-%m-%d %H:%M:%S').strftime("%m/%d/%y")
					algorithm = rows['algorithmName']
					total = rows['totalHashes']
					found = rows['foundHashes']
					left = rows['leftHashes']
					maxcracks = rows['maxCracksNeeded']
					currency = rows['currency']
					price = rows['pricePerHash'] + " / $" + rows['pricePerHashUsd']
					hints = rows['hints']
					if hints != "":
						hints = "Hints available"
					else:
						hints = "No hints available"
					table.add_row([created, ids, algorithm, total, found, left, maxcracks, currency, price, hints])
				print(table)
			else:
				print ("No jobs found.")
		if cmd[0:8] == "download":
			args = cmd[8:]
			parser = argparse.ArgumentParser(description='Download escrow jobs from hashes.com', prog='download')
			parser.add_argument("-currency", help='Crytocurrency to filter downloads by. Multiple can be given e.g. BTC,LTC', default=None)
			g1 = parser.add_mutually_exclusive_group()
			g1.add_argument("-jobid", help='Job ID to download. Multiple IDs can be seperated with a comma. e.g. 3,4,5.', default=None)
			g1.add_argument("-algid", help='Algorithm ID to download', default=None)
			g2 = parser.add_mutually_exclusive_group(required=True)
			g2.add_argument("-f", help='Download to file.')
			g2.add_argument("-p", help='Print to screen', action='store_true')
			try:
				parsed = parser.parse_args(shlex.split(args))
				if parsed.algid is not None:
					if parsed.algid not in validalgs:	
						print(parsed.algid+" is not a valid algorithm.")
					else:
						download(parsed.jobid, parsed.algid, parsed.f, parsed.p, parsed.currency)
				else:
					download(parsed.jobid, parsed.algid, parsed.f, parsed.p, parsed.currency)
			except SystemExit:
				None
		if cmd[0:4] == "help":
			table = PrettyTable()
			table.field_names = ["Command", "Description", "Flags"]
			table.align = "l"
			table.add_row(["get jobs", "Get current jobs in escrow", "-algid, -jobid, -currency, -sortby, -r, -limit, --help"])
			table.add_row(["download", "Download to file or print jobs from escrow", "-jobid, -algid, -currency, -f, -p, --help"])
			table.add_row(["stats", "Get stats about hashes left in escrow", "-algid, --help"])
			table.add_row(["watch", "Watch status of jobs (updates every 10 seconds)", "-jobid, -length, --help"])
			table.add_row(["algs", "Get the algorithms hashes.com currently supports", "-algid, -search, --help"])
			table.add_row(["lookup", "Hash lookup **", "-single, -infile, -outfile, -p, -verbose, --help"])
			table.add_row(["id", "Hash identifier", "-hash, -extended, --help"])
			table.add_row(["login", "Login to hashes.com or view login history.", "-email, -rememberme, -history*, --help"])
			table.add_row(["upload", "Upload cracks to hashes.com **", "-algid, -file, --help"])
			table.add_row(["history", "Show history of submitted cracks **", "-limit, -r, -stats, --help"])
			table.add_row(["hints", "Display any available hints for a specified job ID **", "-jobid, --help"])
			table.add_row(["withdraw", "Withdraw funds from hashes.com to BTC address *", "No flags"])
			table.add_row(["withdrawals", "Show all withdrawal requests **", "No flags"])
			table.add_row(["balance", "Show BTC balance **", "No flags"])
			table.add_row(["logout", "Clear logged in session *", "No flags"])
			table.add_row(["clear", "Clear console", "No flags"])
			table.add_row(["exit", "Exit console", "No flags"])
			print(table)
			print("* = Must be logged in")
			print("** = Only requires apikey")
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
			g1 = parser.add_mutually_exclusive_group(required=True)
			g1.add_argument("-email", help='Email to hashes.com account.', default=None)
			g1.add_argument("-history", help='Show login history.', action='store_true')
			parser.add_argument("-rememberme", help='Save session to reload after closing console.', action='store_true')
			try:
				parsed = parser.parse_args(shlex.split(args))
				if parsed.history:
					if session is not None:
						recent_logins()
					else:
						print("You must be logged in for this action.")
				elif parsed.email is not None:
					if session is None:
						email = parsed.email
						password = getpass()
						login(email, password, parsed.rememberme)
					else:
						print("You are already logged in!")
			except SystemExit:
				None
		if cmd[0:6] == "upload":
			if apikey is not None:
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
				print("API key is required for this action.")
		if cmd[0:7] == "history":
			if apikey is not None:
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
				print("API key is required for this action.")
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
					prev = None
					while True:
						count = watch(parsed.jobid, stime, parsed.length, prev)
						if count == False:
							break
						time.sleep(10)
						prev = count
						print("\033[%sF\033[J" % (count), end="")
				except SystemExit:
					None
		if cmd[0:2] == "id":
			args = cmd[2:]
			parser = argparse.ArgumentParser(description='List potential hash algorithms for a given hash.', prog='id')
			parser.add_argument("-hash", help="Hash to identify.", required=True)
			parser.add_argument("-extended", help="Show extended results.", action='store_true')
			try:
				parsed = parser.parse_args(shlex.split(args))
				print("Possible algorithms for '%s':" % (parsed.hash))
				hashid(parsed.hash, parsed.extended)
			except SystemExit:
				None
		if cmd[0:6] == "lookup":
			if apikey is not None:
				args = cmd[6:]
				parser = argparse.ArgumentParser(description='Hash lookup', prog='lookup')
				parser.add_argument("-verbose", help='Display algorithm of hashes that are found.', action='store_true')
				g1 = parser.add_mutually_exclusive_group()
				g1.add_argument("-infile", help='Input file with hashes to lookup', default=None)
				g1.add_argument("-single", help='Sinlge line hash to lookup', default=None)
				g2 = parser.add_mutually_exclusive_group(required=True)
				g2.add_argument("-outfile", help='Output lookup results to a file', default=None)
				g2.add_argument("-p", help='Print lookup results', action='store_true')
				try:
					parsed = parser.parse_args(shlex.split(args))
					hashes = None
					if parsed.single is not None:
						hashes = [parsed.single]
					elif parsed.infile is not None:
						if os.path.exists(parsed.infile):
							with open(parsed.infile) as infile:
								hashes = infile.read().splitlines()
						else:
							print("The file '%s' does not exist." % (parsed.infile))
					if hashes is not None:
						if len(hashes) <= 250:
							credits = get_escrow_balance(p = False)['credits']
							pcost = 1 + len(hashes)
							if int(credits) > 1:
								if pcost > int(credits):
									print("Warning: Depending on search results, you may not have enough credits for this transaction.")
								if confirm("This transaction has a potential cost of %s credits. You have a balance of %s credits. Continue?" % (pcost, credits)):
									hash_lookup(hashes, parsed.outfile, parsed.p, parsed.verbose)
								else:
									print("Lookup transaction canceled.")
							else:
								print("You don't have enough credits to process a lookup. You need at least 2 credits to process a lookup.")
						else:
							print("The maximum hashes allowed per request is 250!")
				except SystemExit:
					None
			else:
				print("API key is required for this action.")
		if cmd[0:5] == "hints":
			args = cmd[5:]
			parser = argparse.ArgumentParser(description='Get hints for job ID.', prog='hints')
			parser.add_argument("-jobid", help="Job ID to get hints for.", required=True)
			try:
				parsed = parser.parse_args(shlex.split(args))
				data = []
				for j in get_jobs():
					if str(j["id"]) == parsed.jobid:
						data.append(j)
				if len(data) == 0:
					print("%s is an invalid job id." % (parsed.jobid))
				else:
					for hints in data:
						if hints['hints'] != "":
							print("Hints for job id %s:" % (parsed.jobid))
							print(hints['hints'])
						else:
							print("No available hints for job id %s." % (parsed.jobid))
			except SystemExit:
				None
		if cmd[0:7] == "balance":
			if apikey is not None:
				get_escrow_balance()
			else:
				print("API key is required for this action.")
		if cmd == "withdraw":
			if session is not None:
				withdraw()
			else:
				print("You are not logged in. Type 'help' for info.")
		if cmd == "withdrawals":
			if apikey is not None:
				withdraw_requests()
			else:
				print("API key is required for this action.")
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