import time
import os


# define the countdown func.
def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs)
        print(timer, end="\r")
        time.sleep(1)
        t -= 1

        # save the time to a file with each line being a new time
        with open('time.txt', 'a') as f:
            f.write(timer + '\n')
        print(t)

# input time in seconds
t = input("Enter the time in seconds: ")

# check if file exists
if os.path.exists("timer_out.txt"):
    # then delete the file
    os.remove("timer_out.txt")
    # and restart the timer with the new time
    countdown(int(t))
else:
    # if file doesn't exist then just start the timer
    countdown(int(t))
