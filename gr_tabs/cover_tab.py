import os
import gradio as gr
from libs.utils import convert_to_jpg,load_image,add_text_cover
from libs.fix_fb2 import adopt_for_parse

now_dir = os.getcwd()

def save_cover_image(ab_name,cv_img):
    data_path = os.path.join(now_dir, "data", ab_name)
    destination_path = os.path.join(data_path, 'cover.jpg')
    if os.path.exists(destination_path):
        os.remove(destination_path)
    gr.Info("Файл загружен",duration=4)
    return convert_to_jpg(cv_img,destination_path)

def get_cover_image(ab_name):
    work_dir = os.path.join(now_dir, "data", ab_name)
    args = lambda: None
    args.name = f'{work_dir}/{ab_name}.fb2'
    args.work_dir = work_dir
    args.multilang = False
    args.debug = 0
    args.tag = None
    adopt_for_parse(args)
    return load_image(ab_name)

def gen_cover(ab_path):
    work_dir = os.path.join(now_dir, "data", ab_name)
    args = lambda: None
    args.name = f'{work_dir}/{ab_name}.fb2'
    args.work_dir = work_dir
    args.multilang = False
    args.debug = 0
    args.tag = None
    desc = adopt_for_parse(args)
    add_text_cover( \
            f'{args.work_dir}/cover.jpg', \
            f"{desc['first_name']} {desc['last_name']}", \
            desc['book_title']
        )
    return load_image(ab_name)

def cover_tab(ab_path, ab_state):
    with gr.Tab("Обложка", id=0) as cv_tab:
        with gr.Row():
            cur_image = gr.State()
            cover_image = gr.Image(interactive=True, sources=['upload', 'clipboard'])
        with gr.Row():
            cover_from_fb2 = gr.Button("Получить изображение из FB2")
            text_button = gr.Button("Подписать изображение")

    ab_state.change(
        fn=load_image,
        inputs=ab_path,
        outputs=cover_image
    )
    cv_tab.select(
        fn=load_image,
        inputs=ab_path,
        outputs=cover_image
    )
    cover_image.upload(
        fn=save_cover_image,
        inputs=[ab_path,cover_image],
        outputs=cover_image
    )
    cover_from_fb2.click(
        get_cover_image,
        inputs=ab_path,
        outputs=cover_image
    )
    text_button.click(
        gen_cover,
        inputs=ab_path,
        outputs=cover_image
    )