import datetime
import vars_util as vars_util

class Message_Keys():
    status_code = 0
    msg = 1
    time_sent = 2

class Logger():
    _logs = []

    # status codes
    status_codes = {
        0: "INFORMATION",
        1: "WARNING",
        2: "ERROR",
    }

    @staticmethod
    def send_message(msg="", code=0):
        if Logger.get_log_count()+1 > vars_util.max_log_count:
            Logger.get_logs().pop()
        time_sent_msg = datetime.datetime.now()
        msg = (Logger.status_codes[code], msg, time_sent_msg.strftime("%H:%M:%S.%f-%Y:%m:%d"))
        Logger._logs.append(msg)

    @staticmethod
    def get_logs():
        return Logger._logs

    @staticmethod
    def print_logs():
        strformat = "===== LOGS =====\n\n"
        for log in Logger.get_logs():
            strformat += f"{log[Message_Keys.time_sent]} > {log[Message_Keys.status_code]} | {log[Message_Keys.msg]}\n"
        print(strformat)

    @staticmethod
    def get_log_count():
        return len(Logger.get_logs())

    @staticmethod
    def tick_function(function, alias, *args, **kwargs):
        start_tick = datetime.datetime.now()
        Logger.send_message(f"Ticking Function: {alias}", 0)

        function(*args, **kwargs)

        finish_tick = datetime.datetime.now()
        Logger.send_message(f"Completed Function: {alias} in {(finish_tick-start_tick).total_seconds():.10f} seconds.", 0)

Logger.send_message("Beginning Application.", 0)