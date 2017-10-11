import csv
from collections import OrderedDict
import copy

# Verwendete Dateien 
prices = '01_bitcoinaverage.csv'
polotx = '02_polo_transaction_history.csv'
lending = '03_polo_lending_history.csv'
bittrex = '04_bittrex_transaction_history.csv'
onebroker = '05_1broker_transaction_history.csv'
advcash = '06_advcash_transaction_history_relevant.csv'
xapo = '07_xapo_transaction_history.csv'
cashila = '08_cashila_deposit_history.csv'
bitwala = '09_bitwala_deposit_history.csv'
buys = '10_ausgaben.csv'
income = '11_einnahmen.csv'

# Hilfsfunktion für Dateien
def csv_to_list(filename,options):
  #Datei lesend öffnen
  with open(filename, 'r') as f:
    #Liste erstellen
    res = list(csv.reader(f))
    
    #Titel entfernen
    if 'purgeTitle' in options and options['purgeTitle'] == 1:
      del res[0]

    #aufsteigend nach Datum sortieren
    if 'reverse' in options and options['reverse'] == 1:
      res = res[::-1]

  return res


#Dateien einlesen
prices = csv_to_list(prices,{'purgeTitle':1})
polotx = csv_to_list(polotx,{'purgeTitle':1, 'reverse':1})
lending = csv_to_list(lending,{'purgeTitle':1, 'reverse':1})
bittrex = csv_to_list(bittrex,{'purgeTitle':1, 'reverse':1})
onebroker = csv_to_list(onebroker,{'purgeTitle':1, 'reverse':1})
advcash = csv_to_list(advcash,{'purgeTitle':1, 'reverse':1})
xapo = csv_to_list(xapo,{'purgeTitle':1, 'reverse':1})
cashila = csv_to_list(cashila,{'purgeTitle':1})
bitwala = csv_to_list(bitwala,{'purgeTitle':1})
buys = csv_to_list(buys,{'purgeTitle':1})
income = csv_to_list(income,{'purgeTitle':1})


#Durchschnittliche Bitcoinwete in einfaches Dictionary {datum:preis}
avg = {}
for row in prices:
  avg[row[0][0:10]] = float(row[3])


#Einnahmen verrechnen

#Hilfsfunktion für Einnahmen
def income_booking(date,incomes,amount):
  add = {}
  if date in incomes:
    incomes[date] = incomes[date] + amount
  else:
    incomes[date] = amount

  return incomes


#poloniex trades
incomes = {}
lastdate = 0
balance = 0
change = 0
for item in polotx:
  ts = item[0]
  date = ts[0:10]
  if date != lastdate:
    if lastdate != 0:
      incomes[lastdate] = change

    change = float(item[9])
    lastdate = date
  else:
    change += float(item[9])

#poloniex interest
for item in lending:
  ts = item[8]
  date = ts[0:10]
  item[6] = float(item[6])
  incomes = income_booking(date, incomes, item[6])

#bittrex trades
for item in bittrex:
  ts = item[0]
  date = ts[6:10]+'-'+ts[0:2]+'-'+ts[3:5]
  item[8] = float(item[8])
  incomes = income_booking(date, incomes, item[8])

#onebroker trades
for item in onebroker:
  if item[1] != 'WITHDRAW' and item[1] != 'DEPOSIT':
    ts = item[0]
    date = ts[0:10]
    change = float(item[2])
    incomes = income_booking(date, incomes, change)

#various income
for item in income:
  date = item[0]
  change = float(item[1])
  incomes = income_booking(date, incomes, change)

incomes = OrderedDict(sorted(incomes.items()))

#Hilfsfunktion zum verrechnen von negativen Einnahmen
def withdraw(av,amount,date):
  tmp = 0
  av = OrderedDict(sorted(av.items()))
  for key, value in av.items():
    if key >= date:
      av[tmp][0] += amount
      if av[tmp][0] < 0:
        avx = copy.deepcopy(av)
        x = withdraw(avx, av[tmp][0], tmp)
        x[tmp][0] = 0
        return x
      else:
        return av

    tmp = key


#täglich verfügbare Bitcoin
available = {}
for key, value in incomes.items():
  if value > 0:
    available[key] = [value, 0]
  else:
    available[key] = [0, 0]
    avc = copy.deepcopy(available)
    available = withdraw(avc,value,key)


#Ausgaben verrechnen
expenses = {}

#Hilfsfunktion für Ausgaben
def spend(av,amount,rate,date,ex,last=''):
  av = OrderedDict(sorted(av.items()))
  for key, value in av.items():
    if value[0] > 0:
      av[key][0] -= amount

      if av[key][0] >= 0:
        av[key][1] += amount
        ex[date][2] = avg[key]

        return av, ex

      else:
        new_amount = av[key][0] * -1
        paid_off = amount - new_amount
        if paid_off > 0:
          old_paid = av[key][1]
          old_rate = ex[date][2]
          new_paid = old_paid + paid_off
          new_rate = (round((old_rate * old_paid)*100)/100 + round((paid_off * avg[key])*100)/100) / new_paid
          av[key][1] = new_paid
          ex[date][2] = new_rate
        
        av[key][1] = 0
        
        av, ex = spend(av, new_amount, rate, date, ex, key)
        return av, ex
        


#advcash
for item in advcash:
  if item[7] != '':
    if item[0] not in incomes:
      incomes[item[0]] = 0
    if item[0] not in available:
      available[item[0]] = [0, 0]
    if item[0] in expenses:
      #Ausgegebene BTC
      expenses[item[0]][0] += float(item[3])
      #Erzielter Wechselkurs
      expenses[item[0]][1] += expenses[item[0]][0] / ((float(item[8]) * float(item[3])) + ((expenses[item[0]][0] - float(item[3])) * expenses[item[0]][1]))
    else:
      #Ausgegebene BTC
      expenses[item[0]] = [float(item[3]), float(item[8]), 0]

#xapo
for item in xapo:
  if item[8] == '' and item[7] != 'Canceled':
    ts = item[0]
    date = ts[0:10]
    if date not in incomes:
      incomes[date] = 0
    if date not in available:
      available[date] = [0, 0]
    if item[4] != '':
      spent = float(item[4])*-1
      factor = -1
    else:
      spent = float(item[3])
      factor = 1
    if date in expenses:
      #Ausgegebene BTC
      expenses[date][0] += spent
      #Erzielter Wechselkurs
      expenses[date][1] = (((expenses[date][0] - spent) * expenses[date][1]) + float(item[6]) * factor) / expenses[date][0]
    else:
      #Ausgegebene BTC
      if spent != 0:
        expenses[date] = [spent, (float(item[6]) / spent)*factor, 0]

    expenses[date][0] = expenses[date][0]


#Helferfunktion zum Ausgaben verbuchen
def add_to_expenses(platform,incomes,available,expenses):
  for item in platform:
    date = item[0]
    if date not in incomes:
      incomes[date] = 0
    if date not in available:
      available[date] = [0, 0]
    spent = float(item[1])
    rate = float(item[2]) / spent
    if date in expenses:
      expenses[date][0] += spent
      expenses[date][1] = (round(((expenses[date][0] - spent) * expenses[date][1])*100)/100 + round(float(item[2])*100)/100) / expenses[date][0]
    else:
      expenses[date] = [spent, rate, 0]

  return expenses, incomes, available

#cashila
expenses, incomes, available = add_to_expenses(cashila,incomes,available,expenses) 
#bitwala
expenses, incomes, available = add_to_expenses(bitwala,incomes,available,expenses) 
#buys
expenses, incomes, available = add_to_expenses(buys,incomes,available,expenses) 

expenses = OrderedDict(sorted(expenses.items()))
for key, value in expenses.items():
  available, expenses = spend(available,value[0],value[1],key,expenses)

incomes = OrderedDict(sorted(incomes.items()))

#write to file
myfile = open('98_bitcoins_daily_report.csv','w')
wr = csv.writer(myfile, delimiter=';')
wr.writerow(['date', 'balance', 'change', 'price', 'profit', 'total', 'ausgaben', 'ausgegeben', 'realkurs', 'kursgewinn', 'verbleibend'])
lastval = 0
sum = 0
total = 0
for key, value in incomes.items():
  sum += value
  total += value * float(avg[key])
  if key not in expenses:
    expenses[key] = [0, 0, 0]

  profit = (avg[key] - expenses[key][2]) * expenses[key][0]
  print(key+" "+str(sum)+" "+str(value)+" "+str(avg[key])+" "+str(value*avg[key])+" "+str(total)+" "+str(expenses[key][0])+" "+str(available[key][1])+" "+str(expenses[key][1])+" "+str(profit)+" "+str(available[key][0]))
  wr.writerow([key, str(sum), str(value), str(avg[key]), str(value*avg[key]), str(total),  str(expenses[key][0]), str(round(available[key][1]*100000000)/100000000), str(expenses[key][1]), str(profit), str(available[key][0])])
myfile.close()
