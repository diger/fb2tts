import os
import librosa
import json
import shutil
import gradio as gr
import pandas as pd
from pydub import AudioSegment
from libs.utils import get_data_list, word_dict

now_dir = os.getcwd()
sound_dir = os.path.join(now_dir, "sound")
ev_path = os.path.join(sound_dir, 'events')
back_path = os.path.join(sound_dir, 'back')

def save_dict(cust_dict,exc_abrs,list_of_snd):
    n_dict=dict()
    n_dict['cust_dict'] = dict(cust_dict)
    n_dict['list_of_snd'] = dict(list_of_snd)
    n_dict['exc_abrs'] = [item for sublist in exc_abrs for item in sublist]
    with open('dict/word_dict.json', 'w') as file:
        json.dump(n_dict, file, sort_keys=False,ensure_ascii=False,indent=4)
    gr.Info("Настройки сохранены", duration=4)

def save_audio(inp_audio,file_name,ch_sr=22050,index=0):
    ab_path = back_path
    if index == 2:
        ab_path = ev_path
    if not os.path.exists(ab_path):
        os.makedirs(ab_path)
    destination_path = os.path.join(ab_path, file_name)
    if os.path.exists(destination_path):
        gr.Info(f'Файл {file_name} уже есть', duration=4)
    else:
        sr, np_audio = inp_audio
        audio = AudioSegment(
            np_audio.tobytes(),
            frame_rate=sr,
            sample_width=2,
            channels=1
        )
        if ch_sr:
            audio.set_frame_rate(22050)
        audio.export(f'{ab_path}/{file_name}.wav',format='wav')
        gr.Info("Файл сохранён", duration=4)
    return get_data_list(ab_path)

def toggle_tab():
    return gr.Tabs(visible=True, selected=0)

def select_file(evt: gr.SelectData):
    if evt.value is not None:
        return {"interactive": True, "__type__": "update"}, os.path.join(back_path, evt.value)
    else:
        return {"interactive": False, "__type__": "update"}, None

def del_file(filename):
    f_name = os.path.basename(filename)
    gr.Info(f'Remove {f_name}', duration=2)
    os.remove(filename)
    return gr.FileExplorer(ignore_glob='*.mp3')

def get_file_info(s_in):
    return {"interactive": True, "__type__": "update"}

def refresh_fl(ab_name):
    return {"value": ab_name, "choices": sorted(get_data_list(ev_path)), "__type__": "update"}

def snd_list():
    snd_path = os.path.join(sound_dir, "events")
    return [
        dirpath
        for dirpath in os.listdir(snd_path)
    ]

def upload_audio(dropbox):
    ab_file = os.path.basename(dropbox)
    ab_name = os.path.splitext(ab_file)[0]
    return {"value": ab_file, "__type__": "update"}, dropbox

def add_event(ev_name, s_name, new_sound=None):
    if new_sound is not None:
        save_audio(new_sound,s_name)
    ab_file = os.path.basename(s_name)
    ab_name = os.path.splitext(ab_file)[0]
    word_dict['list_of_snd'][ev_name] = ab_name
    return {"value": list(word_dict['list_of_snd'].items()), "__type__": "update"}

def set_tab(evt: gr.SelectData):
    return evt.index

def settings_tab():
    tab_index = gr.State(value=0)
    with gr.Tabs() as s_tabs:
        with gr.Tab("Фоновая музыка", id=0):
            with gr.Row():
                with gr.Column():
                    audio_fe = gr.Dataframe(
                        headers=['Имя файла'],
                        value=get_data_list(back_path),
                        interactive=False,
                    )
                with gr.Column():
                    del_butt = gr.Button("❌ Удалить файл")
                    with gr.Row():
                        upload_back_file = gr.UploadButton(
                            "Загрузить фоновую музыку",
                            file_count="single",
                            file_types=[".mp3", ".wav"]
                        )
                    with gr.Row():
                        ch_sr = gr.Checkbox(value=True, label="Изменить частоту дискретизации", interactive=False)
                        file_name = gr.Text(show_label=False, placeholder='Имя нового файла',interactive=True)
                    save_file_butt = gr.Button("Сохранить файл")
            with gr.Row():
                back_audio_input = gr.Audio(interactive=False,show_download_button=False)
        with gr.Tab("Словарь исключений", id=1):
            with gr.Row():
                exception_word = gr.Dataframe(
                    headers=["Исключение", "С ударением"],
                    value=list(word_dict['cust_dict'].items()),
                    interactive=True,
                    type ='array',
                    datatype=["str", "str"],
                    col_count=2
                )
                exception_abr = gr.Dataframe(
                    headers=["Аббревиатура"],
                    value=word_dict['exc_abrs'],
                    interactive=True,
                    type ='array',
                    datatype=["str"],
                    col_count=1
                )
            with gr.Row():
                save_exept_butt = gr.Button("Сохранить изменения")
        with gr.Tab("Озвучка событий", id=2):
            with gr.Row():
                with gr.Column(scale=1):
                    sound_events = gr.Dataframe(
                        headers=["Описание события", "Звук"],
                        value=list(word_dict['list_of_snd'].items()),
                        interactive=True,
                        type ='array',
                        datatype=["str", "str"],
                    )
                with gr.Column(scale=3):
                    with gr.Row():
                        upload_se_file = gr.UploadButton(
                            "Загрузить звук для события",
                            file_count="single",
                            file_types=[".mp3", ".wav"]
                        )
                    with gr.Row():
                        ev_audio = gr.Audio(interactive=False,show_download_button=False)
                    with gr.Row():
                        ev_name = gr.Text(show_label=False, placeholder='Описание события')
                        se_path = gr.Dropdown(
                            show_label=False,
                            allow_custom_value=True,
                            choices=get_data_list(ev_path),
                            interactive=True,
                        )
                        ad_ev_butt = gr.Button("Добавить событие")
            with gr.Row():
                save_ev_butt = gr.Button("Сохранить изменения")

        save_exept_butt.click(
            save_dict,
            inputs=[exception_word,exception_abr,sound_events]
        )
        save_ev_butt.click(
            save_dict,
            inputs=[exception_word,exception_abr,sound_events]
        )
        del_butt.click(
            del_file,
            inputs=audio_fe,
            outputs=audio_fe
        )
        upload_back_file.upload(
            upload_audio,
            inputs=[upload_back_file],
            outputs=[file_name,back_audio_input]
        )
        save_file_butt.click(
            save_audio,
            inputs=[back_audio_input,file_name,ch_sr,tab_index],
            outputs=audio_fe
        )
        audio_fe.select(
            select_file,
            outputs=[del_butt,back_audio_input]
        )
        ad_ev_butt.click(
            add_event,
            inputs=[ev_name,se_path,ev_audio],
            outputs=sound_events
        )
        upload_se_file.upload(
            upload_audio,
            inputs=upload_se_file,
            outputs=[se_path, ev_audio],
        )
        s_tabs.select(
            set_tab,
            outputs=tab_index
        )
        #s_tabs.select(
        #    toggle_tab,
        #    outputs=s_tabs
        #).then(
        #    get_files_list,
        #    outputs=df_output
        #)