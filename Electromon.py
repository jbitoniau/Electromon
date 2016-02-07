import sys
import datetime
import gspread
import json
from oauth2client.client import SignedJwtAssertionCredentials

def connectAndDoStuff():

	json_key = json.load(open('Electromon-9ec05e526bcd.json'))
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)

	gc = gspread.authorize(credentials)

	wks = gc.open("Electromon").sheet1
	wks.update_acell('B2', "it's down there somewhere, let me take another look.")


	val = int( wks.acell('B1').value )
	print val
	val = val + 1
	wks.update_acell('B1', str( val ))

	c = wks.row_count
	print "row count " + str(c)

	#wks.add_rows(2)
	for val in range(5):
		wks.append_row( ['blabla', datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'), val ] )

connectAndDoStuff()

dd = datetime.datetime.now()
#https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
print(dd.strftime('%d/%m/%Y %H:%M:%S'))