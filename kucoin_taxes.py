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
                if check != transaction.security:
                    raise ValueError('missmatched securities in a security group', ret, transaction.security)
            ret = transaction.security
            check = transaction.security
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

    def __init__(self, line):
        self.line = line
        parts = line.split(',')
        self.isValid = isValidTransactionLine(parts)
        if self.isValid:
            self.security = getSecurityFromLineParts(parts)
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

    def isBuy(self):
        return self.unitsBought > 0

    def isSell(self):
        return self.unitsSold > 0

    def boughtAmount(self):
        return self.price * self.unitsBought

    def convertedBoughtAmount(self):
        return self.boughtAmount() * self.dailyExchangeRate

    def soldAmount(self):
        return self.price * self.unitsSold

    def convertedSoldAmount(self):
        return self.soldAmount() * self.dailyExchangeRate


def getExchangeRateForDayFromLineParts(parts):
    transaction_date = getTransactionDateFromLineParts(parts)
    date_parts = transaction_date.split('-')
    return getExchangeRateForDay(date_parts[0], date_parts[1], date_parts[2])


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
        if (rawTransaction.security in securitiesMap):
            securitiesMap[rawTransaction.security].append(rawTransaction.line)
        else:
            securityLines = [rawTransaction.line]
            securitiesMap[rawTransaction.security] = securityLines
    else:
        print(rawTransaction.line)

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
            amountSold = float(parts[9].strip() if parts[4].strip() == "sell" else 0)
            accumulatedAmountSold += float(amountSold)
    return accumulatedAmountSold


def getSecurityFromLineParts(parts):
    return parts[3].replace('"', '').strip()


def getTransactionDateFromLineParts(parts):
    return parts[0].replace('"', '').strip().split()[0]


def getCostFromLineParts(parts):
    return float(parts[10].strip() if parts[4].strip() == "buy" else 0)


def getProceedsFromLineParts(parts):
    return float(parts[10].strip() if parts[4].strip() == "sell" else 0)


def getCommissionsFromLineParts(parts):
    return float(parts[12].strip())


def getUnitsBoughtFromLineParts(parts):
    return float(parts[9].strip() if parts[4].strip() == "buy" else 0)


def getUnitsSoldFromLineParts(parts):
    return float(parts[9].strip() if parts[4].strip() == "sell" else 0)


def getPriceFromLineParts(parts):
    return float(parts[11].strip())


def isValidTransactionLine(parts):
    if len(parts) >= 3:
        transactionDate = getTransactionDateFromLineParts(parts)
        dateParts = transactionDate.split()
        transactionDate = dateParts[0]
        dateParts = transactionDate.split('-')
        if len(dateParts) == 3:
            return True
    return False

def writeOutputLine(line):
    f = open("output.csv", "a")
    f.write(line.strip() + '\n')
    f.close()

def processSecurity(security):
    transaction_group = TransactionGroup()
    targetAmountSold = getAmountSold(security)
    accumulatedBoughtShareCount = 0.0
    if targetAmountSold > 0:
        for line in securitiesMap.get(security):
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

securitiesMap = {}
remainingMap = {}

# Retrieved from https://www.bankofcanada.ca/valet/series/FXUSDCAD/csv
fx_file = open('FXUSDCAD.csv', 'r')
fx_lines = fx_file.readlines()

transactions_file = open('kucoin_dec_2023.csv', 'r')
transactions_lines = transactions_file.readlines()

extras_file = open('kucoin_extras.csv', 'r')
extras_lines = extras_file.readlines()

excludes_file = open('kucoin_excludes.csv', 'r')
excludes_lines = excludes_file.readlines()

writeOutputLine("SECURITY, SHARES, COST BASIS, PROCEEDS, GAIN/LOSS")
processSecuritiesToDictionary()
for security in securitiesMap:
    processSecurity(security)
