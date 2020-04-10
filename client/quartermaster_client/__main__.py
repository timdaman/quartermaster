import sys

if sys.version_info[0] != 3 or sys.version_info[1] < 7:
    print("You must run this program using Python 3 version 3.7 or higher")
    exit(1)

from client.app import main

main(sys.argv[1:])
