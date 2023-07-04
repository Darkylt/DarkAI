import yaml
import os
import multiprocessing
from datetime import datetime

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

CONFIG_FILENAME = "config.yml"
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)

try:
    with open(config_path) as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    raise Exception("Configuration file not found. Please make sure the config.yml file is in the Main Folder.")
except yaml.YAMLError:
    raise Exception("Error parsing the configuration file. Invalid YAML format. Please make sure the config.yml is formatted correctly.")

class InvalidConfigError(Exception):
    # Error Handling for Invalid Config Errors can be implemented here.
    pass

class SDConfig:
    """
    This class contains all the variables for the Stabel Diffusion Model.
    """
    max_prompt_length = config["Max Prompt Length"]
    default_width = config["Default Width"]
    default_heigth = config["Default Height"]
    default_negative_prompt = config["Default Negative Prompt"]
    default_steps = config["Default Steps"]
    darkart_channel = config["Darkart Channel"]

class LLMConfig:

    """
    This class contains all the variables for the Large Language Model.
    """

    with open("chathistory+/chathistory.txt", "r", encoding="utf-8") as chat_history_file:
        chat_history = chat_history_file.read()
    with open("chathistory+\dm_chathistory.txt", "r", encoding="utf-8") as dmchat_history_file:
        dm_chat_history = dmchat_history_file.read()
    ai_name = config["AI Name"]
    default_chat_history = f"""Darkyl: Hello.\n{ai_name}:Hello. What questions can I answer for you?\n"""
    server_name = config["Server Name"]
    chat_memory_length = config["Chat Memory Length"]
    model_path = config["Model Path"]
    deterministic = config["Deterministic"]
    model_seed = config["Model Seed"] if deterministic else 0  # 0 means a random seed gets chosen for each generation.
    num_threads = config["Number of Threads"]
    MAX_TOKENS = 48  # Max tokens that the LLM will generate.
    prompt = config["Prompt"].replace("[AI-NAME]", ai_name).replace("[SERVER-NAME]", server_name).replace("[CHAT-MEM-LEN]", f"{chat_memory_length}").replace("[TIME]", timestamp)

class BotConfig:
    """
    This class contains all the variables for the Bot.
    """
    url = "http://127.0.0.1:7860"
    token = config["Bot Token"]
    guild = config["Guild ID"]
    admin_role = config["Admin Role"]
    darkart_channel = config["Darkart Channel"]
    help_message = config["Help Message"].replace("[AI-NAME]", LLMConfig.ai_name)
    dev_mode = config["dev mode"]

def validate_config():
    """
    A function that checks if the provided values in the config.yml
    are valid and can be used without error.
    Raises an Error if the config data is Invalid.
    
    Returns:
        True if the config values are valid.
    """

    required_keys = ["Deterministic", "Number of Threads", "Model Seed", "Guild ID", "Bot Token", "AI Name", "Prompt", "Chat Memory Length", "Server Name", "Admin Role", "Darkart Channel", "Max Prompt Length", "Default Width", "Default Height", "Default Negative Prompt", "Default Steps", "Darkart Channel", "Help Message", "dev mode", "Model Path"]
    type_validations = {
        "Deterministic": bool,
        "Number of Threads": int,
        "Model Seed": int,
        "Guild ID": int,
        "Bot Token": str,
        "AI Name": str,
        "Prompt": str,
        "Chat Memory Length": int,
        "Server Name": str,
        "Admin Role": int,
        "Darkart Channel": int,
        "Max Prompt Length": int,
        "Default Width": int,
        "Default Height": int,
        "Default Negative Prompt": str,
        "Default Steps": int,
        "Darkart Channel": int,
        "Help Message": str,
        "dev mode": bool,
        "Model Path": str
    }

    for key in required_keys:
        if key not in config:
            raise InvalidConfigError(f"Missing key in config.yml: {key}")

        if not isinstance(config[key], type_validations[key]):
            raise InvalidConfigError(f"Invalid value for '{key}'. Must be of type {type_validations[key].__name__}")
    
    if not os.path.exists(LLMConfig.model_path):
        raise InvalidConfigError(f"Specified Models could not be found in Models Folder.")
    
    if config["Number of Threads"] is not None:  # Proceeding even if it's None because this is also a valid value
        if not isinstance(config["Number of Threads"], int) or config["Number of Threads"] <= 0:
            raise InvalidConfigError("Invalid value for 'number of threads'. Must be a positive integer.")
        
        if config["Number of Threads"] > multiprocessing.cpu_count():
            raise InvalidConfigError(f"Number of threads provided in the config exceeds available system threads. Please provide a value below {multiprocessing.cpu_count()} or None")
        
    if config["Deterministic"]:
        if not isinstance(config["Model Seed"], int) or config["Model Seed"] <= 0:
            raise InvalidConfigError("Invalid value for 'model seed'. Must be a positive integer.")
        if not len(str(config["Model Seed"])) <= 10:
            raise InvalidConfigError("Invalid value for 'model seed'. Must be 10 digits long or shorter.")
        
    if LLMConfig.MAX_TOKENS < 48:
        raise ValueError(f"Invalid value for 'MAX_TOKENS'. Must be at least 48 and {LLMConfig.MAX_TOKENS} was provided")
    
    return True
