"""
Specific exceptions for the lamp operation.
"""

# Network error codes
UNSPECIFIED_FAULT = 1
LAN_FAULT = 2
INTERNET_FAULT = 3
SERVER_FAULT = 4

class IllegalSetupException(Exception):
    """
    Used to communicate that an error has occured due to some error in the config.txt file.
    """
    
    def __init__(self, message: str = 'Illegal setup detected'):
        """
        Incorrect configuration parameters supplied.

        Args:
            message (str, optional): Exception message. Defaults to 'Illegal setup detected'.
        """
        
        self.message = message
        super().__init__(self.message)

class NetworkException(Exception):
    """
    Used to communicate that something has failed in network communications.
    """
    
    def __init__(self, message: str = 'A network error has occured', errorcode: int = UNSPECIFIED_FAULT):
        """
        Network communication fault.

        Args:
            message (str, optional): Exception message. Defaults to 'A network error has occured'.
            errorcode (int, optional): The type of network error. Defaults to UNSPECIFIED_FAULT.
        """
        
        self.message = message
        self.errorcode = errorcode
        super().__init__(self.message)