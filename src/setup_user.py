"""
Module containing all user functionality
"""


def user_input(ask: str):
    """
    Function to get user input for the backup script
    """
    var = ""
    while not var:
        var = input(f"Please write in a {ask}")
        print(f"would you like to use: {var}")
        decision = input("Yes/No")
        if decision.lower() == "no":
            var = ""


def setup_user():
    """
    Function to set up user for the backup script
    """
    username = user_input("username")
    local_directory = user_input("local_directory")
    remote_directory = user_input("remote_directory")
