import os
import configparser

def get_config_path():
    # config.iniの保存場所
    app_dir = os.path.join(os.path.expanduser('~'), '.metadata_manager')
    
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    
    return os.path.join(app_dir, 'config.ini')

CONFIG_FILE = get_config_path()

def create_default_config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'csv_path': '',
        'caption_position': 'BOTTOM',
        'replace_caption': 'False',
        'csv_title_prefix': '',
        'clone_save_path': os.path.join(os.path.expanduser('~'), 'Desktop'),
        'analysis_model': 'CLIP',
        'clip_categories': '',
        'word_count': '5',
        'is_show_result_graph': 'True',
        'ui_font_name': '',
        'ui_font_size': 12,
        'text_font_name': '',
        'text_font_size': 14
    }
    
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def get_config():
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config