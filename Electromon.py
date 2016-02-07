import sys
import datetime
import time
import gspread
import json
import random
from oauth2client.client import SignedJwtAssertionCredentials
from threading import Thread

class FlashDetector(Thread):

	def __init__(self, flashTimes):
		Thread.__init__(self)
		self.flashTimes = flashTimes
		
	def run(self):
		for val in range(100):
			minMs = 500
			maxMs = 4000
			v = random.randint(minMs, maxMs) / 1000
			time.sleep(v)
			nowTime = datetime.datetime.now()
			print ">>>>" + nowTime.strftime('%d/%m/%Y %H:%M:%S')
			self.flashTimes.append( nowTime )

class PerTimeSliceFlashCounter():

	def __init__(self, timeSliceDurationInS ):
		self.timeSliceDurationInS = timeSliceDurationInS

	def processDateTimes( self, dateTimes ):
		result = []
		dateTimeIndex = 0
		numDateTimes = len(dateTimes)
		while ( dateTimeIndex<numDateTimes ):
			numFlashesInSlice = 0
			sliceStartDate =  dateTimes[dateTimeIndex].date()
			sliceIndex = self._getTimeSliceIndex( dateTimes[dateTimeIndex] )
			while ( dateTimeIndex<numDateTimes and self._getTimeSliceIndex(dateTimes[dateTimeIndex])==sliceIndex ):
				numFlashesInSlice += 1
				dateTimeIndex += 1

			sliceStartTime = self._getTimeSliceStartTime(sliceIndex)
			sliceStartDateTime = datetime.datetime( sliceStartDate.year, sliceStartDate.month, sliceStartDate.day, sliceStartTime[0], sliceStartTime[1], sliceStartTime[2] )
			#print "#" + str(sliceIndex) + " " + str(sliceStartDateTime) +  " " + str(numFlashesInSlice)
			result.append( (sliceStartDateTime, numFlashesInSlice) )
		return result

	def _getTimeSliceIndex( self, dateTime ):
		numSeconds = (dateTime.hour * 3600) + (dateTime.minute * 60) + (dateTime.second) + (dateTime.microsecond/1000000)
		timeSliceNumber = int(numSeconds / self.timeSliceDurationInS)
		return timeSliceNumber

	def _getTimeSliceStartTime( self, timeSliceIndex ):
		numSeconds = timeSliceIndex * self.timeSliceDurationInS
		hours = numSeconds / 3600
		numSeconds -= hours*3600
		minutes = numSeconds / 60
		numSeconds -= minutes * 60 
		seconds = numSeconds
		return (hours, minutes, seconds)

		
class FlashCountSender(): 

	def __init__(self, jsonFileName, worksheetName):
		print 'Initializing sender...'
		json_key = json.load(open(jsonFileName))
		scope = ['https://spreadsheets.google.com/feeds']
		credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
		gc = gspread.authorize(credentials)
		self.worksheet = gc.open(worksheetName).sheet1
		print 'Sender initialized'

	def sendFlashCounts( self, flashCounts ):
		for flashCount in flashCounts:
			self.sendFlashCount(flashCount)

	def sendFlashCount( self, flashCount ):
		dateTimeString = flashCount[0].strftime('%d/%m/%Y %H:%M:%S')
		count = flashCount[1]
		self.worksheet.append_row( [dateTimeString, count] )

def connectAndDoStuff():

	json_key = json.load(open('Electromon-9ec05e526bcd.json'))
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
	gc = gspread.authorize(credentials)
	wks = gc.open("Electromon").sheet1
	#wks.update_acell('B2', "it's down there somewhere, let me take another look.")


	#val = int( wks.acell('B1').value )
	#print val
	#val = val + 1
	#wks.update_acell('B1', str( val ))

	#c = wks.row_count
	#print "row count " + str(c)

	#wks.add_rows(2)
	#for val in range(5):
	#	wks.append_row( ['blabla', datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'), val ] )
	
	# 1:28
	#for i in range(100):
	#	wks.update_cell( i+2, 1, datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S') )

	# 0:40
	a = []
	for i in range(1, 100):
		c = wks.cell( i, 1 )
		c.value = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
		a.append( c )
	wks.update_cells( a )

	# 0:40
	#a = []
	#for i in range(1, 100):
	#	c = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
	#	a.append( c )
	#wks.append_row( a )

#connectAndDoStuff()


#print "hello"
#obj = MyClass(12)
#obj.showStuff()
#obj.run()
#obj.aStaticFunc()

flashTimes = []
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 00) )
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 02) )
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 03) )
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 03, 500000 ) )
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 9, 999000) )
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 11) )
flashTimes.append( datetime.datetime(2016, 02, 07, 12, 00, 12) )
#thread1 = FlashDetector(flashTimes)
#thread1.start()
#time.sleep(8)
print 'enum'
for i, t in enumerate(flashTimes):
	print t.strftime('%d/%m/%Y %H:%M:%S')
		
counter = PerTimeSliceFlashCounter(5)
r = counter.processDateTimes( flashTimes )
print '=>' + str(r)
#thread1.join()

sender = FlashCountSender('Electromon-9ec05e526bcd.json', "Electromon")
sender.sendFlashCounts( r )