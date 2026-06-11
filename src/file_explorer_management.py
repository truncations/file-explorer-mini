import src.vars_util as vars_util

# RETURNS LIST OF vars_util.Directory_Point objects.
def get_files_in_cur_directory() -> list:
    cur_dir = vars_util.Directory_Manager.current_directory
    list_of_files = vars_util.Directory_Manager.get_list_of_files(cur_dir)
    return list_of_files
    