import os
import re
import json
import urllib.request
import torch
import numpy as np
from io import BytesIO
from vosk_tts import Model, Synth
from silero import silero_tts
from ruaccent import RUAccent
from silero_stress import load_accentor
from PIL import Image, ImageDraw, ImageFont

device = 'CPU'

if torch.cuda.is_available():
    device = 'CUDA'

print(f'Run with {device}')

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

class TTSModel:
    def __init__(self):
        self.model = None
        self.ver = None

    def load(self, ver):
        local_folder = "models"
        os.makedirs(local_folder, exist_ok=True)
        self.ver = ver
        if ver == 5:
            silero_pt = 'v5_ru.pt'
            silero_directory = 'models/silero'
            silero_filepath = os.path.join(now_dir, silero_directory, silero_pt)
            if not os.path.isfile(silero_filepath):
                os.makedirs(silero_directory, exist_ok=True)
                print(f'Download silero model v5')
                model_url = "https://models.silero.ai/models/tts/ru/v5_ru.pt"
                urllib.request.urlretrieve(model_url,silero_filepath)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = torch.package.PackageImporter(silero_filepath).load_pickle("tts_models", "model")
            self.model.to(device)
        else:
            vosk_path = f'models/vosk-model-tts-ru-0.{ver}-multi'
            os.makedirs(local_folder, exist_ok=True)
            if not os.path.exists(f'{now_dir}/{vosk_path}'):
                print(f'Download vosk-model 0.{ver}')
                model_url = f"https://alphacephei.com/vosk/models/vosk-model-tts-ru-0.{ver}-multi.zip"
                with urllib.request.urlopen(model_url) as response:
                    zip_content = BytesIO(response.read())
                with zipfile.ZipFile(zip_content, 'r') as zip_ref:
                    zip_ref.extractall(local_folder)
            self.model = Model(model_path=vosk_path, model_name="vosk-model-tts-ru-0.9-multi")
    
    def synth_audio(self, text, speaker_id, rate):
        if self.ver == 5:
            np_audio = self.model.apply_tts(text,
                                              speaker=speaker_id,
                                              sample_rate=48000)
            np_audio = np_audio.detach().numpy()
            np_audio = (np_audio * 32767).astype(np.int16)
            return np_audio,48000
        else:
            return Synth(model).synth_audio(text, speaker_id=speaker_id),22050



synth = TTSModel()

def load_accent_model(ver=1):
    if ver == 1:
        accentizer = RUAccent()
        accentizer.load(
            omograph_model_size='big_poetry',
            use_dictionary=True,
            device=device,
            workdir="./models"
        )
        return accentizer
    else:
        class Accent:
            def __init__(self):
                self.accentizer = load_accentor()
            
            def process_all(self, text, params=None):
                return self.accentizer(text)
        return Accent()

def get_spk_list(ver=10):
    spk_list = []
    if ver == 5:
        spk_list = ['aidar', 'baya', 'kseniya', 'xenia', 'eugene']
    else:
        with open(f'models/vosk-model-tts-ru-0.{ver}-multi/config.json', 'r') as file:
            data = json.load(file)
        for i in data['speaker_id_map']:
            spk_list.append((i,data['speaker_id_map'][i]))
    return spk_list

def set_args(s_args):
    global args
    args = s_args
    return args

def get_args():
    return args

def convert(seconds):
    min, sec = divmod(seconds, 60)
    min = f'{int(min)} m. ' if min else ''
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