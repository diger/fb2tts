import os
import re
import json
from vosk_tts import Model, Synth
from ruaccent import RUAccent
from PIL import Image, ImageDraw, ImageFont

device = 'CPU'
try:
    import torch
    if torch.cuda.is_available():
        device = 'CUDA'
except ModuleNotFoundError as err:
    print(err)

print(f'Run with {device}')

accentizer = RUAccent()

now_dir = os.getcwd()
data_path = os.path.join(now_dir, "data")
ab_name = ''

if not os.path.exists(data_path):
    os.makedirs(data_path)

with open('dict/word_dict.json', 'r') as file:
    word_dict = json.load(file)

with open('dict/num_dict.json', 'r') as fl:
    num_dict = json.load(fl)

args=''

def load_vosk_model():
    local_folder = "model"
    vosk_path = 'model/vosk-model-tts-ru-0.10-multi'
    os.makedirs(local_folder, exist_ok=True)
    if not os.path.exists(f'{now_dir}/{vosk_path}'):
        print('Download vosk-model 0.10')
        model_url = "https://alphacephei.com/vosk/models/vosk-model-tts-ru-0.10-multi.zip"
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        zip_content = BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_ref:
            zip_ref.extractall(local_folder)
    model = Model(model_path='model/vosk-model-tts-ru-0.10-multi', model_name="vosk-model-tts-ru-0.9-multi")
    return Synth(model)

def set_args(s_args):
    global args
    args = s_args
    return args

def get_args():
    return args

def convert(seconds):
    min, sec = divmod(seconds, 60)
    min = f'{int(min)} m. ' if min else None
    sec = f'{int(sec)} s.'

    return min + sec

def set_ab_name(d_path):
    global ab_name
    ab_name = d_path
    return ab_name

def get_ab_name():
    return ab_name

def get_data_list(d_path=data_path):
    return [
        dirpath
        for dirpath in os.listdir(d_path)
    ]

def convert_to_jpg(image,dest_image):
    img = Image.fromarray(image)
    img.save(dest_image)
    return img

def load_image(ab_name):
    d_path = os.path.join(now_dir, "data", ab_name)
    destination_path = os.path.join(d_path, 'cover.jpg')
    if not os.path.exists(destination_path):
        destination_path = os.path.join(now_dir, 'libs', "cover.jpg")
    img = Image.open(destination_path)
    return img

def add_text_cover(output_path, autor, title):
    image = Image.open('libs/cover.jpg')
    draw = ImageDraw.Draw(image)
    font1 = ImageFont.truetype('libs/Horovod-Regular.ttf', size=22)
    font2 = ImageFont.truetype('libs/Horovod-Regular.ttf', size=26)
    
    bbox = draw.textbbox((0, 0), autor, font=font1)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (image.width - text_width) / 2
    y = (image.height - text_height) / 3
    draw.text((x, y), autor, font=font1, fill='black')
    
    bbox = draw.textbbox((0, 0), title, font=font2)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (image.width - text_width) / 2
    y = (image.height - text_height) / 3 + 24
    draw.text((x, y), title, font=font2, fill='black')

    image.save(output_path)