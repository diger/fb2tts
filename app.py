import os
import json
import gradio as gr
import shutil
from pydub import AudioSegment
from libs.utils import get_data_list,data_path, now_dir, load_vosk_model, accentizer, device
from gr_tabs.parse_tab import parse_tab
from gr_tabs.tts_tab import tts_tab,synth
from gr_tabs.settings_tab import settings_tab
from gr_tabs.cover_tab import cover_tab

gr.set_static_paths(paths=[data_path,])

sound_dir = os.path.join(now_dir, "sound")

accentizer.load(omograph_model_size='big_poetry', use_dictionary=True, device=device, workdir="./model")

def refresh_data(ab_name):
    return {"value": ab_name, "choices": sorted(get_data_list()), "__type__": "update"}

def remove_dataset(ab_name):
    ab_path = os.path.join(now_dir, "data", ab_name)
    gr.Warning(f'Remove Dataset {ab_name}')
    shutil.rmtree(ab_path)
    return {"value": '', "choices": sorted(get_data_list()), "__type__": "update"}, \
            {"visible": False, "__type__": "update"}

def save_drop_dataset_audio(dropbox):
    ab_file = os.path.basename(dropbox)
    ab_name = os.path.splitext(ab_file)[0]
    ab_path = os.path.join(now_dir, "data", ab_name)
    if not os.path.exists(ab_path):
        os.makedirs(ab_path)
    destination_path = os.path.join(ab_path, ab_file)
    if os.path.exists(destination_path):
        os.remove(destination_path)
    shutil.copy(dropbox, destination_path)
    gr.Info("Файл загружен",duration=4)
    return refresh_data(ab_name)

def get_spk_list():
    with open('model/vosk-model-tts-ru-0.10-multi/config.json', 'r') as file:
        data = json.load(file)
    spk_list = []
    for i in data['speaker_id_map']:
        spk_list.append((i,data['speaker_id_map'][i]))
    return spk_list

def toggle_tab(ab_path):
    return gr.Tabs(visible=True, selected=0),ab_path

def put_accents(string):
    string = accentizer.process_all(string,'\+\w+|\w+\+\w+')
    return string

def text_to_audio(string, spk, rate=1, noise=None):
    np_audio = synth.synth_audio(string,speaker_id=spk,speech_rate=rate,noise_level=noise)
    return (22050, np_audio)

with gr.Blocks(theme='argilla/argilla-theme', title="🇷🇺") as App:
    with gr.Tabs():
        with gr.TabItem("Demo TTS"):
            with gr.Row():
                spk_sel = gr.Dropdown(
                    value=0,
                    label='Выбрать голос',
                    choices=get_spk_list(),
                    interactive=True,
                )
                speech_rate = gr.Slider(
                    0,
                    3,
                    1,
                    step=0.1,
                    label="Задать скорость",
                    interactive=True,
                )
                noise_lvl = gr.Slider(
                    0,
                    2,
                    0.8,
                    step=0.1,
                    label="Уровень шума",
                    interactive=True,
                )
            with gr.Row():
                text_input = gr.Textbox(label='Текст',lines=2, placeholder="Введите текст для озвучки", interactive=True,)
                audio_output = gr.Audio(interactive=False,show_download_button=False)
            with gr.Row():
                accent_button = gr.Button("Проставить ударения")
                tts_button = gr.Button("Преобразовать в речь")

            accent_button.click(
                put_accents,
                inputs=text_input,
                outputs=text_input
            )
            tts_button.click(
                text_to_audio,
                inputs=[text_input,spk_sel,speech_rate,noise_lvl],
                outputs=audio_output
            )
        with gr.TabItem("Fb2TTS"):
            ab_state= gr.State()
            with gr.Row():
                ab_path = gr.Dropdown(
                    value='',
                    show_label=False,
                    allow_custom_value=True,
                    choices=get_data_list(),
                    interactive=True,
                )
                rm_dataset = gr.Button("❌ Удалить АК")
                upload_text_file = gr.UploadButton("Загрузить файл", file_count="single", file_types=[".fb2", ".txt"])
            with gr.Tabs(visible=False) as tabs:
                cover_tab(ab_path,ab_state)
                parse_tab(ab_path)
                tts_tab(ab_path, get_spk_list())

            upload_text_file.upload(
                fn=save_drop_dataset_audio,
                inputs=upload_text_file,
                outputs=[ab_path],
            ).then(
                toggle_tab,
                inputs=ab_path,
                outputs=[tabs,ab_state]
            )

            rm_dataset.click(
                remove_dataset,
                inputs=ab_path,
                outputs=[ab_path,tabs]
            )

            ab_path.select(
                toggle_tab,
                inputs=ab_path,
                outputs=[tabs,ab_state]
            )

        with gr.TabItem("Настройки"):
            settings_tab()

App.launch(
    share=False,
    server_name="0.0.0.0",
    allowed_paths=[sound_dir],
    favicon_path='libs/vosk.ico'
)