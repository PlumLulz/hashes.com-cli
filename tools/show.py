from datetime import datetime

from prettytable import PrettyTable


def show_table_start() -> None:
    table = PrettyTable()
    table.field_names = ["Command", "Description", "Flags"]
    table.align = "l"
    table.add_row(
        ["get jobs", "Get current jobs in escrow", "-algid, -jobid, -currency, -sortby, -r, -limit, --help"])
    table.add_row(
        ["download", "Download to file or print jobs from escrow", "-jobid, -algid, -currency, -f, -p, --help"])
    table.add_row(["stats", "Get stats about hashes left in escrow", "-algid, --help"])
    table.add_row(["watch", "Watch status of jobs (updates every 10 seconds)", "-jobid, -length, --help"])
    table.add_row(["algs", "Get the algorithms hashes.com currently supports", "-algid, -search, --help"])
    table.add_row(["lookup", "Hash lookup **", "-single, -infile, -outfile, -p, -verbose, --help"])
    table.add_row(["id", "Hash identifier", "-hash, -extended, --help"])
    table.add_row(
        ["login", "Login to hashes.com or view login history.", "-email, -rememberme, -history*, --help"])
    table.add_row(["upload", "Upload cracks to hashes.com **", "-algid, -file, --help"])
    table.add_row(["history", "Show history of submitted cracks **", "-limit, -r, -stats, --help"])
    table.add_row(["hints", "Display any available hints for a specified job ID **", "-jobid, --help"])
    table.add_row(["websocket", "Connect to hashes.com websocket API using a hook file **", "-hook, --help"])
    table.add_row(["withdrawals", "Show all withdrawal requests **", "No flags"])
    table.add_row(["balance", "Show BTC balance **", "No flags"])
    table.add_row(["logout", "Clear logged in session *", "No flags"])
    table.add_row(["clear", "Clear console", "No flags"])
    table.add_row(["exit", "Exit console", "No flags"])
    print(table)
    print("* = Must be logged in")
    print("** = Only requires apikey")


def show_table_jobs(jobs: list, limit: int | None) -> None:
    table = PrettyTable()
    table.field_names = ["Created", "ID", "Algorithm",
                         "Total", "Found", "Left", "Max",
                         "Currency", "Price Per Hash", "Hints"]
    table.align = "l"

    for row in jobs[0:limit] if limit else jobs:
        ids = row["id"]
        created = datetime.strptime(row["createdAt"], "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%y")
        algorithm = row["algorithmName"]
        total = row["totalHashes"]
        found = row["foundHashes"]
        left = row["leftHashes"]
        maxcracks = row["maxCracksNeeded"]
        currency = row["currency"]
        price = f"{row['pricePerHash']} / ${row['pricePerHashUsd']}"

        hints = row.get("hints", None)
        if hints is None:
            hints = "Disabled"
        elif hints != "":
            hints = "Hints available"
        else:
            hints = "No hints available"

        table.add_row([created, ids, algorithm, total, found, left, maxcracks, currency, price, hints])

    print(table)
