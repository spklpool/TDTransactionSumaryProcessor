class TransactionGroup:

    transactions = []

    def __init__(self):
        self.transactions = []

    def appendTransaction(self, transaction):
        self.transactions.append(transaction)

    def size(self):
        return len(self.transactions)

    def getSecurity(self):
        check = ""
        ret = ""
        for transaction in self.transactions:
            if check != "":
                if check != transaction.normalized_security:
                    raise ValueError('missmatched securities in a security group', ret, transaction.security)
            ret = transaction.security
            check = transaction.normalized_security
        return ret

    def getUnitsSold(self):
        ret = 0
        for transaction in self.transactions:
            ret += transaction.unitsSold
        return ret

    def getBuyCommissions(self):
        ret = 0
        for transaction in self.transactions:
            ret += transaction.boughtCommissions
        return ret

    def getSellCommissions(self):
        ret = 0
        for transaction in self.transactions:
            ret += transaction.soldCommissions
        return ret

    def getProceeds(self):
        ret = 0
        for transaction in self.transactions:
            ret += transaction.soldAmount()
        return ret

    def getNetProceeds(self):
        ret = 0
        for transaction in self.transactions:
            ret += (transaction.convertedSoldAmount() - transaction.soldCommissions)
        return ret

    def getCostBasis(self):
        ret = 0
        for transaction in self.transactions:
            ret += transaction.boughtAmount()
        return ret

    def getNetCostBasis(self):
        ret = 0
        for transaction in self.transactions:
            ret += (transaction.convertedBoughtAmount() + transaction.boughtCommissions)
        return ret

    def getNetGainLoss(self):
        return self.getNetProceeds() - self.getNetCostBasis()
        
    def writeToFile(self):
        f = open("output.csv", "a")
        f.write("{},{},{},{},{}\n".format(self.getSecurity(), self.getUnitsSold(),
                                   self.getNetCostBasis(), self.getNetProceeds(),
                                   self.getNetGainLoss()))
        f.close()

class RawTransaction:
    line = ""
    currency = ""
    security = ""
    commissions = 0.0
    boughtCommissions = 0.0
    soldCommissions = 0.0
    dailyExchangeRate = 0.0
    unitsBought = 0
    unitsSold = 0
    price = 0.0
    cost = 0.0
    proceeds = 0.0
    isValid = False
    option_type = ""
    option_ticker = ""
    option_expiry_year = ""
    option_expiry_day = ""
    option_expiry_month = ""
    option_expiry_strike = ""
    normalized_security = ""

    def __init__(self, line):
        self.line = line.strip()
        parts = line.split(',')
        self.isValid = isValidTransactionLine(parts)
        if self.isValid:
            self.currency = getCurrencyFromLineParts(parts)
            self.security = getSecurityFromLineParts(parts)
            self.normalized_security = self.security
            self.commissions = getCommissionsFromLineParts(parts)
            self.dailyExchangeRate = getExchangeRateForDayFromLineParts(parts)
            self.unitsBought = getUnitsBoughtFromLineParts(parts)
            self.unitsSold = getUnitsSoldFromLineParts(parts)
            self.price = getPriceFromLineParts(parts)
            self.cost = getCostFromLineParts(parts)
            self.proceeds = getProceedsFromLineParts(parts)
            if self.isBuy():
                self.boughtCommissions = self.commissions
            if self.isSell():
                self.soldCommissions = self.commissions
            if self.isOption():
                self.option_type = self.security[:8].split("-")[0]
                self.option_ticker = self.security[8:].strip().split()[0].split("'")[0]
                self.option_expiry_year = self.security[8:].strip().split()[0].split("'")[1]
                self.option_expiry_day = self.security[8:].strip().split()[1].split("@")[0].strip().zfill(4)[:2]
                self.option_expiry_month = self.security[8:].strip().split()[1].split("@")[0].strip().zfill(4)[2:]
                self.option_expiry_strike = self.security[8:].strip().split()[1].split("@")[1].strip()
                self.normalized_security = "{}--{}--{}--{}--{}--{}".format(self.option_type,
                                                                           self.option_ticker,
                                                                           self.option_expiry_year,
                                                                           self.option_expiry_month,
                                                                           self.option_expiry_day,
                                                                           self.option_expiry_strike)

    def isBuy(self):
        return self.unitsBought > 0

    def getOptionTicker(self):
        return self.option_ticker

    def isSell(self):
        return self.unitsSold > 0

    def isOption(self):
        return "PUT" in self.security or "CALL" in self.security

    def boughtAmount(self):
        multiplier = 1
        if self.isOption():
            multiplier = 100
        return self.price * self.unitsBought * multiplier

    def convertedBoughtAmount(self):
        if self.currency == "USD":
            return self.boughtAmount() * self.dailyExchangeRate
        return self.boughtAmount()

    def soldAmount(self):
        multiplier = 1
        if self.isOption():
            multiplier = 100
        return self.price * self.unitsSold * multiplier

    def convertedSoldAmount(self):
        if self.currency == "USD":
            return self.soldAmount() * self.dailyExchangeRate
        return self.soldAmount()


def getExchangeRateForDayFromLineParts(parts):
    transaction_date = getTransactionDateFromLineParts(parts)
    date_parts = transaction_date.split()
    return getExchangeRateForDay(date_parts[2], monthsMap.get(date_parts[0]), date_parts[1])


def getExchangeRateForDay(year, month, day):
    target_date = "{}-{}-{}".format(year.zfill(4), month.zfill(2), day.zfill(2))
    for line in fx_lines:
        parts = line.split(',')
        if (len(parts) == 2):
            date = parts[0].replace('"', '')
            if (date == target_date):
                return float(parts[1].replace('"', '').strip())
    if int(day) == 1:
        return getExchangeRateForDay(year, str(int(month) - 1), str(31))
    else:
        return getExchangeRateForDay(year, month, str(int(day) - 1))

def addToSecuritiesMap(rawTransaction):
    if rawTransaction.line not in excludes_lines:
        if (rawTransaction.normalized_security in securitiesMap):
            securitiesMap[rawTransaction.normalized_security].append(rawTransaction.line)
        else:
            securityLines = [rawTransaction.line]
            securitiesMap[rawTransaction.normalized_security] = securityLines

def processSecuritiesToDictionary():
    for line in extras_lines:
        rawTransaction = RawTransaction(line)
        if rawTransaction.isValid:
            addToSecuritiesMap(rawTransaction)
    for line in transactions_lines:
        rawTransaction = RawTransaction(line)
        if rawTransaction.isValid:
            addToSecuritiesMap(rawTransaction)

def getAmountSold(security):
    accumulatedAmountSold = 0.0
    for line in securitiesMap.get(security):
        parts = line.split(',')
        if (len(parts) >= 3):
            amountSold = 0 if parts[5].replace('-', '').strip() == "" else parts[5].replace('-', '').strip()
            accumulatedAmountSold += float(amountSold)
    return accumulatedAmountSold


def getAmountBought(security):
    accumulatedAmountBought = 0.0
    for line in securitiesMap.get(security):
        parts = line.split(',')
        if (len(parts) >= 3):
            amountBought = 0 if parts[4].strip() == "" else parts[4].strip()
            accumulatedAmountBought += float(amountBought)
    return accumulatedAmountBought


def getSecurityFromLineParts(parts):
    return parts[3].replace('"', '').strip()


def getCurrencyFromLineParts(parts):
    return parts[1].replace('"', '').strip()


def getTransactionDateFromLineParts(parts):
    return parts[2].replace('"', '').strip()


def getCostFromLineParts(parts):
    return float(0 if parts[7].strip() == "" else parts[7].replace('-', '').strip())


def getProceedsFromLineParts(parts):
    return float(0 if parts[8].strip() == "" else parts[8].replace('-', '').strip())


def getCommissionsFromLineParts(parts):
    return float(0 if parts[9].strip() == "" else parts[9].replace('-', '').strip())


def getUnitsBoughtFromLineParts(parts):
    return int(0 if parts[4].replace('-', '').strip() == "" else parts[4].replace('-', '').strip())


def getUnitsSoldFromLineParts(parts):
    return int(0 if parts[5].replace('-', '').strip() == "" else parts[5].replace('-', '').strip())


def getPriceFromLineParts(parts):
    return float(0 if parts[6].replace('-', '').strip() == "" else parts[6].replace('-', '').strip())


def isValidTransactionLine(parts):
    if len(parts) >= 3:
        transactionDate = getTransactionDateFromLineParts(parts)
        dateParts = transactionDate.split()
        if len(dateParts) == 3:
            return True
    return False

def writeOutputLine(line):
    f = open("output.csv", "a")
    f.write(line.strip() + '\n')
    f.close()

def processSecurity(normalized_security):
    if 'SP--255' in normalized_security:
        print(normalized_security)
    transaction_group = TransactionGroup()
    targetAmountSold = getAmountSold(normalized_security)
    accumulatedBoughtShareCount = 0.0
    if targetAmountSold > 0:
        for line in securitiesMap.get(normalized_security):
            rawTransaction = RawTransaction(line)
            if rawTransaction.isValid:
                if (accumulatedBoughtShareCount >= targetAmountSold):
                    if rawTransaction.isSell():
                        transaction_group.appendTransaction(rawTransaction)
                else:
                    transaction_group.appendTransaction(rawTransaction)
                    if (rawTransaction.unitsBought > 0):
                        accumulatedBoughtShareCount += rawTransaction.unitsBought
        transaction_group.writeToFile()


def printOptionParts(security):
    for line in securitiesMap.get(security):
        rawTransaction = RawTransaction(line)
        if rawTransaction.isOption():
            writeOutputLine("{}  --  {}".format(rawTransaction.security, rawTransaction.normalized_security))


def printOptionsNeverSold(securitiesMap):
    for normalized_security in securitiesMap:
        for line in securitiesMap.get(normalized_security):
            rawTransaction = RawTransaction(line)
            if rawTransaction.isOption():
                if getAmountSold(normalized_security) == 0:
                    print('this option was never sold: ' + rawTransaction.normalized_security)


def printOptionsNeverBought(securitiesMap):
    for normalized_security in securitiesMap:
        for line in securitiesMap.get(normalized_security):
            rawTransaction = RawTransaction(line)
            if rawTransaction.isOption():
                if getAmountBought(normalized_security) == 0:
                    print('this option was never bought: ' + rawTransaction.normalized_security)

def printOptionsBuySellMismatch(securitiesMap):
    for normalized_security in securitiesMap:
        boughtAmount = getAmountBought(normalized_security)
        soldAmount = getAmountSold(normalized_security)
        if boughtAmount != soldAmount:
            print('buy sell amount mismatch: ' + normalized_security)


monthsMap = {
    "JAN": "01",
    "FEB": "02",
    "MAR": "03",
    "APR": "04",
    "MAY": "05",
    "JUN": "06",
    "JUL": "07",
    "AUG": "08",
    "SEP": "09",
    "OCT": "10",
    "NOV": "11",
    "DEC": "12",
}

securitiesMap = {}
remainingMap = {}

# Retrieved from https://www.bankofcanada.ca/valet/series/FXUSDCAD/csv
fx_file = open('FXUSDCAD.csv', 'r')
fx_lines = fx_file.readlines()

transactions_file = open('Tax-Document_3879J6USD_Investment-Income---Trading-Summary--csv---Feb-28--2024_2023.csv', 'r')
#ransactions_file = open('Tax-Document_3879J6CAD_Investment-Income---Trading-Summary--csv---Feb-28--2024_2023.csv', 'r')
#transactions_file = open('temp.csv', 'r')
transactions_lines = transactions_file.readlines()

extras_file = open('extras.csv', 'r')
extras_lines = extras_file.readlines()

excludes_file = open('excludes.csv', 'r')
excludes_lines = excludes_file.readlines()

writeOutputLine("SECURITY, SHARES, COST BASIS, PROCEEDS, GAIN/LOSS")
processSecuritiesToDictionary()
printOptionsNeverSold(securitiesMap)
printOptionsNeverBought(securitiesMap)
printOptionsBuySellMismatch(securitiesMap)

for normalized_security in securitiesMap:
    processSecurity(normalized_security)
#processSecurity("CALL--TSLA--22--JA--1100")
#processSecurity("CALL--TSLA--21--AG--730")
#processSecurity("CALL--TSLA--21--AG--720")
