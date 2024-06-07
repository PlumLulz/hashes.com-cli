import argparse
import asyncio
import importlib
import json
import os
import shlex
import sys
import time
from binascii import a2b_base64
from getpass import getpass

import bs4
import requests
import websockets
from prettytable import PrettyTable

from inc.algorithms import validalgs
from tools import show


def get_jobs(
        apikey_: str,
        sortby: str = "createdAt",
        algid: set | None = None,
        reverse: bool = True,
        currency: str | None = None,
        self_: bool = False
) -> list:
    url = "https://hashes.com/en/api/jobs" + ("_self" if self_ else f"?key={apikey_}")
    json_data_ = requests.get(url).json()

    if json_data_["success"]:
        result = json_data_["list"]

        if currency is not None:
            data_ = []

            for data_row in result:
                if str(data_row["currency"]) in currency.upper().split(","):
                    data_.append(data_row)

            result = data_
        elif algid is not None:
            data_ = []
            for data_row in result:
                if str(data_row['algorithmId']) in algid:
                    data_.append(data_row)
            result = data_

        return sorted(result, key=lambda x: x[sortby], reverse=reverse)


def download(
        apikey_: str,
        jobid: str,
        algid: int,
        file: str,
        currency: str,
        printr: bool | None = None,
) -> None:
    urls = []
    jobs_ = get_jobs(apikey_, currency=currency)
    if jobid is not None:
        jobids_ = "".join(
            jobid.split()
        ).split(",")

        s_ = set(jobids_)

        for rows in jobs_:
            if str(rows['id']) in s_:
                urls.append(rows['leftList'])
                s_.remove(str(rows['id']))

        if s_:
            print(f"{','.join(s_)} not valid jobs")
    elif algid is not None:
        for rows in jobs_:
            if str(rows['algorithmId']) == algid:
                urls.append(rows['leftList'])

        if not urls:
            print(f"No jobs for {validalgs[algid]}")
    else:
        if currency is not None:
            for rows in jobs_:
                urls.append(rows['leftList'])
    if urls:
        if printr:
            for url in urls:
                req = requests.get(f"http://hashes.com{url}").text.rstrip()
                print(req)
        if file:
            try:
                with open(file, "ab+") as outfile:
                    for url in urls:
                        req = requests.get(f"http://hashes.com{url}", stream=True, headers={'Accept-Encoding': None})
                        total_size = int(req.headers.get('Content-Length'))
                        downloaded_ = 0

                        if total_size < 1048576:
                            suffix = "KB"
                            factor = float(1 << 10)
                        else:
                            suffix = "MB"
                            factor = float(1 << 20)

                        for chunk in req.iter_content(1024):
                            outfile.write(chunk)

                            downloaded_ += len(chunk)
                            end = int(50 * downloaded_ / total_size)

                            print(f"\r[{'=' * end}{' ' * (50-end)}]{round((downloaded_ / factor), 2)} {suffix}/"
                                  f"{round((total_size / factor), 2)} {suffix}   ", flush=True, end='')
                        time.sleep(2)
                    print("\nWrote hashes to: "+file)
            except OSError as e:
                print(e)


def get_stats(
        json_data_: list
) -> None:
    stats = {}
    btc, xmr, ltc = 0, 0, 0
    for rows in json_data_:
        algid = rows['algorithmId']
        currency = rows['currency']
        neededleft = float(rows['maxCracksNeeded']) - float(rows['foundHashes']) \
            if rows['foundHashes'] > 0 else rows['maxCracksNeeded']
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
        stats[algid] = {
            "totalFound": found,
            "totalLeft": left,
            "totalUSD": round(float(usd), 3),
            "totalBTC": round(float(btc), 7),
            "totalXMR": round(float(xmr), 7),
            "totalLTC": round(float(ltc), 7)
        }
    table_ = PrettyTable()
    table_.field_names = ["ID", "Algorithm", "Left", "Found", "USD", "BTC", "XMR", "LTC"]
    table_.align = "l"
    escrowleft, escrowfound, escrowusdvalue, escrowbtcvalue, escrowxmrvalue, escrowltcvalue = 0, 0, 0, 0, 0, 0
    for aid_ in stats:
        escrowleft += stats[aid_]['totalLeft']
        escrowfound += stats[aid_]['totalFound']
        escrowusdvalue += float(stats[aid_]['totalUSD'])
        escrowbtcvalue += float(stats[aid_]['totalBTC'])
        escrowxmrvalue += float(stats[aid_]['totalXMR'])
        escrowltcvalue += float(stats[aid_]['totalLTC'])
        table_.add_row([aid_, validalgs[str(aid_)], stats[aid_]['totalLeft'],
                        stats[aid_]['totalFound'], "$" + str(stats[aid_]['totalUSD']),
                        stats[aid_]['totalBTC'], stats[aid_]['totalXMR'], stats[aid_]['totalLTC']])
    print(table_)
    print(f"Total hashes left: {escrowleft}")
    print(f"Total hashes found: {escrowfound}")
    print(f"Total USD value: ${round(escrowusdvalue, 3)}")
    print(f"Total BTC value: {round(escrowbtcvalue, 7)} / "
          f"{to_usd(round(escrowbtcvalue, 7), 'BTC')['converted'] if escrowbtcvalue > 0 else '$0.00'}")
    print(f"Total XMR value: {round(escrowxmrvalue, 7)} / "
          f"{to_usd(round(escrowxmrvalue, 7), 'XMR')['converted'] if escrowxmrvalue > 0 else '$0.00'}")
    print(f"Total LTC value: {round(escrowltcvalue, 7)} / "
          f"{to_usd(round(escrowltcvalue, 7), 'LTC')['converted'] if escrowltcvalue > 0 else '$0.00'}")


def recent_logins(
        limit_: int | None = None
):
    url = "https://hashes.com/en/profile"

    req = session.get(url).text
    bs = bs4.BeautifulSoup(req, features="html.parser")

    loginhistory = bs.find("table", {"class": "table table-hover table-striped"})
    loginhistory.find("thead", {"class": "fw-bolder"}).decompose()

    table_ = PrettyTable()
    table_.field_names = ["Created", "Status", "IP Addres", "Location"]
    table_.align = "l"
    for row in loginhistory.findAll("tr")[0:limit_]:
        cells = row.findAll("td")

        if cells:
            date = cells[0].find(string=True)
            status = cells[1].find("span").text
            ipaddress = cells[2].find(string=True)
            location = cells[3].find(string=True)
            table_.add_row([str(date), str(status), str(ipaddress), str(location)])
    print(table_)


def save_captcha(
        uri: str
) -> int:
    base64 = uri.split(",", 1)[1]
    binary = a2b_base64(base64)
    captcha_time = int(time.time())

    with open(f"captcha_{captcha_time}.jpg", "wb+") as img:
        img.write(binary)

    print(f"Downloaded captcha image to 'captcha_{captcha_time}.jpg'")

    return captcha_time


def login(
        email_: str,
        password_: str,
        rememberme_: bool | None = None
) -> requests.Session | None:
    url = "https://hashes.com/en/login"
    session_ = requests.Session()

    html = session_.get(url).text
    bs = bs4.BeautifulSoup(html, features="html.parser")

    csrf = bs.find('input', {'name': 'csrf_token'})['value']
    captcha_id = bs.find('input', {'name': 'captchaIdentifier'})['value']
    captcha_uri = bs.find("img", {"class": "img-fluid"}).get('src')
    captcha_time = save_captcha(captcha_uri)

    print("Please open the captcha image saved to the current directory and enter it below.")

    captcha = input("Captcha Code: ")
    auth_data = {
        "email": email_,
        "password": password_,
        "csrf_token": csrf,
        "captcha": captcha,
        "captchaIdentifier": captcha_id,
        "ddos": "fi",
        "submitted": "1"
    }

    html = session_.post(url, data=auth_data).text
    bs = bs4.BeautifulSoup(html, features="html.parser")

    error1 = bs.find("div", {"class": "my-center alert alert-dismissible alert-danger"})
    error2 = bs.find('p', attrs={'class': 'mb-0'})

    if error1 is not None:
        error = []
        for t in error1.contents:
            if type(t) is bs4.element.NavigableString:
                error.append(t.text)

        print("".join(error).strip())
        os.remove(f"captcha_{captcha_time}.jpg")
    elif error2 is not None:
        print(error2.text.strip())
        os.remove(f"captcha_{captcha_time}.jpg")
    else:
        print("Login successful.")
        os.remove(f"captcha_{captcha_time}.jpg")
        if rememberme_:
            with open("session.txt", "w", encoding="utf-8") as sessionfile_:
                sessionfile_.write(json.dumps(session_.cookies))
            print("Wrote session data to: session.txt")
        return session_

    return


def upload(
        apikey_: str,
        algid: int,
        file: str
) -> None:
    uploadurl = "https://hashes.com/en/api/founds"

    data_ = {"key": apikey_, "algo": algid}
    data_file = {"userfile": open(file, "rb")}

    req = requests.post(uploadurl, files=data_file, data=data_).json()

    if req["success"]:
        print("File successfully uploaded.")
        print("Use the 'history' command to check the status.")
    else:
        print("Failed to upload file!")

    return


def to_usd(
        value: float | int | str,
        currency: str
) -> dict:
    convert = {'BTC': 'XXBTZUSD', 'XMR': 'XXMRZUSD', 'LTC': 'XLTCZUSD'}

    if currency != 'credits':
        url = f'https://api.kraken.com/0/public/Ticker?pair={currency}usd'
        resp = requests.get(url).json()

        currentprice = resp['result'][convert[currency.upper()]]['a'][0]
        price = float(value) * float(currentprice)
        converted = f'${round(price, 3)}'

        return {'currentprice': currentprice, 'converted': converted}

    return {'currentprice': None, 'converted': 'N/A'}


def get_escrow_history(
        apikey_: str,
        reverse_: bool,
        limit_: int | None,
        stats_: bool | None
) -> None:
    uploadurl = f"https://hashes.com/en/api/uploads?key={apikey_}"
    data_json = requests.get(uploadurl).json()

    if data_json['success'] is True:
        data_list = []

        for row in data_json['list']:
            cid = row['id']
            date = row['date']
            alg = row['algorithm']
            status = row['status']
            total = row['totalHashes']
            finds = row['validHashes']
            btc = row['btc']
            xmr = row['xmr']
            ltc = row['ltc']
            data_list.append(
                [
                    str(cid), str(date), str(alg),
                    str(status), str(total), str(finds),
                    str(btc), str(xmr), str(ltc)
                ])

        if stats_:
            totalsub, totalvalid, totalearnedusd, totalearnedbtc, totalearnedxmr, totalearnedltc = 0, 0, 0, 0, 0, 0
            algorithms = {}
            for row in data_list:
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
                    algorithms[row[2]] = [int(algorithms[row[2]][0]) + int(row[4]),
                                          int(algorithms[row[2]][1]) + int(row[5]),
                                          float(algorithms[row[2]][2]) + float(btc),
                                          float(algorithms[row[2]][3]) + float(xmr),
                                          float(algorithms[row[2]][4]) + float(ltc)]
            table_ = PrettyTable()
            table_.field_names = ["Algorithm", "Hashes Submitted", "Valid Hashes Submitted", "BTC", "XMR", "LTC"]
            table_.align = "l"
            for k, v in algorithms.items():
                table_.add_row([k, v[0], v[1], round(float(v[2]), 7), round(float(v[3]), 7),
                                "{0:.7f}".format(float(v[4]))])
            table_.sortby = "BTC"
            table_.reversesort = True
            print("USD prices are based on BTCs current price.")
            print(table_)
            print(f"Total hashes submitted: {totalsub}")
            print(f"Total valid hashes submitted: {totalvalid}")
            print(f"Total BTC value: {round(totalearnedbtc, 7)} / "
                  f"{to_usd(round(totalearnedbtc, 7), 'BTC')['converted'] if totalearnedbtc > 0 else '$0.00'}")
            print(
                f"Total XMR value: {round(totalearnedxmr, 7)} / "
                f"{to_usd(round(totalearnedxmr, 7), 'XMR')['converted'] if totalearnedxmr > 0 else '$0.00'}")
            print(
                f"Total LTC value: {round(totalearnedltc, 7)} / "
                f"{to_usd(round(totalearnedltc, 7), 'LTC')['converted'] if totalearnedltc > 0 else '$0.00'}")

        else:
            table_ = PrettyTable()
            table_.field_names = ["ID", "Created", "Algorithm", "Status",
                                  "Total Hashes", "Valid Finds", "BTC",
                                  "XMR", "LTC"]
            table_.align = "l"
            for row in data_list:
                table_.add_row(row)
            if reverse_:
                table_ = table_[::-1]
            if limit_:
                table_ = table_[0:limit]

            print(table_)

    return


def watch(
        apikey_: str,
        jobid: str,
        start: float,
        length: int,
        prev_: str | None
) -> int | None:
    data_list = []
    # This is used to count how many lines are going to be displayed
    # Starts at 4 to account for the 3 line header and 1 line bottom
    count_ = 4
    elapsed = time.time() - start
    jobids_ = "".join(
        jobid.split()
    ).split(",")

    s_ = set(jobids_)

    if elapsed >= 60 * length:
        print("\033[2F\033[J", end="")
        print(f"Watch completed on job IDs: {','.join(s_)}\n", end="")
        return None

    for q in get_jobs(apikey_):
        if str(q["id"]) in s_:
            data_list.append(q)
            count_ += 1
            s_.remove(str(q["id"]))

    if data_list:
        table_ = PrettyTable()
        table_.field_names = ["ID", "Hashes Cracked", "Hashes Left"]
        table_.align = "l"

        for row in data_list:
            table_.add_row([row['id'], row['foundHashes'], row['leftHashes']])

        print(table_)

        if len(s_) > 0:
            count_ += 1
            print(f"Job IDs {','.join(s_)} are no longer valid.")

        return count_
    else:
        if prev_ is not None:
            print("\033[2F\033[J", end="")

        print(f"Job IDs {','.join(s_)} are no longer valid.")

        return None


def hashid(
        hashh,
        extended
) -> None:
    url = f"https://hashes.com/en/api/identifier?hash={hashh}&extended={str(extended).lower()}"
    req = requests.get(url).json()

    if req['success'] is True:
        for algs in req['algorithms']:
            print(algs)
    elif req['success'] is False:
        print(req['message'])

    return


def get_escrow_balance(
        apikey_: str,
        p: bool = True
) -> dict | None:
    req = requests.get(f"https://hashes.com/en/api/balance?key={apikey_}").json()

    print(req)

    if req['success'] is True:
        if p is True:
            table_ = PrettyTable()
            table_.field_names = ["Currency", "Amount", "USD"]
            table_.align = "l"

            req.pop('success')

            for currency, value in req.items():
                if float(value) > 0:
                    usd = to_usd(value, currency)["converted"]
                else:
                    usd = "$0.00"
                table_.add_row([currency, value, usd])

            print(table_)
        elif p is False:
            return req


def confirm(
        message: str
) -> bool:
    c = input(message + " [y/n] ")

    if c == "y":
        return True
    if c == "n":
        return False

    return False


def hash_lookup(
        apikey_: str,
        hashes_: list,
        outfile: str | None,
        printr: bool | None,
        verbose: bool | None
) -> None:
    url = "https://hashes.com/en/api/search"
    data_ = {"key": apikey_, "hashes[]": hashes_}

    req = requests.post(url, data=data_).json()

    if req['success'] is True:
        cost = req['cost']
        hcount = req['count']
        founds = req['founds']

        print(f"There were {len(founds)}/{hcount} hashes found.")
        print(f"Potential cost: {len(hashes_) + 1}")
        print(f"Actual cost: {cost}\n\n")

        if len(founds) > 0:
            for found in founds:
                hashh = found['hash']
                salt = found['salt']
                plain = found['plaintext']
                alg = found['algorithm']

                if len(salt) == 0:
                    line = f"{hashh}:{plain}"
                else:
                    line = f"{hashh}:{salt}:{plain}"

                if verbose is True:
                    line += ":" + alg

                if printr is True:
                    print(line)

                elif outfile is not None:
                    with open(outfile, "a+") as ofile:
                        ofile.write(line + "\n")
            if outfile is not None:
                print(f"Wrote search results to '{outfile}'")
        else:
            print("No hashes found.")
    elif req['success'] is False:
        print(req['message'])

    return


async def wslistener(
        websocket,
        hookcode
) -> None:
    while True:
        message = await websocket.recv()

        message = json.loads(message)

        if message['success'] is False:
            print(message['message'])

        elif message['success'] is True:
            hookcode.process_message(message)


async def main(
        apikey_: str,
        hook: str
) -> None:
    # Import hook code
    try:
        hookcode = importlib.import_module(hook.rstrip(".py"))
    except ModuleNotFoundError:
        print("Hook code failed to import.")
        return

    # Start websocket loop
    url = f"wss://hashes.com/en/api/jobs_wss/?key={apikey_}"
    async for ws in websockets.connect(url):
        try:
            print("Connected to hashes.com websocket API...")
            print("Use Ctrl + C to disconnect from websocket.\n")
            await wslistener(ws, hookcode)
        except websockets.exceptions.ConnectionClosedError:
            # Redundant close request to avoid 3 connection limit error
            await ws.close()
            print("\nConnection closed. Reconnecting...")
            time.sleep(5)
            continue
        except websockets.exceptions.ConnectionClosedOK:
            break


def withdraw_requests(
        apikey_: str
) -> None:
    req = requests.get(f"https://hashes.com/en/api/withdrawals?key={apikey_}").json()
    table_ = PrettyTable()
    table_.field_names = [
        "ID", "Created",
        "Status", "Currency",
        "Amount", "Final",
        "USD", "Destination Address",
        "Transaction Hash"
    ]
    table_.align = "l"

    if req['success'] is True:
        for row in req['list']:
            wid = row['id']
            date = row['date']
            status = row['status']
            amount = round(float(row['amount']), 7)
            final = round(float(row['afterFee']), 7)
            thash = row['transaction']
            currency = row['currency']
            destination = row['destination']
            usd = to_usd(final, currency)['converted']
            table.add_row([wid, date, status, currency, amount, final, usd, destination, thash])
    print(table_)


def update_algs() -> None:
    url = "https://hashes.com/en/api/algorithms"
    req_json = requests.get(url).json()

    if req_json['success'] is True:
        if len(req_json['list']) > len(validalgs):
            temp_ = {}

            for alg in req_json['list']:
                temp_[str(alg['id'])] = alg['algorithmName']

            new = set(temp_) - set(validalgs)

            with open("inc/algorithms.py", "w+") as test:
                test.write("validalgs = " + str(json.dumps(temp_, indent=4)))

                print("\nNew algorithms added to list:")

                for nalg in new:
                    print(f"{nalg}: {temp_[nalg]}")

            print("\nIn order for update to be applied the script must be reloaded.")
            exit()
    else:
        print("Failed to get algorithm list to check for updates.")


if os.path.exists("session.txt"):
    if confirm("Load saved session?"):
        session = requests.session()

        with open("session.txt", "rb") as sessionfile:
            json_data = json.loads(sessionfile.read())
            session.cookies.update(json_data)

        print("Loaded existing session from session.txt")
    else:
        session = None
else:
    session = None

# Check if api key exists
if os.path.exists("api.txt"):
    with open("api.txt", "r") as apifile:
        apikey = apifile.read().replace(" ", "")
    print("Loaded API key from api.txt")
else:
    apikey = input("Enter API Key: ")
    with open("api.txt", "w+") as apifile:
        apifile.write(apikey.replace(" ", ""))

# Check if valid algorithm list is updated
update_algs()

# If logged in display last 3 attempted logins
if session is not None:
    print("\nLast 3 login attempts:")
    recent_logins(3)


# Start command line

try:
    while True:
        cmd = input("hashes.com:~$ ")

        if cmd[0:8] == "get jobs":
            if len(cmd) > 8:
                args = cmd[8:]
                validsort = {"price": "pricePerHash", "total": "totalHashes", "left": "leftHashes",
                             "found": "foundHashes", "lastcrack": "lastUpdate", "created": "createdAt"}

                parser = argparse.ArgumentParser(
                    description='Get escrow jobs from hashes.com',
                    prog='get jobs'
                )
                parser.add_argument(
                    "-sortby",
                    help='Parameter to sort jobs by.',
                    default='created',
                    choices=validsort
                )
                parser.add_argument(
                    "-r",
                    help='Reverse display order.',
                    action='store_false'
                )
                parser.add_argument(
                    "-limit",
                    help='Rows to limit results by.',
                    default=None,
                    type=int
                )
                parser.add_argument(
                    "-currency",
                    help='Current to filter jobs by. Multiple can be given e.g. BTC,LTC',
                    default=None
                )

                g = parser.add_mutually_exclusive_group()
                g.add_argument(
                    "-algid",
                    help='Algorithm to filter jobs by. Multiple can be given e.g. 20,300,220',
                    default=None
                )
                g.add_argument(
                    "-jobid",
                    help='Job ID to filter jobs by. Multiple can be given e.g. 1,2,3,4,5',
                    default=None
                )
                g.add_argument(
                    "-self",
                    help='Search jobs you have created.',
                    default=False,
                    action='store_true'
                )

                try:
                    parsed = parser.parse_args(shlex.split(args))

                    if parsed.algid is not None:
                        algids = "".join(
                            parsed.algid.split()
                        ).split(",")

                        s = set(algids)
                        error_id = []
                        for id_ in algids:
                            if id_ not in validalgs:
                                error_id.append(id_)

                        if len(error_id) != 0:
                            print(",".join(s) + " are not valid algorithm IDs.")
                            continue

                        jobs = get_jobs(apikey, validsort[parsed.sortby], s, parsed.r, parsed.currency)

                    elif parsed.jobid is not None:
                        jobids = "".join(
                            parsed.jobid.split()
                        ).split(",")

                        s = set(jobids)

                        jobs = get_jobs(apikey, validsort[parsed.sortby], None, parsed.r, parsed.currency)
                        temp = []

                        for job in jobs:
                            if str(job["id"]) in jobids:
                                temp.append(job)
                                jobids.remove(str(job["id"]))

                        jobs = temp

                        if jobids:
                            print("No valid jobs for ids: " + ",".join(jobids))
                            continue
                    elif parsed.self:
                        jobs = get_jobs(apikey, validsort[parsed.sortby], None, parsed.r, parsed.currency, parsed.self)
                    else:
                        jobs = get_jobs(apikey, validsort[parsed.sortby], None, parsed.r, parsed.currency)
                    limit = parsed.limit
                except SystemExit:
                    continue
            else:
                jobs = get_jobs(apikey)
                limit = None

            show.show_table_jobs(jobs, limit)
        elif cmd[0:8] == "download":
            args = cmd[8:]

            parser = argparse.ArgumentParser(
                description="Download escrow jobs from hashes.com",
                prog="download"
            )
            parser.add_argument(
                "-currency",
                help='Crytocurrency to filter downloads by. Multiple can be given e.g. BTC,LTC',
                default=None
            )

            g1 = parser.add_mutually_exclusive_group()
            g1.add_argument(
                "-jobid",
                help='Job ID to download. Multiple IDs can be seperated with a comma. e.g. 3,4,5.',
                default=None
            )
            g1.add_argument(
                "-algid",
                help='Algorithm ID to download',
                default=None
            )

            g2 = parser.add_mutually_exclusive_group(required=True)
            g2.add_argument(
                "-f",
                help='Download to file.'
            )
            g2.add_argument(
                "-p",
                help='Print to screen',
                action='store_true'
            )

            try:
                parsed = parser.parse_args(shlex.split(args))
                downloaded = False
                if parsed.algid is not None:
                    if parsed.algid not in validalgs:
                        print(f"{parsed.algid} is not a valid algorithm.")
                        continue

                    download(apikey, parsed.jobid, parsed.algid, parsed.f, parsed.currency, parsed.p)
                    downloaded = True

                if not downloaded:
                    download(apikey, parsed.jobid, parsed.algid, parsed.f, parsed.currency, parsed.p)
            except SystemExit:
                pass
        elif cmd[0:4] == "help":
            show.show_table_start()
        elif cmd[0:5] == "stats":
            args = cmd[5:]
            parser = argparse.ArgumentParser(
                description='Get stats for hashes left in escrow from hashes.com',
                prog='stats'
            )
            parser.add_argument(
                "-algid",
                help='Algorithm ID to sort stats by. Multiple can be given e.g. 20,300,220',
                default=None
            )
            try:
                parsed = parser.parse_args(shlex.split(args))

                if parsed.algid is not None:
                    algids = "".join(
                        parsed.algid.split()
                    ).split(",")

                    s = set(algids)
                    error_id = []
                    for id_ in algids:
                        if id_ not in validalgs:
                            error_id.append(id_)

                    if len(error_id) != 0:
                        print(",".join(s) + " are not valid algorithm IDs.")
                        continue

                    get_stats(get_jobs(apikey, "createdAt", s))
                    continue
                get_stats(get_jobs(apikey))
            except SystemExit:
                pass
        elif cmd[0:4] == "algs":
            args = cmd[4:]

            parser = argparse.ArgumentParser(
                description='List of all algorithms that hashes.com supports',
                prog='algs'
            )
            parser.add_argument(
                "-algid",
                help='Algorithm ID to lookup. Multiple can be given e.g. 20,300,220',
                default=None
            )
            parser.add_argument(
                "-search",
                help='Search algorithm by name.',
                default=None
            )

            try:
                parsed = parser.parse_args(shlex.split(args))
                ids = {}

                if parsed.algid:
                    algids = "".join(
                        parsed.algid.split()
                    ).split(",")

                    ids = set(algids)

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
                elif parsed.search:
                    print(f"No results found for '{parsed.search}'")
                elif parsed.algid and len(ids) > 0:
                    print(f"{','.join(ids)} not currently supported.")
            except SystemExit:
                pass
        elif cmd[0:5] == "login":
            args = cmd[5:]

            parser = argparse.ArgumentParser(
                description='Login to hashes.com',
                prog='login'
            )

            g1 = parser.add_mutually_exclusive_group(
                required=True
            )
            g1.add_argument(
                "-email",
                help="Email to hashes.com account.",
                default=None
            )
            parser.add_argument(
                "-history",
                help="Show login history.",
                action="store_true"
            )
            parser.add_argument(
                "-rememberme",
                help="Save session to reload after closing console.",
                action="store_true"
            )
            try:
                parsed = parser.parse_args(shlex.split(args))
                if parsed.history:
                    if session is not None:
                        recent_logins()
                        continue
                    print("You must be logged in for this action.")
                elif parsed.email is not None:
                    if session is None:
                        email = parsed.email
                        password = getpass(prompt="Password: ")
                        session = login(email, password, parsed.rememberme)
                    else:
                        print("You are already logged in!")
                else:
                    print("Email is None")
            except SystemExit:
                pass
        elif cmd[0:6] == "upload":
            if apikey is not None:
                args = cmd[6:]

                parser = argparse.ArgumentParser(
                    description='Upload cracked hashes to hashes.com',
                    prog='upload'
                )
                parser.add_argument(
                    "-algid",
                    help='Algorithm ID of cracked hashes',
                    required=True,
                    default=None
                )
                parser.add_argument(
                    "-file",
                    help='File of cracked hashes',
                    required=True,
                    default=None
                )

                try:
                    parsed = parser.parse_args(shlex.split(args))

                    if parsed.algid not in validalgs:
                        print(f"{parsed.algid} is not a valid algorithm ID")
                    elif os.path.exists(parsed.file) is False:
                        print(f"{parsed.file} does not exist")
                    elif not parsed.file.lower().endswith(".txt"):
                        print("File type must be .txt")
                    else:
                        upload(apikey, parsed.algid, parsed.file)
                except SystemExit:
                    pass
            else:
                print("API key is required for this action.")
        elif cmd[0:7] == "history":
            if apikey is not None:
                args = cmd[7:]

                parser = argparse.ArgumentParser(
                    description='View history of submitted cracks.',
                    prog='history'
                )
                parser.add_argument(
                    "-r",
                    help='Reverse order of history.',
                    required=False,
                    action='store_true'
                )
                parser.add_argument(
                    "-limit",
                    help='Number of rows to limit results.',
                    required=False,
                    type=int
                )
                parser.add_argument(
                    "-stats",
                    help='See history stats.',
                    required=False,
                    action='store_true'
                )
                try:
                    parsed = parser.parse_args(shlex.split(args))
                    get_escrow_history(apikey, parsed.r, parsed.limit, parsed.stats)
                except SystemExit:
                    pass
            else:
                print("API key is required for this action.")
        elif cmd[0:5] == "watch":
            args = cmd[5:]

            parser = argparse.ArgumentParser(
                description='Watch status of job ID.',
                prog='watch'
            )
            parser.add_argument(
                "-jobid",
                help='Job ID to watch. Multiple can be given e.g. 29374,29294,8',
                required=True
            )
            parser.add_argument(
                "-length",
                help='Length in minutes to watch job.',
                required=False,
                default=5,
                type=int
            )
            try:
                parsed = parser.parse_args(shlex.split(args))
                stime = time.time()

                # In order to use ANSI escape codes on Windows they must be activated first.
                # The easiest way that I have found is to simply run the color command first
                if sys.platform == 'win32':
                    os.system("color")

                print(f"Watching job IDs: {parsed.jobid}")
                print("Use Ctrl + C to end watch session.\n")

                prev = None
                try:
                    while True:
                        count = watch(apikey, parsed.jobid, stime, parsed.length, prev)

                        if count is False:
                            break

                        time.sleep(10)
                        prev = count
                        print(f"\033[{count}F\033[J", end="")
                except KeyboardInterrupt:
                    print("\n")
                    continue
            except SystemExit:
                pass
        elif cmd[0:2] == "id":
            args = cmd[2:]
            parser = argparse.ArgumentParser(description='List potential hash algorithms for a given hash.', prog='id')
            parser.add_argument("-hash", help="Hash to identify.", required=True)
            parser.add_argument("-extended", help="Show extended results.", action='store_true')
            try:
                parsed = parser.parse_args(shlex.split(args))
                print(f"Possible algorithms for '{parsed.hash}':")
                hashid(parsed.hash, parsed.extended)
            except SystemExit:
                pass
        elif cmd[0:6] == "lookup":
            if apikey is not None:
                args = cmd[6:]

                parser = argparse.ArgumentParser(
                    description='Hash lookup',
                    prog='lookup'
                )
                parser.add_argument(
                    "-verbose",
                    help='Display algorithm of hashes that are found.',
                    action='store_true'
                )

                g1 = parser.add_mutually_exclusive_group()
                g1.add_argument(
                    "-infile",
                    help='Input file with hashes to lookup',
                    default=None
                )
                g1.add_argument(
                    "-single",
                    help='Sinlge line hash to lookup',
                    default=None
                )

                g2 = parser.add_mutually_exclusive_group(required=True)
                g2.add_argument(
                    "-outfile",
                    help='Output lookup results to a file',
                    default=None
                )
                g2.add_argument(
                    "-p",
                    help='Print lookup results',
                    action='store_true'
                )

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
                            print(f"The file '{parsed.infile}' does not exist.")
                    if hashes is not None:
                        if len(hashes) > 250:
                            print("The maximum hashes allowed per request is 250!")
                            continue

                        credits_ = get_escrow_balance(apikey, p=False)['credits']
                        pcost = 1 + len(hashes)

                        if int(credits_) < 1:
                            print("You don't have enough credits to process a lookup. "
                                  "You need at least 2 credits to process a lookup.")
                            continue

                        if pcost > int(credits_):
                            print("Warning: Depending on search results,"
                                  " you may not have enough credits for this transaction.")
                            continue

                        if confirm(f"This transaction has a potential cost of {pcost} credits. "
                                   f"You have a balance of {credits_} credits. Continue?"):
                            hash_lookup(apikey, hashes, parsed.outfile, parsed.p, parsed.verbose)
                        else:
                            print("Lookup transaction canceled.")
                except SystemExit:
                    pass
            else:
                print("API key is required for this action.")
        elif cmd[0:5] == "hints":
            args = cmd[5:]

            parser = argparse.ArgumentParser(
                description='Get hints for job ID.',
                prog='hints'
            )
            parser.add_argument(
                "-jobid",
                help="Job ID to get hints for.",
                required=True
            )
            try:
                parsed = parser.parse_args(shlex.split(args))
                data = []

                for j in get_jobs(apikey):
                    if str(j["id"]) == parsed.jobid:
                        data.append(j)

                if len(data) == 0:
                    print(f"{parsed.jobid} is an invalid job id.")
                else:
                    for hints in data:
                        hints_ = hints.get("hints", None)
                        if hints_ is None:
                            print("Hints are disabled for your usergroup.")
                        elif hints_ != "":
                            print(f"Hints for job id {parsed.jobid}:")
                            print(hints_)
                        else:
                            print(f"No available hints for job id {parsed.jobid}.")
            except SystemExit:
                pass
        elif cmd[0:9] == "websocket":
            args = cmd[9:]

            parser = argparse.ArgumentParser(
                description='Connect to hashes.com Websocket API.',
                prog='websocket'
            )
            parser.add_argument(
                "-hook",
                help="Name of hook file. (Must be stored in same dir)",
                required=True
            )
            try:
                parsed = parser.parse_args(shlex.split(args))
                try:
                    asyncio.run(main(apikey, parsed.hook))
                except KeyboardInterrupt:
                    print("\nDisconnected from hashes.com Websocket API.")
            except SystemExit:
                pass
        elif cmd[0:7] == "balance":
            if apikey is not None:
                get_escrow_balance(apikey)
            else:
                print("API key is required for this action.")
        elif cmd == "withdrawals":
            if apikey is not None:
                withdraw_requests(apikey)
            else:
                print("API key is required for this action.")
        elif cmd[0:6] == "logout":
            if session is not None:
                session = None
                print("Logged out.")
            else:
                print("You are not logged in.")
        elif cmd[0:5] == "clear":
            os.system('cls||clear')
        elif cmd[0:4] == "exit":
            break
        elif cmd.replace(" ", "") == "":
            show.show_table_start()
        else:
            print("The command you entered is unknown")
            show.show_table_start()
except KeyboardInterrupt:
    pass
