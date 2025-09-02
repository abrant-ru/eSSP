# !/usr/bin/env python3
import threading
from ctypes import *
from dataclasses import dataclass
from time import sleep
from six.moves import queue
from .constants import Status, FailureStatus, PayoutResponse, Actions, UnitType, Route

DEFAULT_CURRENCY = "RUB"

@dataclass
class Note:
    value: int
    currency: str
    def __init__(self, value, currency=DEFAULT_CURRENCY):
        self.value = int(value)
        self.currency = currency
    def __str__(self):
        return "%s %s" % (str(self.value), self.currency)
    def __int__(self):
        return self.value

@dataclass
class Channel:
    note: Note
    amount: int
    route: Route

@dataclass
class Last:
    status: Status
    note: Note | None

class Ssp6ChannelData(Structure):
    _fields_ = [("security", c_ubyte),
                ("value", c_uint),
                ("cc", c_char * 4)]

class Ssp6SetupRequestData(Structure):
    _fields_ = [("UnitType", c_ubyte),
                ("FirmwareVersion", c_char * 5),
                ("NumberOfChannels", c_uint),
                ("ChannelData", Ssp6ChannelData * 20),
                ("RealValueMultiplier", c_ulong),
                ("ProtocolVersion", c_ubyte)]

class SspPollEvent6(Structure):
    _fields_ = [("event", c_ubyte),
                ("data1", c_ulong),
                ("data2", c_ulong),
                ("cc", c_char * 4)]

class SspPollData6(Structure):
    _fields_ = [("events", SspPollEvent6 * 20),
                ("event_count", c_ubyte)]

class eSSP(object):
    """Encrypted Smiley Secure Protocol Class"""

    def __init__(self, com_port, ssp_address="0", route_to_storage=None, debug=False):
        self.debug = debug
        self.actions = queue.Queue()
        self.actions_args = {}
        self.response_data = {}
        self.events = []
        self.storage = {}
        self.busy = True
        self.stacked = 0
        self.last = Last(None, None)
        # There can't be 9999 notes in the storage
        self.response_data['getnoteamount_response'] = 9999

        self.sspC = self.essp.ssp_init(com_port.encode(), ssp_address.encode(), debug)
        self.poll = SspPollData6()
        setup_req = Ssp6SetupRequestData()

        # Check if the validator is present
        if self.essp.ssp6_sync(self.sspC) != Status.SSP_RESPONSE_OK:
            self.print_debug("NO VALIDATOR FOUND")
            self.close()
            raise Exception("No validator found")
        else:
            self.print_debug("Validator found")

        # Try to setup encryption
        if self.essp.ssp6_setup_encryption(self.sspC, c_ulonglong(0x123456701234567)) == Status.SSP_RESPONSE_OK:
            self.print_debug("Encryption setup")
        else:
            self.print_debug("Encryption failed")

        # Checking the version, make sure we are using ssp version 6
        if self.essp.ssp6_host_protocol(self.sspC, 0x06) != Status.SSP_RESPONSE_OK:
            self.print_debug(self.essp.ssp6_host_protocol(self.sspC, 0x06))
            self.print_debug("Host protocol failed")
            self.close()
            raise Exception("Host protocol failed")

        # Get some information about the validator
        if self.essp.ssp6_setup_request(self.sspC, byref(setup_req)) != Status.SSP_RESPONSE_OK:
            self.print_debug("Setup request failed")
            self.close()
            raise Exception("Setup request failed")

        try:
            self.unit = UnitType(setup_req.UnitType)
        except ValueError:
            self.unit = setup_req.UnitType
        self.print_debug("Unit type: %s" % str(self.unit))
        self.print_debug("Firmware: %s" % (setup_req.FirmwareVersion.decode('utf8')))

        self.print_debug("Storage: ")
        for i, channel in enumerate(setup_req.ChannelData):
            if channel.value:
                note = Note(channel.value, channel.cc.decode())
                DEFAULT_CURRENCY = note.currency
                if self.essp.ssp6_get_note_amount(self.sspC, channel.value * 100, channel.cc) == Status.SSP_RESPONSE_OK:
                    response_data = cast(self.essp.ssp_get_response_data(self.sspC), POINTER(c_ubyte))
                    amount = response_data[1]
                else:
                    amount = 0
                if self.essp.ssp6_get_routing(self.sspC, channel.value * 100, channel.cc) == Status.SSP_RESPONSE_OK:
                    response_data = cast(self.essp.ssp_get_response_data(self.sspC), POINTER(c_ubyte))
                    try:
                        route = Route(response_data[1])
                    except ValueError:
                        route = None
                else:
                    route = None
                self.storage[i + 1] = Channel(note, amount, route)
                self.print_debug("Channel %s: %s: %s, %s" % (str(i + 1), str(note), str(amount), str(route)))

        # Enable the validator
        if self.essp.ssp6_enable(self.sspC) != Status.SSP_RESPONSE_OK:
            self.print_debug("Enable failed")
            self.close()
            raise Exception("Enable failed")

        if self.unit == UnitType.SMART_HOPPER:
            for channel in enumerate(setup_req.ChannelData):
                self.essp.ssp6_set_coinmech_inhibits(self.sspC, channel.value, channel.cc, Status.ENABLED)
        else:
            if setup_req.UnitType in {UnitType.SMART_PAYOUT, UnitType.NOTE_FLOAT}:
                # Enable the payout unit
                if self.essp.ssp6_enable_payout(self.sspC, setup_req.UnitType) != Status.SSP_RESPONSE_OK:
                    self.print_debug("Payout enable failed")
                else:
                    self.print_debug("Payout enable")
                if route_to_storage:
                    for channel in self.storage.values():
                        if channel.note.value <= route_to_storage and channel.route != Route.PAYOUT:
                            if self.essp.ssp6_set_route(self.sspC, channel.note.value * 100, channel.note.currency.encode(), Route.PAYOUT.value) == Status.SSP_RESPONSE_OK:
                                self.print_debug("Route to storage %s" % (str(channel.note)))
                            else:
                                self.print_debug("ERROR: Route to storage failed")

            # Set the inhibits (enable all note acceptance)
            if self.essp.ssp6_set_inhibits(self.sspC, 0xFF, 0xFF) != Status.SSP_RESPONSE_OK:
                self.print_debug("Inhibits failed")
                self.close()
                raise Exception("Inhibits failed")
        
        # Set bezel color
        self.configure_bezel(0, 255, 0)

        system_loop_thread = threading.Thread(target=self.system_loop)
        system_loop_thread.daemon = True
        system_loop_thread.start()

    def get_note(self, channel):
        try:
            return self.storage[channel].note
        except KeyError:
            return channel

    def add_note_to_storage(self, note):
        for channel in self.storage.values():
            if channel.note == note:
                channel.amount += 1
                return

    def close(self):
        """Close the connection"""
        self.reject()
        self.essp.close_ssp_port()

    def reject(self):
        """Reject the bill if there is one"""
        if self.essp.ssp6_reject(self.sspC) != Status.SSP_RESPONSE_OK:
            self.print_debug("Error to reject bill OR nothing to reject")

    def do_actions(self):
        while not self.actions.empty() and not self.busy:
            current_action = self.actions.get()  # get and delete
            self.print_debug(current_action["action"])

            if current_action["action"] == Actions.ENABLE_VALIDATOR:
                self.enable_validator(now=True)

            elif current_action["action"] == Actions.UPDATE_PAYOUT:
                self.update_payout(now=True)

            elif current_action["action"] == Actions.ROUTE_TO_CASHBOX:
                if self.essp.ssp6_set_route(self.sspC, current_action["amount"], current_action["currency"]).encode() != Status.SSP_RESPONSE_OK:
                    self.print_debug("ERROR: Route to cashbox failed")

            elif current_action["action"] == Actions.ROUTE_TO_STORAGE:
                if self.essp.ssp6_set_route(self.sspC, current_action["amount"], current_action["currency"].encode(), Route.PAYOUT.value) != Status.SSP_RESPONSE_OK:
                    self.print_debug("ERROR: Route to storage failed")

            elif current_action["action"] == Actions.PAYOUT:
                if self.essp.ssp6_payout(self.sspC, current_action["amount"], current_action["currency"].encode(), Status.SSP6_OPTION_BYTE_DO.value) == Status.SSP_RESPONSE_OK:
                    if self.essp.ssp6_configure_bezel(self.sspC, 0, 0, 255, 0) != Status.SSP_RESPONSE_OK:
                        self.print_debug("ERROR: Can't configure bezel color")
                    self.busy = True
                else:
                    response_data = cast(self.essp.ssp_get_response_data(self.sspC), POINTER(c_ubyte))
                    if response_data[1] == PayoutResponse.SMART_PAYOUT_NOT_ENOUGH:
                        response_info = str(PayoutResponse.SMART_PAYOUT_NOT_ENOUGH)
                    elif response_data[1] == PayoutResponse.SMART_PAYOUT_EXACT_AMOUNT:
                        response_info = str(PayoutResponse.SMART_PAYOUT_EXACT_AMOUNT)
                    elif response_data[1] == PayoutResponse.SMART_PAYOUT_BUSY:
                        response_info = str(PayoutResponse.SMART_PAYOUT_BUSY)
                    elif response_data[1] == PayoutResponse.SMART_PAYOUT_DISABLED:
                        response_info = str(PayoutResponse.SMART_PAYOUT_DISABLED)
                    else:
                        response_info = str(response_data[1])
                    self.print_debug(f"ERROR: Payout failed, {response_info}")

            elif current_action["action"] == Actions.DISABLE_VALIDATOR:
                if self.essp.ssp6_disable(self.sspC) != Status.SSP_RESPONSE_OK:
                    self.print_debug("ERROR: Disable failed")

            elif current_action["action"] == Actions.DISABLE_PAYOUT:
                if self.essp.ssp6_disable_payout(self.sspC) != Status.SSP_RESPONSE_OK:
                    self.print_debug("ERROR: Disable payout failed")

            elif current_action["action"] == Actions.GET_NOTE_AMOUNT:
                if self.essp.ssp6_get_note_amount(self.sspC, current_action["amount"], current_action["currency"]) == Status.SSP_RESPONSE_OK:
                    response_data = cast(self.essp.ssp_get_response_data(self.sspC), POINTER(c_ubyte))
                    self.print_debug(response_data[1])
                    # The number of note
                    self.response_data['getnoteamount_response'] = response_data[1]
                else:
                    self.print_debug("ERROR: Can't read the note amount")
                    # There can't be 9999 notes
                    self.response_data['getnoteamount_response'] = 9999

            elif current_action["action"] == Actions.EMPTY_STORAGE:  # Empty the storage ( Send all to the cashbox )
                if self.essp.ssp6_empty(self.sspC) == Status.SSP_RESPONSE_OK:
                    if self.essp.ssp6_configure_bezel(self.sspC, 255, 255, 0, 0) != Status.SSP_RESPONSE_OK:
                        self.print_debug("ERROR: Can't configure bezel color")
                    self.busy = True
                    self.print_debug("Emptying, please wait...")
                else:
                    self.print_debug("ERROR: Can't empty the storage")

            elif current_action["action"] == Actions.CONFIGURE_BEZEL:
                if self.essp.ssp6_configure_bezel(self.sspC, current_action["red"], current_action["green"], current_action["blue"], current_action["volatile"]) != Status.SSP_RESPONSE_OK:
                    self.print_debug("ERROR: Can't configure bezel color")

            else:
                self.print_debug("Unknow action")

    def print_debug(self, text):
        if self.debug:
            print(text)

    def parse_poll(self):
        """Parse the poll, for getting events"""
        for events in self.poll.events[:self.poll.event_count]:
            try:
                event = Status(events.event)
                #self.print_debug(event)
            except ValueError:
                event = events.event
                self.print_debug('Unknown status: {}'.format(event))

            if event == Status.SSP_POLL_DISABLED:
                self.enable_validator(now=True)

            if event == Status.SSP_POLL_RESET:
                if self.essp.ssp6_host_protocol(self.sspC, 0x06) != Status.SSP_RESPONSE_OK:
                    raise Exception("Host protocol failed")
                    self.close()

            elif event == Status.SSP_POLL_READ:
                if events.data1 > 0:
                    note = self.get_note(events.data1)
                    self.last.status = event
                    self.last.note = note
                    self.print_debug("Note Read %s" % (note))
                    #self.events.append((note, event))

            elif event == Status.SSP_POLL_CREDIT:
                note = self.get_note(events.data1)
                self.last.status = event
                self.last.note = note
                self.print_debug("Credit %s" % (note))
                self.events.append((note, event))

            elif event == Status.SSP_POLL_STORED:
                if (self.last.status == Status.SSP_POLL_CREDIT):
                    self.add_note_to_storage(self.last.note)
                    self.print_debug("Stored in payout %s" % (self.last.note))
                    self.last = Last(None, None)

            elif event == Status.SSP_POLL_STACKED:
                if events.data1 > 0:
                    self.last.note = self.get_note(events.data1)
                self.stacked += self.last.note.value
                self.print_debug("Stacked in cashbox %s" % (self.last.note))
                #self.events.append((note, event))
                self.last = Last(None, None)

            elif event == Status.SSP_POLL_DISPENSING:
                if events.data1 > 0:
                    self.last.status = event
                    self.last.note = Note(events.data1 / 100)#, events.cc.decode())
                    self.print_debug("Dispensing %s" % (str(self.last.note)))
                    self.events.append((self.last.note, event))
                else:
                    self.print_debug("Dispensing")

            elif event == Status.SSP_POLL_DISPENSED:
                if events.data1 > 0:
                    self.last.note = Note(events.data1 / 100)#, events.cc.decode())
                self.print_debug("Dispensed %s" % (str(self.last.note)))
                self.events.append((self.last.note, event))
                self.last = Last(None, None)

            elif event == Status.SSP_POLL_CASH_BOX_REPLACED:
                self.stacked = 0
                self.print_debug("Cashbox replaced")
                self.events.append((None, event))

            elif event == Status.SSP_POLL_SMART_EMPTIED:
                storage_amount = 0
                for channel in self.storage.values():
                    storage_amount += channel.note.value * channel.amount
                    channel.amount = 0
                self.stacked += storage_amount
                emptied = Note(storage_amount)
                self.print_debug("Emptied to cashbox %s" % (str(emptied)))
                self.events.append((emptied, event))

            elif event == Status.SSP_POLL_INCOMPLETE_PAYOUT:
                self.print_debug(
                    "Incomplete payout %s of %s %s" %
                    (events.data1, events.data2, events.cc.decode()))

            elif event == Status.SSP_POLL_INCOMPLETE_FLOAT:
                self.print_debug(
                    "Incomplete float %s of %s %s" %
                    (events.data1, events.data2, events.cc.decode()))

            elif event == Status.SSP_POLL_FRAUD_ATTEMPT:
                note = self.get_note(events.data1)
                self.print_debug("Fraud Attempt %s" % (note))
                self.events.append((note, event))

            elif event == Status.SSP_POLL_CALIBRATION_FAIL:
                self.print_debug("Calibration fail: ")
                self.print_debug(FailureStatus(events.data1))
                if events.data1 == Status.COMMAND_RECAL:
                    self.print_debug("trying to run autocalibration")
                    self.essp.ssp6_run_calibration(self.sspC)
            
            else:
                self.events.append((None, event))

    def system_loop(self):  # Looping for getting the alive signal ( obligation in eSSP6 )
        while True:
            rsp_status = self.essp.ssp6_poll(self.sspC, byref(self.poll))
            if rsp_status != Status.SSP_RESPONSE_OK:  # If there's a problem, check what is it
                if rsp_status == Status.SSP_RESPONSE_TIMEOUT:  # Timeout
                    self.print_debug("SSP poll timeout")
                    self.close()
                    exit(0)
                else:
                    if rsp_status == Status.SSP_POLL_KEY_NOT_SET:
                        # The self has responded with key not set, so we should try to negotiate one
                        if self.essp.ssp6_setup_encryption(self.sspC, c_ulonglong( 0x123456701234567)) == Status.SSP_RESPONSE_OK:
                            self.print_debug("Encryption setup")
                        else:
                            self.print_debug("Encryption failed")
                    else:
                        # Not theses two, stop the program
                        raise Exception("SSP poll error {}".format(rsp_status))
                        exit(1)
            if self.poll.event_count > 0:
                if not self.busy:
                    self.busy = True
                    self.print_debug("Busy")
                self.parse_poll()
            elif self.busy:
                self.busy = False
                self.print_debug("Free")
            self.do_actions()
            sleep(0.5)

    def get_last_event(self):
        """Get the last event and delete it from the event list"""
        if len(self.events) > 0:
            event = self.events.pop(0)
            return event
        return None

    def enable_validator(self, now=False):
        # Send this command to enable a disabled device.
        # device: 'NV9USB', 'NV10USB', 'BV20', 'BV50', 'BV100', 'NV200', 'SMART Hopper', 'NV11'
        if not now:       
            queued_action = { "action": Actions.ENABLE_VALIDATOR }
            self.actions.put(queued_action)
            return
        
        setup_req = Ssp6SetupRequestData()
        if self.essp.ssp6_enable(self.sspC) != Status.SSP_RESPONSE_OK:
            self.print_debug("ERROR: Enable failed")
            return False
        
        # SMART Hopper requires different inhibit commands, so use setup
        # request to see if it is an SH
        if self.essp.ssp6_setup_request(self.sspC, byref(setup_req)) != Status.SSP_RESPONSE_OK:
            self.print_debug("Setup request failed")
            return False
        
        if setup_req.UnitType == UnitType.SMART_HOPPER:
            # SMART Hopper requires different inhibit commands
            for channel in setup_req.ChannelData:
                self.essp.ssp6_set_coinmech_inhibits(self.sspC, channel.value, channel.cc, Status.ENABLED.value)
        else:
            if self.essp.ssp6_set_inhibits(self.sspC, 0xFF, 0xFF) != Status.SSP_RESPONSE_OK:  # Magic numbers here too
                self.print_debug("Inhibits Failed")
                return False
        
        # Set bezel color
        self.configure_bezel(0, 255, 0)

    def update_payout(self, now=False):
        if self.unit not in {UnitType.SMART_PAYOUT, UnitType.NOTE_FLOAT}:
            # No payout device
            return False

        if not now:       
            queued_action = { "action": Actions.UPDATE_PAYOUT }
            self.actions.put(queued_action)
            return
        
        for channel in self.storage.values():
            if self.essp.ssp6_get_note_amount(self.sspC, channel.note.value * 100, channel.note.currency.encode()) == Status.SSP_RESPONSE_OK:
                response_data = cast(self.essp.ssp_get_response_data(self.sspC), POINTER(c_ubyte))
                channel.amount = response_data[1]
            if self.essp.ssp6_get_routing(self.sspC, channel.note.value * 100, channel.note.currency.encode()) == Status.SSP_RESPONSE_OK:
                response_data = cast(self.essp.ssp_get_response_data(self.sspC), POINTER(c_ubyte))
                try:
                    channel.route = Route(response_data[1])
                except ValueError:
                    channel.route = None

    def set_route_cashbox(self, amount, currency=DEFAULT_CURRENCY):
        # This command will configure the denomination to be either routed to the cashbox on detection or stored to be made available for later possible payout.
        # device: 'SMART Hopper', 'SMART Payout', 'NV11'
        queued_action = { "action": Actions.ROUTE_TO_CASHBOX, "amount": amount*100, "currency": currency }
        self.actions.put(queued_action)

    def set_route_storage(self, amount, currency=DEFAULT_CURRENCY):
        # This command will configure the denomination to be either routed to the cashbox on detection or stored to be made available for later possible payout.
        # device: 'SMART Hopper', 'SMART Payout', 'NV11'
        queued_action = { "action": Actions.ROUTE_TO_STORAGE, "amount": amount*100, "currency": currency }
        self.actions.put(queued_action)

    def payout(self, amount, currency=DEFAULT_CURRENCY):
        # A command to set the monetary value to be paid by the payout unit. Using protocol version 6, the host also sends a pre-test option byte (TEST_PAYOUT_AMOUT 0x19, PAYOUT_AMOUNT 0x58), which will determine if the command amount is tested or paid out. This is useful for multi-payout systems so that the ability to pay a split down amount can be tested before committing to actual payout.
        # device: 'SMART Hopper', 'SMART Payout'
        queued_action = { "action": Actions.PAYOUT, "amount": amount*100, "currency":currency }
        self.actions.put(queued_action)

    def get_note_amount(self, amount, currency=DEFAULT_CURRENCY):
        # This command returns the level of a denomination stored in a payout device as a 2 byte value. In protocol versions greater or equal to 6, the host adds a 3 byte ascii country code to give multi-currency functionality. Send the requested denomination to find its level. In this case a request to find the amount of 0.10c coins in protocol version 5.
        # device: 'SMART Hopper', 'SMART Payout'
        queued_action = { "action": Actions.GET_NOTE_AMOUNT, "amount": amount*100, "currency": currency }
        self.actions.put(queued_action)

    def reset(self):
        self.print_debug("Starting reset")
        self.essp.ssp6_reset(self.sspC)
        self.print_debug("Reset complete")

    def empty_storage(self):
        # Empties payout device of contents, maintaining a count of value emptied. The current total value emptied is given is response to a poll command. All coin counters will be set to 0 after running this command. Use Cashbox Payout Operation Data command to retrieve a breakdown of the denomination routed to the cashbox through this operation.
        # device: 'SMART Hopper', 'SMART Payout', 'NV11'
        queued_action = { "action": Actions.EMPTY_STORAGE }
        self.actions.put(queued_action)

    def disable_payout(self):
        # All accepted notes will be routed to the stacker and payout commands will not be accepted.
        # device: 'SMART Payout', 'NV11'
        queued_action = { "action": Actions.DISABLE_PAYOUT }
        self.actions.put(queued_action)

    def disable_validator(self):
        # The peripheral will switch to its disabled state, it will not execute any more commands or perform any actions until enabled, any poll commands will report disabled.
        # device: 'NV9USB', 'NV10USB', 'BV20', 'BV50', 'BV100', 'NV200', 'SMART Hopper', 'NV11'
        queued_action = { "action": Actions.DISABLE_VALIDATOR }
        self.actions.put(queued_action)

    def configure_bezel(self, red, green, blue, volatile = 0):
        # This command allows the host to configure a supported BNV bezel. If the bezel is not supported the command will return generic response COMMAND NOT KNOWN 0xF2.
        # device: 'NV200'
        queued_action = { "action": Actions.CONFIGURE_BEZEL, "red": red, "green": green, "blue": blue, "volatile": volatile }
        self.actions.put(queued_action)

    def __str__(self):
        cashbox_text = f"Cashbox: {self.stacked} {DEFAULT_CURRENCY}\n"
        storage_amount = 0
        storage_text = ""
        for channel in self.storage.values():
            storage_amount += channel.note.value * channel.amount
            if len(storage_text):
                storage_text += ", "
            storage_text += f"{str(channel.note)}: {channel.amount}"
        storage_text = f"Storage: {storage_amount} {DEFAULT_CURRENCY} ({storage_text})"
        return cashbox_text + storage_text
