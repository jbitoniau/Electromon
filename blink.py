import RPi.GPIO as GPIO
import time
def blink(pin):
	print '.'
	GPIO.output(pin, GPIO.HIGH)
	time.sleep(1)
	GPIO.output(pin, GPIO.LOW)
	time.sleep(1)
	return

try:
	print 'start!'
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(8, GPIO.OUT)
	for i in range(0, 10):
		blink(8)
finally:
	print 'cleaning up...'
	GPIO.cleanup()
