from piston import Steem
from piston.account import Account
from piston.post import Post
import datetime
import time
import csv
import sys


from pprint import pprint

skipyear = 2017
lastyear = 2016
user = 'pharesim'
s = Steem(['wss://steemd.pevo.science'])

prices = 'btcusd_investingcom.csv'
eurusd = 'eurusd_investingcom.csv'

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

def convertInvestingcomDate(value,offset):
  return datetime.datetime.fromtimestamp(
      time.mktime(datetime.datetime.strptime(value, "%b %d, %Y").timetuple())+offset
    ).strftime('%Y-%m-%d')


#Dateien einlesen
prices = csv_to_list(prices,{'purgeTitle':1})
eurusd = csv_to_list(eurusd,{'purgeTitle':1})

#Durchschnittliche Bitcoinwerte in einfaches Dictionary {datum:preis}
avg = {}
for row in prices:
  if row[0] != '':
    i = 0
    while i < 300:
      date = convertInvestingcomDate(row[0],(86400*i))
      if date not in avg and (i == 0 or i != len(avg)):
        avg[date] = float(row[1])
      else:
        i = 300

      i = i + 1

#Durchschnittliche Eurowerte in einfaches Dictionary {datum:preis}, 2 tage auffuellen wenn noetig
eur = {}
for row in eurusd:
  if row[0] != '':
    i = 0
    while i < 300:
      date = convertInvestingcomDate(row[0],(86400*i))
      if date not in eur and (i == 0 or i != len(eur)):
        eur[date] = float(row[1])
      else: 
        i = 300

      i = i + 1

myfile = open('author_rewards.csv','w')
wr = csv.writer(myfile, delimiter=';')
wr.writerow(['date', 'reward', 'btc', 'eur', 'post'])

i = 10000000
while i > 1:
  a = Account(user,s)
  tx = a.rawhistory(i,1000)
  tx = list(tx)

  for ndx, member in enumerate(tx):
    i = member[0] - 1
    if member[1]['op'][0] == 'author_reward':
      id = '@'+member[1]['op'][1]['author']+'/'+member[1]['op'][1]['permlink']
      p = Post(id,s)
      reward = float(str(p.reward)[:-4])
      post = p.export()
      dt = post['last_payout']
      unixtime = time.mktime(dt.timetuple())
      value = datetime.datetime.fromtimestamp(unixtime)
      year = int(value.strftime('%Y'))
      month = int(value.strftime('%m'))
      date = value.strftime('%Y-%m-%d')
      if year < lastyear:
        myfile.close()
        sys.exit('DONE')

      if year != skipyear:
        btc = round(reward/avg[date],8)
        euros = round(reward/eur[date],3)
        print(id)
        print(reward)
        print(btc)
        print(euros)
        pprint(date)
        wr.writerow([date,reward,btc,euros,id])
