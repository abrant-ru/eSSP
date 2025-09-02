from aenum import Enum

class Status(Enum):
    _init_ = 'value', 'debug_message'

    SSP_RESPONSE_ERROR = 0xFF, "Error"
    SSP_RESPONSE_TIMEOUT = 0xFF, "Timeout"
    SSP_RESPONSE_OK = 0xF0, "Ok"
    ENABLED = 0x01, "Enabled"
    DISABLED = 0x00, "Disabled"
    SSP_POLL_CALIBRATION_FAIL = 0x83, "Calibration failed"
    SSP_POLL_JAM_RECOVERY = 0xB0, "Jam recovery"        # The SMART Payout unit is in the process of recovering from a detected jam. This process will typically move five notes to the cash box; this is done to minimise the possibility the unit will go out of service
    SSP_POLL_SMART_EMPTYING = 0xB3, "Smart emptying"    # The device is in the process of carrying out its Smart Empty command from the host. The value emptied at the poll point is given in the event data.
    SSP_POLL_SMART_EMPTIED = 0xB4, "Smart emptied"      # The device has completed its Smart Empty command. The total amount emptied is given in the event data.
    SSP_POLL_EMPTYING = 0xC2, "Emptying"                # The device is in the process of emptying its content to the system cashbox in response to an Empty command.
    SSP_POLL_EMPTY = 0xC3, "Empty"                      # The device has completed its Empty process in response to an Empty command from the host.
    SSP_POLL_STACKING = 0xCC, "Note stacking"           # The note is being moved from the escrow position to the host exit section of the device.
    SSP_POLL_BARCODE_ACK = 0xD1, "Barcode ACK"          # The bar code ticket has been passed to a safe point in the device stacker.
    SSP_POLL_DISPENSED = 0xD2, "Dispensed"              # The device has completed its pay-out request. The final value paid is given in the event data.
    SSP_POLL_COINS_LOW = 0xD3, "Coins low"
    SSP_POLL_COINS_EMPTY = 0xD4, "Coins empty"
    SSP_POLL_JAMMED = 0xD5, "Jammed"                    # The device has detected that coins are jammed in its mechanism and cannot be removed other than by manual intervention. The value paid at the jam point is given in the event data.
    SSP_POLL_HALTED = 0xD6, "Halted"                    # This event is given when the host has requested a halt to the device. The value paid at the point of halting is given in the event data.
    SSP_POLL_FLOATING = 0xD7, "Floating"                # The device is in the process of executing a float command and the value paid to the cashbox at the poll time is given in the event data.
    SSP_POLL_FLOATED = 0xD8, "Floated"                  # The device has completed its float command and the final value floated to the cashbox is given in the event data.
    SSP_POLL_TIMEOUT = 0xD9, "Timeout"                  # The device has been unable to complete a request. The value paid up until the time-out point is given in the event data.
    SSP_POLL_DISPENSING = 0xDA, "Dispensing"            # The device is in the process of paying out a requested value. The value paid at the poll is given in the vent data.
    SSP_POLL_STORED = 0xDB, "Note stored in payout"     # The note has been passed into the note store of the payout unit.
    SSP_POLL_INCOMPLETE_PAYOUT = 0xDC, "Incomplete payout" # The device has detected a discrepancy on power-up that the last payout request was interrupted (possibly due to a power failure). The amounts of the value paid and requested are given in the event data.
    SSP_POLL_INCOMPLETE_FLOAT = 0xDD, "Incomplete float" # The device has detected a discrepancy on power-up that the last float request was interrupted (possibly due to a power failure). The amounts of the value paid and requested are given in the event data.
    SSP_POLL_CASHBOX_PAID = 0xDE, "Cashbox paid"        # This is given at the end of a payout cycle. It shows the value of stored coins that were routed to the cashbox that were paid into the cashbox during the payout cycle.
    SSP_POLL_COIN_CREDIT = 0xDF, "Coin credit"          # A coin has been detected as added to the system via the attached coin mechanism. The value of the coin detected is given in the event data.
    SSP_POLL_NOTE_PATH_OPEN = 0xE0, "Note path open"    # The device has detected that its note transport path has been opened.
    SSP_POLL_CLEARED_FROM_FRONT = 0xE1, "Cleared from front" # At power-up, a note was detected as being rejected out of the front of the device. The channel value, if known is given in the data byte.
    SSP_POLL_CLEARED_INTO_CASHBOX = 0xE2, "Cleared into cashbox" # At power up, a note was detected as being moved into the stacker unit or host exit of the device. The channel number of the note is given in the data byte if known.
    SSP_POLL_CASH_BOX_REMOVED = 0xE3, "Cashbox removed" # A device with a detectable cashbox has detected that it has been removed.
    SSP_POLL_CASH_BOX_REPLACED = 0xE4, "Cashbox replaced" # A device with a detectable cashbox has detected that it has been replaced.
    SSP_POLL_BARCODE_VALIDATE = 0xE5, "Barcode ticket validated" # A validated barcode ticket has been scanned and is available at the escrow point of the device.
    SSP_POLL_FRAUD_ATTEMPT = 0xE6, "Fraud attempt"      # The device has detected an attempt to tamper with the normal validation/stacking/payout process. (next byte is channel)
    SSP_POLL_STACKER_FULL = 0xE7, "Stacker full"        # The banknote stacker unit attached to this device has been detected as at its full limit
    SSP_POLL_DISABLED = 0xE8, "Disabled"                # The device is not active and unavailable for normal validation functions.
    SSP_POLL_UNSAFE_JAM = 0xE9, "Unsafe note jam"       # The note is stuck in a position where the user could possibly remove it from the front of the device.
    SSP_POLL_SAFE_JAM = 0xEA, "Safe note jam"           # The note is stuck in a position not retrievable from the front of the device (user side).
    SSP_POLL_STACKED = 0xEB, "Note stacked"             # The note has exited the device on the host side or has been placed within its note stacker.
    SSP_POLL_REJECTED = 0xEC, "Note rejected"           # The note has been rejected from the validator and is available for the user to retrieve.
    SSP_POLL_REJECTING = 0xED, "Note rejecting"         # The note is in the process of being rejected from the validator.
    SSP_POLL_CREDIT = 0xEE, "Credit note"               # A note has passed through the device, past the point of possible recovery and the host can safely issue its credit amount. The byte value is the channel number of the note to credit. (next byte is channel)
    SSP_POLL_READ = 0xEF, "Read note"                   # A note is in the process of being scanned by the device (byte value 0) or a valid note has been scanned and is in escrow (byte value gives the channel number).
    SSP_POLL_RESET = 0xF1, "Reset"                      # The device has undergone a power reset.
    SSP_POLL_KEY_NOT_SET = 0xFA, "Key not set"          # The slave is in encrypted communication mode but the encryption keys have not been negotiated.
    SSP6_OPTION_BYTE_DO = 0x58, "Option Byte DO"
    NO_EVENT = 0xF9, "No event"

    def __int__(self):
        return self.value

    def __str__(self):
        return self.debug_message

    def __eq__(self, other):
        return self.value == other
    
    def __ne__(self, other):
        return self.value != other

class PayoutResponse(Enum):
    _init_ = 'value', 'debug_message'

    SMART_PAYOUT_NOT_ENOUGH = 0x01, "Not enough value in smart payout"
    SMART_PAYOUT_EXACT_AMOUNT = 0x02, "Can't pay exact amount"
    SMART_PAYOUT_BUSY = 0x03, "Smart payout is busy"
    SMART_PAYOUT_DISABLED = 0x04, "Smart payout is disabled"

    def __int__(self):
        return self.value

    def __str__(self):
        return self.debug_message

    def __eq__(self, other):
        return self.value == other
    
    def __ne__(self, other):
        return self.value != other

class FailureStatus(Enum):
    _init_ = 'value', 'debug_message'

    NO_FAILUE = 0x00, "No Failure"
    SENSOR_FLAP = 0x01, "Optical Sensor Flap"
    SENSOR_EXIT = 0x02, "Optical Sensor Exit"
    SENSOR_COIL1 = 0x03, "Coil sensor 1"
    SENSOR_COIL2 = 0x04, "Coil sensor 2"
    NOT_INITIALISED = 0x05, "Unit not initialized"
    CHECKSUM_ERROR = 0x06, "Data checksum error"
    COMMAND_RECAL = 0x07, "Recalibration by command required"

    def __int__(self):
        return self.value

    def __str__(self):
        return self.debug_message

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

class Actions(Enum):
    _init_ = 'value', 'debug_message'

    ENABLE_VALIDATOR = 0, "Enable validator"
    ROUTE_TO_CASHBOX = 1, "Route to cashbox"
    ROUTE_TO_STORAGE = 2, "Route to storage"
    PAYOUT = 3, "Payout"
    PAYOUT_NEXT_NOTE_NV11 = 4, "Payout next note"
    STACK_NEXT_NOTE_NV11 = 5, "Stack next note"
    DISABLE_VALIDATOR = 6, "Disable validator"
    DISABLE_PAYOUT = 7, "Disable payout"
    GET_NOTE_AMOUNT = 8, "Get note amount"
    EMPTY_STORAGE = 9, "Empty storage & cleaning indexes"
    CONFIGURE_BEZEL = 10, "Configure bezel color"
    UPDATE_PAYOUT = 11, "Update payout status"

    def __int__(self):
        return self.value

    def __str__(self):
        return self.debug_message

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

class UnitType(Enum):
    _init_ = 'value', 'debug_message'

    BANKNOTE_VALIDATOR = 0, 'Banknote validator'
    SMART_HOPPER = 3, 'Smart Hopper'
    SMART_PAYOUT = 6, 'SMART Payout'
    NOTE_FLOAT = 7, 'Note Float'
    ADDON_PRINTER = 8, 'Addon Printer'
    STAND_ALONE_PRINTER = 11, 'Stand Alone Printer'
    TEBS = 13, 'TEBS'
    TEBS_WITH_PAYOUT = 14, 'TEBS with SMART Payout'
    TEBS_WIDTH_TICKET = 15, 'TEBS with SMART Ticket'

    def __int__(self):
        return self.value

    def __str__(self):
        return self.debug_message

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other
    
    def __hash__(self):
        return self.value

class Route(Enum):
    _init_ = 'value', 'debug_message'

    PAYOUT = 0, 'Payout'
    CASHBOX = 1, 'Cashbox'

    def __int__(self):
        return self.value

    def __str__(self):
        return self.debug_message

if __name__ == "__main__":
    print(FailureStatus.SENSOR_FLAP == 1)
    print(FailureStatus(1))
