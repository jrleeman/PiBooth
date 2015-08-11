import sys
import pygame
import picamera
import RPi.GPIO as GPIO
from time import sleep, strftime, gmtime
import os


def drawText(font, textstr, clear_screen=True, color=(250, 10, 10)):
    if clear_screen:
        screen.fill(black)  # black screen

    # Render font
    pltText = font.render(textstr, 1, color)

    # Center text
    textpos = pltText.get_rect()
    textpos.centerx = screen.get_rect().centerx
    textpos.centery = screen.get_rect().centery

    # Blit onto screen
    screen.blit(pltText, textpos)

    # Update
    pygame.display.update()


def clearScreen():
    screen.fill(black)
    pygame.display.update()


def doCountdown(pretext="Ready", pretext_fontsize=600, countfrom=5):
    pretext_font = pygame.font.Font(None, pretext_fontsize)
    drawText(pretext_font, pretext)
    sleep(1)
    clearScreen()

    # Count down on the display from 5 to 1
    for i in range(countfrom, 0, -1):
        print "Countdown: ", i
        drawText(bigfont, str(i))
        outputToggle(ledPin, False, time=0.125)
        outputToggle(ledPin, True, time=0.125)
        outputToggle(ledPin, False, time=0.125)
        outputToggle(ledPin, True, time=0.125)
        outputToggle(ledPin, False, time=0.125)
        outputToggle(ledPin, True, time=0.125)
        outputToggle(ledPin, False, time=0.125)
        outputToggle(ledPin, True, time=0.125)

    # Clear the screen one final time so no numbers are left
    clearScreen()


def takePhoto():
    camera.brightness = photoBrightness
    time_stamp = strftime("%Y_%m_%dT%H_%M_%S", gmtime())
    camera.capture("/home/pi/photobooth_photos/%s.jpg" % time_stamp)
    camera.brightness = previewBrightness
    # Can add use_video_port=True to the capture call, which does prevent
    # the preview from not matching the captured size. This seemed to
    # signifcantly degrade the capture quality though, so I let it be.


def outputToggle(pin, status, time=False):
    GPIO.output(pin, status)
    if time:
        sleep(time)
    return status


def photoButtonPress(event):
    sleep(0.1)
    if GPIO.input(photobuttonPin) != GPIO.LOW:
        print "Photo button pin status was: ", GPIO.input(photobuttonPin)
        return
    sleep(1)
    outputToggle(auxlightPin, True)
    sleep(2)
    doCountdown()
    takePhoto()
    sleep(1)
    doCountdown()
    takePhoto()
    sleep(1)
    doCountdown(pretext="One More", pretext_fontsize=400)
    takePhoto()
    sleep(1)
    outputToggle(auxlightPin, False)


def shutdownPi():
    # shutdown our Raspberry Pi
    os.system("sudo shutdown -h now")


def shutdownButtonPress(event):
    sleep(3)
    if GPIO.input(shutdownbuttonPin) != GPIO.LOW:
        return
    print "Shutdown button detected!"
    safeClose()
    shutdownPi()


def safeClose():
    print "Doing safe close-out"
    outputToggle(ledPin, False)
    outputToggle(auxlightPin, False)
    camera.stop_preview()
    camera.close()
    GPIO.cleanup()

# Initial Setup

if not os.path.exists('/home/pi/photobooth_photos'):
    os.makedirs('/home/pi/photobooth_photos')

pygame.init()

# Constants
ledPin = 19  # GPIO of the indicator LED
auxlightPin = 20  # GPIO of the AUX lighting output
photobuttonPin = 17  # GPIO of the photo push button
shutdownbuttonPin = 18  # GPIO of the shutdown push button
previewBrightness = 60  # Lighter than normal to offset the alpha distortion
photoBrightness = 57  # Darker than preview since there is no alpha
photoContrast = 0  # Default

size = width, height = 1280, 720
black = 0, 0, 0

screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
bigfont = pygame.font.Font(None, 800)
smfont = pygame.font.Font(None, 600)
tinyfont = pygame.font.Font(None, 300)

# Setup camera
camera = picamera.PiCamera()
camera.resulotion = (2592, 1944)  # 1280,720 also works for some setups
camera.framerate = 10  # slower is necessary for high-resolution
camera.brightness = previewBrightness  # Turned up so the black isn't too dark
camera.preview_alpha = 210  # Set transparency so we can see the countdown
camera.hflip = True
camera.start_preview()

# Fill screen
screen.fill(black)

# Turn off mouse
pygame.mouse.set_visible(False)

# Setup and tie GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(photobuttonPin, GPIO.IN, GPIO.PUD_UP)  # Take photo button
GPIO.setup(shutdownbuttonPin, GPIO.IN, GPIO.PUD_UP)  # Shutdown button
GPIO.setup(ledPin, GPIO.OUT)  # Front LED
GPIO.setup(auxlightPin, GPIO.OUT)  # Aux Lights
GPIO.add_event_detect(photobuttonPin, GPIO.FALLING,
                      callback=photoButtonPress, bouncetime=1000)
GPIO.add_event_detect(shutdownbuttonPin, GPIO.FALLING,
                      callback=shutdownButtonPress, bouncetime=1000)

outputToggle(ledPin, True)  # Turn on the camera "power" LED

# Main loop... just waiting
while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print "QUIT event detected"
            safeClose()
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            # Quit the program on escape
            if event.key == pygame.K_ESCAPE:
                safeClose()
                sys.exit()

            # Adjust brightness with the up and down arrows
            if event.key == pygame.K_UP:
                photoBrightness += 1
                previewBrightness += 1
                camera.brightness = previewBrightness
                print "New brightness (preview/photo): %d/%d" % (
                        photoBrightness, previewBrightness)
            if event.key == pygame.K_DOWN:
                photoBrightness -= 1
                previewBrightness -= 1
                camera.brightness = previewBrightness
                print "New brightness (preview/photo): %d/%d" % (
                        photoBrightness, previewBrightness)

            # Adjust contrast with the right and left arrows
            if event.key == pygame.K_RIGHT:
                photoContrast += 1
                camera.contrast = photoContrast
                print "New contrast: %d" % (photoContrast)
            if event.key == pygame.K_LEFT:
                photoContrast -= 1
                camera.contrast = photoContrast
                print "New contrast: %d" % (photoContrast)

        else:
            pass
