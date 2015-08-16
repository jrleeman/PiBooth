import sys
import pygame
import picamera
import RPi.GPIO as GPIO
from time import sleep, strftime, gmtime
import os


def drawText(font, textstr, clear_screen=True, color=(250, 10, 10)):
    """
    Draws the given string onto the pygame screen.

    Parameters:
    -----------
    font : object
        pygame font object
    textstr: string
        text to be written to the screen
    clean_screan : boolean
        determines if previously shown text should be cleared
    color : tuple
        RGB tuple of font color

    Returns:
    --------
    None
    """
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
    """
    Clears the pygame screen of all drawn objects.

    Parameters:
    -----------
    None

    Returns:
    --------
    None
    """
    screen.fill(black)
    pygame.display.update()


def doCountdown(pretext="Ready", pretext_fontsize=600, countfrom=5):
    """
    Performs on screen countdown

    Parameters:
    -----------
    pretext : string
        Text shown before countdown starts
    pretext_fontsize : int
        Size of pretext font
    countfrom : int
        Number to count down from
    """
    pretext_font = pygame.font.Font(None, pretext_fontsize)
    drawText(pretext_font, pretext)
    sleep(1)
    clearScreen()

    # Count down on the display
    for i in range(countfrom, 0, -1):
        # Draw text on the screen
        drawText(bigfont, str(i))

        # Flash the LED during the second of dead time
        for j in range(4):
            outputToggle(ledPin, False, time=0.125)
            outputToggle(ledPin, True, time=0.125)

    # Clear the screen one final time so no numbers are left
    clearScreen()


def takePhoto():
    """
    Captures and stores a photo from the pi camera board

    Paramters:
    ----------
    None

    Returns:
    --------
    path : str
        path, including filename, of captured photo

    Notes:
    ------
    Can add use_video_port=True to the capture call, which does prevent
    the preview from not matching the captured size. This seemed to
    signifcantly degrade the capture quality though, so I let it be.
    Photos can be trimmed after the fact, or just left as is.
    """
    # Adjust to image capture brightness
    camera.brightness = photoBrightness

    # Grab the capture
    time_stamp = strftime("%Y_%m_%dT%H_%M_%S", gmtime())
    path = "/home/pi/photobooth_photos/%s.jpg" % time_stamp
    camera.capture(path)

    # Go back to preview brightness
    camera.brightness = previewBrightness

    return path


def outputToggle(pin, status, time=False):
    """
    Changes the state of an ouput GPIO pin with optional time delay.

    Parameters:
    -----------
    pin : int
        Pin number to manipulate
    status : boolean
        Status to be assigned to the pin
    time : int, float
        Time to wait before returning (optional)
    """
    GPIO.output(pin, status)
    if time:
        sleep(time)
    return status


def photoButtonPress(event):
    """
    Event handler for the big red photo button.

    Parameters:
    -----------
    event : object
        Button press event from GPIO

    Returns:
    --------
    None
    """
    # Wait for 0.1 sec to be sure it's a person pressing the
    # button, not noise.
    sleep(0.1)
    if GPIO.input(photobuttonPin) != GPIO.LOW:
        return

    # Turn on the lights and let people adjust
    sleep(1)
    outputToggle(auxlightPin, True)
    sleep(2)

    # Take photos
    photo_names = []
    for i in range(number_photos):
        doCountdown()
        fname = takePhoto()
        photo_names.append(fname)
        sleep(1)

    # Turn off the lights
    outputToggle(auxlightPin, False)

    # Tweet the photos
    if tweet_photos:
        if ".txt" in tweet_text:
            text = getRandomTweet(tweet_text)
        else:
            text = tweet_text
        tweetPhotos(photo_names, tweet_text=tweet_text)


def getRandomTweet(fname):
        """
        Gets a random line from a file of possible tweets to go with
        photo posts to Twitter.

        Parameters:
        -----------
        fname : str
            filename

        Returns:
        --------
        tweet : str
            text of random tweet from file
        """
        lines = []
        with open(fname", "r") as f:
            lines = f.readlines()
        random_line_num = random.randrange(0, len(lines))
        return lines[random_line_num].strip('\n\r')


def tweetPhotos(photo_files, tweet_text="Photobooth photos!"):
    """
    Posts photos to twitter with the given tweet text

    Paramters:
    ----------
    photo_files : list
        list of full paths to the files to tweet
    tweet_text  : str
        text to tweet with photos

    Returns:
    --------
    None

    Notes:
    ------
    If you allow many photos per session (>3 photos/button press)
    it is probably a good idea to only tweet a few to save time
    and not make the Twitter API angry. Untested with high numbers.
    """
    responses = []
    media_ids = []
    for photo_file in photo_files:
        photo = open(photo_file)
        response = twitter.upload_media(media=photo)
        responses.append(response)
        media_ids.append(response['media_id'])
    twitter.update_status(status=tweet_text, media_ids=media_ids)


def shutdownPi():
    """
    Shutdown the system totally. Full halt.

    Paramters:
    ----------
    None

    Returns:
    --------
    None
    """
    os.system("sudo shutdown -h now")


def shutdownButtonPress(event, hold_time=3):
    """
    Event handler for the shutdown button. Makes sure that
    the button is held before shutting down completely.

    Parameters:
    -----------
    event : object
        Event from GPIO
    hold_time : int, float
        Time (seconds) the button must be held for shutdown to
        be activated. Helps prevent accidental shutdowns.
    """
    sleep(hold_time)
    if GPIO.input(shutdownbuttonPin) != GPIO.LOW:
        return

    safeClose()
    shutdownPi()


def safeClose():
    """
    Cleanly exits the program by turning off the lights, stopping
    the camera, and cleaning up the resources.

    Parameters:
    -----------
    None

    Returns:
    --------
    None
    """
    outputToggle(ledPin, False)
    outputToggle(auxlightPin, False)
    camera.stop_preview()
    camera.close()
    GPIO.cleanup()

# Setup Parameters
tweet_photos = True
number_photos = 3
tweet_text = "tweet_options.txt"
photo_path = '/home/pi/photobooth_photos'
CONSUMER_KEY = "1fXopQ2aU1b4v9D6ufdJXmAZf"
CONSUMER_SECRET = "16IfaC1dEEQhNKlERU7ggE2GU2id09zVVEsLfgexf7Qa8lPsHb"
ACCESS_TOKEN = "145877180-AHXpU20eA5ofrARcA6FuWMpF1shHlR8iVhLrpFLK"
ACCESS_TOKEN_SECRET = "jGWBAZ7pI2nnObmFwvFCvIzywPEe0riD1LRPoZ4PjOHfU"

# Initial Setup
if not os.path.exists(photo_path):
    os.makedirs(photo_path)

if tweet_photos:
    import twython

    twitter = twython.Twython(
      CONSUMER_KEY,
      CONSUMER_SECRET,
      ACCESS_TOKEN,
      ACCESS_TOKEN_SECRET
    )

pygame.init()

# Pin configuration
ledPin = 19  # GPIO of the indicator LED
auxlightPin = 20  # GPIO of the AUX lighting output
photobuttonPin = 17  # GPIO of the photo push button
shutdownbuttonPin = 18  # GPIO of the shutdown push button

# Camera Settings
previewBrightness = 60  # Lighter than normal to offset the alpha distortion
photoBrightness = 57  # Darker than preview since there is no alpha
photoContrast = 0  # Default

# pygame Settings
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

# Main loop. Waits for keypress events. Everything else is
# an interrupt. Most of the time this just loops doing nothing.
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
