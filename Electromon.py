import sys
import datetime
import time
import gspread
import json
import random
from oauth2client.client import SignedJwtAssertionCredentials
import threading

import platform
if platform.system()=='Linux':
	import RPi.GPIO as GPIO

	class GPIOTimeReader():

		def __init__(self, pin):
			print 'GPIO Time Reader!'
			self.pin = pin
			GPIO.setmode(GPIO.BOARD)

		def readTime(self):
			t0 = datetime.datetime.now()
			GPIO.setup(self.pin, GPIO.OUT)
			GPIO.output(self.pin, GPIO.LOW)
			time.sleep(0.1)
			GPIO.setup(self.pin, GPIO.IN)
			while (GPIO.input(self.pin)==GPIO.LOW):
			        time.sleep(0.05)
			delta = datetime.datetime.now()-t0
			return delta.total_seconds()

		def cleanup(self):
			print '!!!!!!!!!!!!!!cleanup'
			GPIO.cleanup()

else:
	class GPIOTimeReader():

		def __init__(self, pin):
			print 'Mock Time Reader!'
			self.pin = pin
			self.times = [ 0.5, 0.6, 0.7, 0.8 ]
			self.timeIndex = 0

		def readTime(self):
			t = self.times[self.timeIndex]
			self.timeIndex += 1
			if self.timeIndex>=len(self.times):
				self.timeIndex = 0
			time.sleep(t)
			return t

		def cleanup(self):
			print '!!!!!!!!!!!!!!cleanup'
			
class FlashLogger():

	def __init__(self, gpioTimeReader, filename):
		self.gpioTimeReader = gpioTimeReader
		self.file = open(filename, "w")

	def run(self):
		while ( True ):
			v = self.gpioTimeReader.readTime()
			td = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S') 
			text = td + ";" + str(v)
			print text
			self.file.write( text + '\n' )
			
			#t = time.strptime(td, '%d/%m/%Y %H:%M:%S') 
			#print str(t)

	def cleanup(self):
		self.file.close()
		self.gpioTimeReader.cleanup()

class FlashDetector(threading.Thread):

	def __init__(self, gpioTimeReader):
		threading.Thread.__init__(self)
		self.gpioTimeReader = gpioTimeReader
		self.flashTimes = []
		self.lock = threading.Lock()
		self.stopRequest = False
		self.lastTimeValue = 0

	def run(self):
		while ( not self.stopRequest ):
			v = self.gpioTimeReader.readTime()
			if v<self.lastTimeValue: 
				nowTime = datetime.datetime.now()
				#print ">>>>" + str(len(self.flashTimes)) + " " + nowTime.strftime('%d/%m/%Y %H:%M:%S')  
				with self.lock:
					self.flashTimes.append( nowTime )
			self.lastTimeValue = v

	def flushFlashTimes(self):
		with self.lock:
			flashTimes = list(self.flashTimes)
			del self.flashTimes[:]
		return flashTimes

	def cleanup(self):
		print('!!!!!!!!!!!!!!!!cleanup in flash')
		self.stopRequest = True
		self.join()
		self.gpioTimeReader.cleanup()

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


class Electromon():

	def __init__(self):

		print 'Electromon!'
		print '==========='
		self.gpioTimeReader = GPIOTimeReader(7)
		self.flashTimes = []
		self.flashDetector = FlashDetector(self.gpioTimeReader)
		self.flashCounter = PerTimeSliceFlashCounter(5)
		self.flashCountSender = FlashCountSender('Electromon-9ec05e526bcd.json', "Electromon");
		self.stopRequest = False

	def run(self):
		self.flashDetector.start()		# Start the detector thread
		while ( not self.stopRequest ):
			flashTimes = self.flashDetector.flushFlashTimes()
			if ( len(flashTimes)>0 ):
				flashCounts = self.flashCounter.processDateTimes( flashTimes )
				self.flashCountSender.sendFlashCounts( flashCounts )
			time.sleep(5)

	def cleanup(self):
		print 'CLEANUP!'
		self.flashDetector.cleanup()

def main():
	electromon = Electromon()
	try:
		electromon.run()
	finally:
		print 'interrupted!'
		electromon.cleanup()

def mainLog():
	try:
		gpioTimeReader = GPIOTimeReader(7)
		flashLogger = FlashLogger(gpioTimeReader, "flashes.csv")
		flashLogger.run()
	finally:
		flashLogger.cleanup()


mainLog()

def tests():
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