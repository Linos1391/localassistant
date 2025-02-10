"""Utils file."""

import pathlib
import json
import os
import shutil
import logging

from transformers import BitsAndBytesConfig
import warnings

###### - Add more model:
# 1.n.n
# - Search google https://github.com/Nv7-GitHub/googlesearch
# 2.n.n
# - TEXT_TO_SPEECH (Voice from AI)
# - SPEECH_TO_TEXT (Voice chat)
# - AUDIO_CLASSIFICATION (Multiple user voice chat
#      + https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb) I will cook.

class LocalAssistantException(Exception):
    """For common errors in LocalAssistant"""

class UtilsExtension:
    """Main utils extension of LocalAssistant"""
    def __init__(self):
        self.model_task: dict = {
            1: 'Text_Generation',
            2: 'Sentence_Transformer',
            3: 'Cross_Encoder',
        }
        self.reverse_model_task: dict = {k: v for v, k in self.model_task.items()}

        # path and stuffs
        self.project_path: str = pathlib.Path(__file__).parent
        self.env_path: pathlib.Path = self.project_path

        timeout: int = 100
        while self.env_path.name != '.venv': # goes back until reach .venv
            if not timeout:
                warnings.warn(f"Cannot detect '.venv', set main path to {self.project_path}. \
                    Remember it is recommended to use the installer. ")
                self.env_path = self.project_path
            self.env_path = self.env_path.parent
            timeout -= 1

        self.model_path: str = self.env_path.parent / 'models'
        self.user_path: str = self.env_path.parent / 'users'
        self.docs_path: str = self.env_path.parent / 'documents'

    @staticmethod
    def read_json_file(path: str):
        """Read a json file.

        Args:
            path (str): file's path.

        Returns:
            Any: file's data.
        """
        with open(path, mode="r", encoding="utf-8") as read_file:
            data = json.load(read_file)
            read_file.close()
        return data

    @staticmethod
    def write_json_file(path: str, data: dict) -> None:
        """Write a json file.

        Args:
            path (str): file's path.
            data (dict): file's data.
        """
        with open(path, mode="w", encoding="utf-8") as write_file:
            json.dump(data, write_file, indent=4)
            write_file.close()

    # it happens that i'm too smart.
    def print_dict(self, data: dict, level: int=0):
        """Used to print `dict` type."""
        for key, value in data.items():
            if isinstance(value, str):
                print(level*'   ' + f"'{key}': '{value}',")
            else: # value is dict
                print(level*'   ' + "%r: {" % (key)) # use %r as '{' is written
                self.print_dict(value, level+1)
                print(level*'   ' + "},")

    # remove all
    def self_destruction(self, delete_all: bool = False):
        """Everything all needs self-destruction."""
        option: str = input("Are you sure to remove LocalAssistant. \
There will be no turning back. Continue? [y/(n)]: ")
        if option.lower() != 'y':
            print('Self-destruction denied.')
            return
        print('Self-destruction...')

        # Locas, kys.

        if delete_all:
            self.env_path = self.env_path.parent
        shutil.rmtree(self.env_path)

    def load_chat_history(self, user: str) -> tuple[list, str]:
        """Load chat history!

        Args:
            user (str): user's name.
        
        Returns:
            tuple[list, str]: (list of history, history's name).
        """
        while True:
            scanned: bool = False
            history_list: list = []

            for _, _, files in os.walk(os.path.join(self.user_path, user, 'history')):
                if scanned:
                    break
                scanned = True

                if files == []:
                    print("\nThere is no history yet, please create one.")
                else:
                    print("\nChoose from:")
                for history in files:
                    if history.endswith('.json'):
                        print(f'    - {history.removesuffix('.json')}')
                        history_list.append(history.removesuffix('.json'))
            print("""
Type 'create [name (Required, 1 WORD ONLY)] [system_prompt (Optional)]' to create new history.
Type 'delete [name (Required, 1 WORD ONLY)]' to delete history.
Type 'exit' to exit.\n""")
            command: str = input('>> ')

            if command == '':
                logging.error('There is no input.')
                continue

            if command.lower() in ('exit', 'exit()'):
                break

            if command.split()[0].lower() == 'create':
                try:
                    command_split = command.split()
                    chat_name = command_split[1]
                    system_prompt = ' '.join(command_split[2:])
                except (ValueError, IndexError):
                    try:
                        chat_name = command.split()[1]
                    except IndexError:
                        logging.error('Missing NAME.')
                        continue

                if user == 'default':
                    system_prompt = "You are an Assistant named LocalAssistant (Locas). \
Give the user the best supports as you can."
                else:
                    system_prompt = f"You are an Assistant named LocalAssistant (Locas) \
who serves the user called {user}. Give {user} the best supports as you can."

                if chat_name in history_list: # throw error if create same name.
                    logging.error("ERROR: Name %s is used.", chat_name)
                    continue

                return ([{"role": "system", "content": system_prompt}], chat_name)

            if command.split()[0].lower() == 'delete':
                try:
                    chat_name = command.split()[1]
                except IndexError:
                    logging.error('Missing NAME.')
                    continue

                if chat_name not in history_list: # throw error if create same name.
                    logging.error('Name %s is not existed.', chat_name)
                    continue

                os.remove(os.path.join(self.user_path,user,'history',f'{chat_name}.json'))
                continue

            if command not in history_list:
                logging.error('No history named %s', command)
                continue

            temp_path: str = os.path.join\
                (self.user_path, user, 'history', f'{command}.json')
            return ([v for v in self.read_json_file(temp_path)], command.split()[0])
        return ([], '')

class ConfigManager:
    """Config of LocalAssistant"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.utils_ext = UtilsExtension()
        self.data: dict = {}
        self.path: str = os.path.join(self.utils_ext.project_path, 'locas_config.json')

    def upload_config_file(self) -> None:
        """Dump data to `locas_config.json` file."""
        self.utils_ext.write_json_file(self.path, self.data)
        logging.debug("Uploaded current data to config.json file.")

    def get_config_file(self) -> None:
        """"Read data from `locas_config.json` file."""
        logging.debug('Finding locas_config.json file.')
        try:
            # Read the data
            self.data = self.utils_ext.read_json_file(self.path)
            logging.debug('Found locas_config.json file.')

        except FileNotFoundError:
            logging.debug('Cannot find locas_config.json file. Create new one.')

            self.data = {
                "hf_token": "", # Hugging Face token.
                "load_in_bits": "8", # 'quantization' method. (So the device won't blow up)
                "top_k_memory": "25", # num of memory that retrieve.
                "models": { # the model that being use for chatting.
                    "Text_Generation": "",
                    "Sentence_Transformer": "",
                    "Cross_Encoder": "",
                },
                "documents": {
                    "top_k": "10",
                    "allow_score": "0.6"
                },
                "users": "default",
            }

            # dump data to file.
            self.utils_ext.write_json_file(self.path, self.data)
        logging.debug('Got data from config file.')

    def print_config_data(self) -> None:
        """Print out current config data (not from file)."""
        self.utils_ext.print_dict(self.data)

    def check_exist_user_physically(self, target: str) -> bool:
        """Check user in folder.

        Args:
            target (str): user's name.

        Returns:
            bool: if user already existed.
        """
        scanned: bool = False
        for _, folders, _ in os.walk(os.path.join(self.utils_ext.user_path, target)):
            if scanned:
                break
            scanned = True

            if 'history' in folders and 'memory' in folders:
                return True
            return False

    def check_for_exist_user(self, user: str):
        """Check user in but in current data.

        Args:
            user (str): user's name.
        """
        if user == 'default': # user did not add 'user'.
            try:
                os.makedirs(os.path.join(self.utils_ext.user_path, 'default', 'history'))
            except FileExistsError:
                pass

            try:
                os.mkdir(os.path.join(self.utils_ext.user_path, 'default', 'memory'))
            except FileExistsError:
                pass

            self.data.update({'users': 'default',})
        else: # user add new user.
            self.data.update({'users': user})

            if not self.check_exist_user_physically(user):
                # update on physical directory
                try:
                    os.makedirs(os.path.join(self.utils_ext.user_path, user, 'history'))
                except FileExistsError:
                    pass
                os.mkdir(os.path.join(self.utils_ext.user_path, user, 'memory'))
            logging.debug("Created user '%s'.", user)
        self.upload_config_file()

    # check exist model for each task
    def check_for_exist_model(self, task: int) -> None:
        """Check for exist model."""
        if not 0 < task <= len(self.utils_ext.model_task):
            logging.error("Wrong task. Got '%s' (%d)", self.utils_ext.model_task[task], task)
            raise LocalAssistantException\
                (f"Wrong task. Got '{self.utils_ext.model_task[task]}' ({task})")

        task: str = self.utils_ext.model_task[task]

        if self.data['models'][task] != '':
            for root, folders, _ in os.walk(os.path.join(self.utils_ext.model_path, task)):
                if root != os.path.join(self.utils_ext.model_path, task):
                    break

                if self.data['models'][task] in folders:
                    return # nothing to fix.

        scanned: bool = False
        for _, folders, _ in os.walk(os.path.join(self.utils_ext.model_path, task)):
            if scanned:
                break

            scanned = True
            self.data['models'][task] = folders[0] # if no model, meaning folders == [] -> ignored.

        if not scanned: # the above line has skipped
            logging.critical("There is no models for %s. \
Please type 'locas download -h' and download one.", task)
            raise LocalAssistantException(f"There is no models for {task}. \
Please type 'locas download -h' and download one.")

        self.upload_config_file()
        logging.info('Apply %s as model for %s.',self.data['models'][task], task)

    def load_quantization(self) -> dict:
        """
        Load desire quantization bits.
        
        Returns:
            dict: kwarg for models' `from_pretrain`.
        """
        kwarg = dict(local_files_only=True, use_safetensors=True, device_map="auto",)

        used_bit = self.data["load_in_bits"]
        match used_bit:
            case '8':
                kwarg.update({'quantization_config': BitsAndBytesConfig(load_in_8bit=True)})
            case '4':
                kwarg.update({'quantization_config': BitsAndBytesConfig(load_in_4bit=True)})
            case 'None':
                pass
            case _:
                logging.error('Invalid bits! We found: %s.', used_bit)
                raise LocalAssistantException(f"Invalid bits! We found: {used_bit}.")
        return kwarg
