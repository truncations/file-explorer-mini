# using txt
# autoplay, max_zoom, zoom_scale, nav_bar_size
import os
_work_path: str = os.path.dirname(__file__)[:-len("src")]
_data_path: str = os.path.join(_work_path, "data.txt")

class Data:
    data: list | None = None

    @classmethod
    def save_data(cls, _data: list):
        cls.data = _data

        with open(os.path.join(_data_path), "w") as file:
            parsed_str = ",".join([str(value) for value in cls.data if type(value) is not list])
            file.write(parsed_str+"\n")
            file.writelines("\n".join(cls.data[len(cls.data)-1]))

    @classmethod
    def save_default_data(cls):
        print("New Data File")
        cls.save_data(["YES", 1000, 25, 125, 50, []])

    @classmethod
    def load_data(cls):
        if not os.path.exists(_data_path):
            cls.save_default_data()
            return
    
        with open(os.path.join(_data_path), "r") as file:
            _data = file.readline().strip("\n").split(",")
            _parsed_data = [None]*5
            _parsed_data.append([])
            for index, value in enumerate(_data):
                if type(value) is list:
                    _parsed_data[index] = value
                elif value.isnumeric():
                    _parsed_data[index] = int(value)
                else:
                    _parsed_data[index] = value
            _parsed_data[len(_parsed_data)-1] = [line.strip("\n") for line in file.readlines()]
            cls.data = _parsed_data

    @classmethod
    def get_data(cls) -> list:
        return cls.data