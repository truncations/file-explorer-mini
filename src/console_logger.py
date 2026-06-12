import datetime
import configuration as configuration

class Logger():
    """
    Global logs list.

    Must be stored as:
        tuple: (status_code, msg, time_sent)
    """
    _logs = []

    class Message_Keys():
        status_code = 0
        msg = 1
        time_sent = 2

    status_codes = {
        0: "INFORMATION",
        1: "WARNING",
        2: "ERROR"
    }

    @staticmethod
    def send_message(msg: str = "", code: int = 0):
        """
        Sends a message that is then stored in the logs list. Message contains status code name, message content, and day/time of sent message.

        Args:
            msg: The message to be sent to the logs.
            code: 0 = INFORMATION, 1 = WARNING, 2 = ERROR

        Returns:
            None
        """
        if Logger.get_log_count()+1 > configuration.get_max_log_count():
            Logger.get_logs().pop()
        time_sent_msg = datetime.datetime.now()
        msg = (Logger.status_codes[code], msg, time_sent_msg.strftime("%H:%M:%S.%f-%Y:%m:%d"))
        Logger._logs.append(msg)

    @staticmethod
    def get_logs() -> list:
        return Logger._logs

    @staticmethod
    def print_logs():
        strformat = "===== LOGS =====\n\n"
        for log in Logger.get_logs():
            strformat += f"{log[Logger.Message_Keys.time_sent]} > {log[Logger.Message_Keys.status_code]} | {log[Logger.Message_Keys.msg]}\n"
        print(strformat)

    @staticmethod
    def get_log_count() -> int:
        return len(Logger.get_logs())

    @staticmethod
    def tick_function(function: function, alias: str, *args, **kwargs):
        """
        Test a function's runtime given as an alias for debugging purposes.
        The amount of time for the function to run will be noted in logs.

        Args:
            function: The function to be tested.
            alias: A custom name for the function for convenient debugging purposes.
            *args [optional]: Arguments for the function provided.
            **kwargs [optional]: Keyword arguments for the function provided.

        Returns:
            None
        """
        start_tick = datetime.datetime.now()
        Logger.send_message(f"Ticking Function: {alias}", 0)

        function(*args, **kwargs)

        finish_tick = datetime.datetime.now()
        Logger.send_message(f"Completed Function: {alias} in {(finish_tick-start_tick).total_seconds():.10f} seconds.", 0)

Logger.send_message("Beginning Application.", 0)