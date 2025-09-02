import threading
from eSSP.constants import Status
from eSSP import eSSP
from time import sleep

#  Create a new object ( Validator Object ) and initialize it ( In debug mode, so it will print debug infos )
validator = eSSP(com_port="/dev/ttyACM0", ssp_address="0", route_to_storage=2000, debug=True)

def event_loop():
    while True:
        # ---- Example of interaction with events ---- #
        last = validator.get_last_event()
        if last is not None:
            (note, event) = last
            if note == None or event == 0:
                pass  # Operation that do not send money info, we don't do anything with it
            else:
                print(last)
                if event == Status.SSP_POLL_CREDIT:
                    validator.print_debug("credit")
        sleep(0.2)

t1 = threading.Thread(target=event_loop)  # Create a new thread on the Validator System Loop ( needed for the signal )
t1.daemon = True  # Set the thread as daemon because it don't catch the KeyboardInterrupt, so it will stop when we cut the main thread
t1.start()  # Start the validator system loop thread ( Needed for starting sending action )

try:  # Command Interpreter
    while True:
        choice = input("")
        if choice == "p":  # Payout "choice" value bill ( 10, 20, 50, 100, etc. )
            choice = input("")
            validator.payout(int(choice))
        elif choice == "s":  # Route to storage ( In NV11, it is any amount <= than "choice" )
            choice = input("")
            validator.set_route_storage(int(choice))
        elif choice == "c":  # Route to cashbox ( In NV11, it is any amount <= than "choice" )
            choice = input("")
            validator.set_route_cashbox(int(choice))
        elif choice == "e":  # Enable ( Automaticaly disabled after a payout )
            validator.enable_validator()
        elif choice == "r":  # Reset ( It's like a "reboot" of the validator )
            validator.reset()
        elif choice == "d":  # Disable
            validator.disable_validator()
            print("disable")
        elif choice == "D":  # Disable the payout device
            validator.disable_payout()
        elif choice == "E":  # Empty the storage to the cashbox
            validator.empty_storage()
        elif choice == "g":  # Get the number of bills denominated with their values
            choice = input("")
            validator.get_note_amount(int(choice))
            sleep(1)
            print("Number of bills of %s : %s"%(choice, validator.response_data['getnoteamount_response']))
        elif choice == "v":  # View validator state
            print(validator)

except KeyboardInterrupt:  # If user do CTRL+C
    validator.close()  # Close the connection with the validator
    print("Exiting")
    exit(0)    