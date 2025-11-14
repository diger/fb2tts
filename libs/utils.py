import os
import re
import json
import requests
import zipfile
import torch
import numpy as np
from ruaccent import RUAccent
from vosk_tts import Model, Synth
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

with open('dict/word_dict.json', 'r', encoding="utf-8") as file:
    word_dict = json.load(file)

with open('dict/num_dict.json', 'r', encoding="utf-8") as fl:
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
                m, status = download_model(model_url,silero_filepath)
                if m is None:
                    return m, status
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = torch.package.PackageImporter(silero_filepath).load_pickle("tts_models", "model")
            self.model.to(device)
            return ver, "Модель успешно загружена!"
        else:
            vosk_path = f'models/vosk-model-tts-ru-0.{ver}-multi'
            vosk_filepath = os.path.join(now_dir, local_folder, f"vosk-model-tts-ru-0.{ver}-multi.zip")
            os.makedirs(local_folder, exist_ok=True)
            if not os.path.isfile(vosk_filepath) and not os.path.exists(f'{now_dir}/{vosk_path}'):
                print(f'Download vosk-model 0.{ver}')
                model_url = f"https://alphacephei.com/vosk/models/vosk-model-tts-ru-0.{ver}-multi.zip"
                m, status = download_model(model_url,vosk_filepath)
                if m is None:
                    return m, status
            elif not os.path.exists(f'{now_dir}/{vosk_path}'):
                with zipfile.ZipFile(vosk_filepath, 'r') as zip_ref:
                    zip_ref.extractall(local_folder)
            self.model = Model(model_path=vosk_path, model_name="vosk-model-tts-ru-0.9-multi")
            return ver, "Модель успешно загружена!"
    
    def synth_audio(self, text, speaker_id):
        if self.ver == 5:
            np_audio = self.model.apply_tts(text,
                                              speaker=speaker_id,
                                              sample_rate=48000
                                              )
            np_audio = np_audio.detach().numpy()
            np_audio = (np_audio * 32767).astype(np.int16)
            return np_audio,48000
        else:
            return Synth(self.model).synth_audio(text, speaker_id=speaker_id),22050

synth = TTSModel()

class ACCModel:
    def __init__(self):
        self.accentizer = None
        self.ver = None

    def load(self, ver):
        self.ver = ver
        if ver == 1:
            self.accentizer = RUAccent()
            self.accentizer.load(
                omograph_model_size='big_poetry',
                use_dictionary=True,
                device=device,
                workdir="./models"
            )
            return ver, "Модель успешно загружена!"
        else:
            silero_stress = 'accentor.pt'
            silero_directory = 'models/silero_stress'
            silero_filepath = os.path.join(now_dir, silero_directory, silero_stress)
            if not os.path.isfile(silero_filepath):
                os.makedirs(silero_directory, exist_ok=True)
                print(f'Download silero stress')
                model_url = "https://github.com/snakers4/silero-stress/raw/refs/heads/master/src/silero_stress/data/accentor.pt"
                m, status = download_model(model_url,silero_filepath)
                if m is None:
                    return m, status
            self.accentizer = torch.package.PackageImporter(silero_filepath).load_pickle("accentor_models", "accentor")
            quantized_weight = self.accentizer.homosolver.model.bert.embeddings.word_embeddings.weight.data.clone()
            restored_weights = self.accentizer.homosolver.model.bert.scale * (quantized_weight - self.accentizer.homosolver.model.bert.zero_point)
            self.accentizer.homosolver.model.bert.embeddings.word_embeddings.weight.data = restored_weights
            return ver, "Модель успешно загружена!"

    def process_accent(self, string, regexp):
        if self.ver == 1:
            return self.accentizer.process_all(string, regexp)
        else:
            return self.accentizer(string)

accentizer = ACCModel()


def download_model(model_url, target_path):
    try:
        response = requests.get(model_url, stream=True, timeout=5)
        response.raise_for_status()
        expected_size = int(response.headers.get('content-length', 0))
        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        actual_size = os.path.getsize(target_path)
        if actual_size > 0 and (expected_size == 0 or actual_size == expected_size):
            return True, True
        else:
            if os.path.exists(target_path):
                os.remove(target_path)
            return None, 'Error: Размер неверный!'

    except Exception as e:
        if os.path.exists(target_path):
            os.remove(target_path)
        return None, f'Error: {e}'

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