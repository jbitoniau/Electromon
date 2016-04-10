import sys
import os
import datetime
import time
import gspread
import math
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

	class GPIOLed():
		def __init__(self, pin):
			print "GPIO LED"
			self.pin = pin
			GPIO.setmode(GPIO.BOARD)
			GPIO.setup(pin, GPIO.OUT)

		def setOn(self):
			GPIO.output(self.pin, GPIO.HIGH)
		
		def setOff(self):
			GPIO.output(self.pin, GPIO.LOW)
			
		def cleanup(self):
			self.setOff()
			GPIO.cleanup()

else:
	class GPIOTimeReader():

		def __init__(self, pin):
			print 'Mock Time Reader'
			self.pin = pin
			self.times = [ 0.5, 0.6, 0.7, 0.8, 0.799, 0.55 ]
			self.timeIndex = 0

		def readTime(self):
			t = self.times[self.timeIndex]
			self.timeIndex += 1
			if self.timeIndex>=len(self.times):
				self.timeIndex = 0
			time.sleep(t)
			return t

		def cleanup(self):
			print 'Mock Time Reader cleanup'

	class GPIOLed():
		def __init__(self, pin):
			print "Mock LED"
			
		def setOn(self):
			print '[x]'
		
		def setOff(self):
			print '[ ]'
			
		def cleanup(self):
			self.setOff()
			
	
class LedBlinker(threading.Thread):
	def __init__(self, led):
		threading.Thread.__init__(self)
		self.stopRequest = False
		self.led = led
		self.blinkDuration = -1
		self.condition = threading.Condition()
		self.start()

	def blink(self, sec):
		if self.blinkDuration!=-1:
			return False
		self.condition.acquire()
		self.blinkDuration = sec
		self.condition.notify()
		self.condition.release()
		return True

	def run(self):
		while True and not self.stopRequest:
			self.condition.acquire()
			if self.blinkDuration!=-1:
				self.led.setOn()
				time.sleep(self.blinkDuration)
				self.led.setOff()
				self.blinkDuration=-1
			self.condition.wait()
			self.condition.release()
		
	def cleanup(self):
		self.stopRequest = True
		self.blink(0)
		self.join()
		self.led.cleanup()

class FlashLogger():

	def __init__(self, gpioTimeReader, filename):
		self.gpioTimeReader = gpioTimeReader
		self.file = open(filename, "w")

	def run(self):
		lastv = self.gpioTimeReader.readTime()
		lastdv = 1;
		while ( True ):
			v = self.gpioTimeReader.readTime()
			#td = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
			td = datetime.datetime.now()
			std = str(td.year) + ";" + str(td.month) + ";" + str(td.day) + ";" + str(td.hour) + ";" + str(td.minute) + ";" + str(td.second) + ";" + str(td.microsecond)
			text = std + ";;" + str(v)
			self.file.write( text + '\n' )

			dv = v - lastv
			diffAsPercentageOfOldValue = 0
			if ( lastv!=0 ):
				diffAsPercentageOfOldValue = (v-lastv) / lastv * 100

			print text + " lastv:" + str(lastv) + " lastdv:" + str(lastdv) + " v:" + str(v) + " dv:" + str(dv) + " diff%:" + str(diffAsPercentageOfOldValue)
			
			if math.fabs(diffAsPercentageOfOldValue)<2.0:
				print "value diff not significant enough. Dropping the value"
			else:
				if ( lastdv>0 and dv<0 ):
					print "FLASH"
					os.system( "aplay beep.wav" )
				lastv = v
				lastdv = dv

	def cleanup(self):
		self.file.close()
		self.gpioTimeReader.cleanup()

class FlashDetector(threading.Thread):

	def __init__(self, gpioTimeReader, led):
		threading.Thread.__init__(self)
		self.gpioTimeReader = gpioTimeReader
		self.flashTimes = []
		self.lock = threading.Lock()
		self.stopRequest = False
		self.lastTimeValue = 0
		self.led = led
		self.ledBlinker = LedBlinker(self.led)
		
	def run(self):

		# If the difference between the current value and the previous one  
		# is less than 2 percent of the previous value in absolute value,
		# the new value is ignored because it's too close to the previous one
		# We want a significant change
		deltaRatioThreshold = 0.02		
		lastValue = self.gpioTimeReader.readTime()
		lastDelta = 1;
		while ( not self.stopRequest ):
			value = self.gpioTimeReader.readTime()
			delta = value - lastValue;
			deltaRatio = delta / lastValue 	
			if ( math.fabs(deltaRatio)>=deltaRatioThreshold ):
				if ( lastDelta>0 and delta<0 ):
					# A flash is detected when the signal was increasing and is now decreasing
					nowTime = datetime.datetime.now()
					#print "flash! #" + str(len(self.flashTimes)) + " " + nowTime.strftime('%d/%m/%Y %H:%M:%S') 
					print "Dtor:> " + nowTime.strftime('%d/%m/%Y %H:%M:%S')
					with self.lock:
						self.flashTimes.append( nowTime )
						self.ledBlinker.blink(0.2)
					#os.system( "aplay beep.wav" )
				lastValue = value
				lastDelta = delta
			else:
				pass 	# We skip this value as it's too close to the previous

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
		self.ledBlinker.cleanup()


def getTimeSliceIndex( dateTime, sliceDurationInS ):
	numSeconds = (dateTime.hour * 3600) + (dateTime.minute * 60) + (dateTime.second) + (dateTime.microsecond/1000000)
	timeSliceNumber = int(numSeconds / sliceDurationInS)
	return timeSliceNumber

# Return a tuple hours, minutes, seconds
def getTimeSliceStartTime( timeSliceIndex, sliceDurationInS ):
	numSeconds = timeSliceIndex * sliceDurationInS
	hours = numSeconds / 3600
	numSeconds -= hours*3600
	minutes = numSeconds / 60
	numSeconds -= minutes * 60 
	seconds = numSeconds
	return (hours, minutes, seconds)

#class PerTimeSliceFlashCounter():
#	def __init__(self, timeSliceDurationInS ):
#		self.timeSliceDurationInS = timeSliceDurationInS
#
#	def processDateTimes( self, dateTimes ):
#		result = []
#		dateTimeIndex = 0
#		numDateTimes = len(dateTimes)
#		while ( dateTimeIndex<numDateTimes ):
#			numFlashesInSlice = 0
#			sliceStartDate =  dateTimes[dateTimeIndex].date()
#			sliceIndex = getTimeSliceIndex( dateTimes[dateTimeIndex], self.timeSliceDurationInS )
#			while ( dateTimeIndex<numDateTimes and getTimeSliceIndex(dateTimes[dateTimeIndex], self.timeSliceDurationInS)==sliceIndex ):
#				numFlashesInSlice += 1
#				dateTimeIndex += 1
#
#			sliceStartTime = getTimeSliceStartTime(sliceIndex, self.timeSliceDurationInS )
#			sliceStartDateTime = datetime.datetime( sliceStartDate.year, sliceStartDate.month, sliceStartDate.day, sliceStartTime[0], sliceStartTime[1], sliceStartTime[2] )
#			#print "#" + str(sliceIndex) + " " + str(sliceStartDateTime) +  " " + str(numFlashesInSlice)
#			result.append( (sliceStartDateTime, numFlashesInSlice) )
#		return result
		
class FlashCountSender(): 

	def __init__(self, jsonFileName, spreadsheetName, worksheetName):
		self.worksheet = None
		self.jsonFileName = jsonFileName
		self.spreadsheetName = spreadsheetName
		self.worksheetName = worksheetName
		self.sendTries = 0
		self.initialize()


	def initialize(self):
		try:
			print 'Sndr: initializing...'
			json_key = json.load(open(self.jsonFileName))
			scope = ['https://spreadsheets.google.com/feeds']
			credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
			gc = gspread.authorize(credentials)
			spreadsheet = gc.open(self.spreadsheetName)
			self.worksheet = spreadsheet.worksheet(self.worksheetName)
		except:
			print "Sndr: initializing error!"
			return False
		print 'Sndr: initializing OK'
		return True

	def sendFlashCounts( self, flashCounts ):
		self.sendTries += 1
		# If we haven't managed to send data 5 times, we try to
		# re-initialize the connection each time we're asked to send
		# until it gets back on its feet
		if self.sendTries>=5:
			if self.initialize():
				self.sendTries = 0
		try:
			for flashCount in flashCounts:
				self.sendFlashCount(flashCount)
		except:
			print "Sndr: error sending " + str(len(flashCounts)) + " flashcounts"
			return False 
		self.sendTries = 0
		return True

	def sendFlashCount( self, flashCount ):
		dateTimeString = flashCount[0].strftime('%d/%m/%Y %H:%M:%S')
		count = flashCount[1]
		self.worksheet.append_row( [dateTimeString, count] )

class Electromon():

	def __init__(self):

		print 'Electromon!'
		print '==========='
		self.gpioTimeReader = GPIOTimeReader(7)
		self.led = GPIOLed(8)
		self.flashDetector = FlashDetector(self.gpioTimeReader, self.led)
		self.sliceDurationInS = 5
		#self.flashCounter = PerTimeSliceFlashCounter(self.sliceDurationInS)
		self.flashCountSender = FlashCountSender('Electromon-9ec05e526bcd.json', "Electromon", "A");
		self.stopRequest = False

	def run(self):
		lastTimeSliceIndex = getTimeSliceIndex( datetime.datetime.now(), self.sliceDurationInS )
		self.flashDetector.start()		# Start the detector thread
		
		perTimeSliceFlashes = {}
		flashCounts = []				# Pending flash counts to send (a send might fail and we need to keep trying)
		while not self.stopRequest:

			time.sleep(3)
			timeSliceIndex = getTimeSliceIndex( datetime.datetime.now(), self.sliceDurationInS )
			
			if timeSliceIndex>lastTimeSliceIndex:
				
				# Fetch flash measures from the detector
				flashTimes = self.flashDetector.flushFlashTimes()

				# Dispatch the flashes per time-slice
				for flashTime in flashTimes:
					#print '>>' + str(flashTime)
					sliceIndex = getTimeSliceIndex( flashTime, self.sliceDurationInS )
					if perTimeSliceFlashes.has_key(sliceIndex):
						perTimeSliceFlashes[sliceIndex] += 1
					else:
						perTimeSliceFlashes[sliceIndex] = 1

				# Go through each past time-slices (stop before the current one) and 
				# prepare the final list of flash counts (per slice start datetime)
				# If a slice didn't have any flash put down a zero for it
				
				sliceStartDate =   datetime.datetime.now().date()		# CRAPPY!!!
				for sliceIndex in range(lastTimeSliceIndex, timeSliceIndex):
					
					sliceStartTime = getTimeSliceStartTime( sliceIndex, self.sliceDurationInS )
					sliceStartDateTime = datetime.datetime( sliceStartDate.year, sliceStartDate.month, sliceStartDate.day, sliceStartTime[0], sliceStartTime[1], sliceStartTime[2] )
					if perTimeSliceFlashes.has_key(sliceIndex):
						flashCounts.append( (sliceStartDateTime, perTimeSliceFlashes[sliceIndex]) ) 
						del perTimeSliceFlashes[sliceIndex]
					else:
						flashCounts.append( (sliceStartDateTime, 0) ) 
			
				for flashCount in flashCounts:
					print "Emon:>   " + flashCount[0].strftime('%d/%m/%Y %H:%M:%S') + " => " + str(flashCount[1])
				
				# Send flash counts
				sentOK = self.flashCountSender.sendFlashCounts( flashCounts )
				if sentOK:
					flashCounts = []

				lastTimeSliceIndex = timeSliceIndex

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

main()

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
