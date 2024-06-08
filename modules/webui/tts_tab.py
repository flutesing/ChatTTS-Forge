import gradio as gr
import torch
from modules.webui.webui_utils import (
    get_speakers,
    get_styles,
    refine_text,
    tts_generate,
)
from modules.webui import webui_config
from modules.webui.examples import example_texts
from modules import config


def create_tts_interface():
    speakers = get_speakers()

    def get_speaker_show_name(spk):
        if spk.gender == "*" or spk.gender == "":
            return spk.name
        return f"{spk.gender} : {spk.name}"

    speaker_names = ["*random"] + [
        get_speaker_show_name(speaker) for speaker in speakers
    ]

    styles = ["*auto"] + [s.get("name") for s in get_styles()]

    history = []

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("🎛️Sampling")
                temperature_input = gr.Slider(
                    0.01, 2.0, value=0.3, step=0.01, label="Temperature"
                )
                top_p_input = gr.Slider(0.1, 1.0, value=0.7, step=0.1, label="Top P")
                top_k_input = gr.Slider(1, 50, value=20, step=1, label="Top K")
                batch_size_input = gr.Slider(
                    1,
                    webui_config.max_batch_size,
                    value=4,
                    step=1,
                    label="Batch Size",
                )

            with gr.Row():
                with gr.Group():
                    gr.Markdown("🎭Style")
                    gr.Markdown("- 后缀为 `_p` 表示带prompt，效果更强但是影响质量")
                    style_input_dropdown = gr.Dropdown(
                        choices=styles,
                        # label="Choose Style",
                        interactive=True,
                        show_label=False,
                        value="*auto",
                    )
            with gr.Row():
                with gr.Group():
                    gr.Markdown("🗣️Speaker")
                    with gr.Tabs():
                        with gr.Tab(label="Pick"):
                            spk_input_text = gr.Textbox(
                                label="Speaker (Text or Seed)",
                                value="female2",
                                show_label=False,
                            )
                            spk_input_dropdown = gr.Dropdown(
                                choices=speaker_names,
                                # label="Choose Speaker",
                                interactive=True,
                                value="female : female2",
                                show_label=False,
                            )
                            spk_rand_button = gr.Button(
                                value="🎲",
                                # tooltip="Random Seed",
                                variant="secondary",
                            )
                            spk_input_dropdown.change(
                                fn=lambda x: x.startswith("*")
                                and "-1"
                                or x.split(":")[-1].strip(),
                                inputs=[spk_input_dropdown],
                                outputs=[spk_input_text],
                            )
                            spk_rand_button.click(
                                lambda x: str(torch.randint(0, 2**32 - 1, (1,)).item()),
                                inputs=[spk_input_text],
                                outputs=[spk_input_text],
                            )

                        with gr.Tab(label="Upload", visible=webui_config.experimental):
                            spk_input_upload = gr.File(label="Speaker (Upload)")
                            # TODO 读取 speaker
                            # spk_input_upload.change(
                            #     fn=lambda x: x.read().decode("utf-8"),
                            #     inputs=[spk_input_upload],
                            #     outputs=[spk_input_text],
                            # )
            with gr.Group():
                gr.Markdown("💃Inference Seed")
                infer_seed_input = gr.Number(
                    value=42,
                    label="Inference Seed",
                    show_label=False,
                    minimum=-1,
                    maximum=2**32 - 1,
                )
                infer_seed_rand_button = gr.Button(
                    value="🎲",
                    # tooltip="Random Seed",
                    variant="secondary",
                )
            use_decoder_input = gr.Checkbox(
                value=True, label="Use Decoder", visible=False
            )
            with gr.Group():
                gr.Markdown("🔧Prompt engineering")
                prompt1_input = gr.Textbox(label="Prompt 1")
                prompt2_input = gr.Textbox(label="Prompt 2")
                prefix_input = gr.Textbox(label="Prefix")

                prompt_audio = gr.File(
                    label="prompt_audio", visible=webui_config.experimental
                )

            infer_seed_rand_button.click(
                lambda x: int(torch.randint(0, 2**32 - 1, (1,)).item()),
                inputs=[infer_seed_input],
                outputs=[infer_seed_input],
            )
        with gr.Column(scale=4):
            with gr.Group():
                input_title = gr.Markdown(
                    "📝Text Input",
                    elem_id="input-title",
                )
                gr.Markdown(f"- 字数限制{webui_config.tts_max:,}字，超过部分截断")
                gr.Markdown("- 如果尾字吞字不读，可以试试结尾加上 `[lbreak]`")
                gr.Markdown(
                    "- If the input text is all in English, it is recommended to check disable_normalize"
                )
                text_input = gr.Textbox(
                    show_label=False,
                    label="Text to Speech",
                    lines=10,
                    placeholder="输入文本或选择示例",
                    elem_id="text-input",
                )
                # TODO 字数统计，其实实现很好写，但是就是会触发loading...并且还要和后端交互...
                # text_input.change(
                #     fn=lambda x: (
                #         f"📝Text Input ({len(x)} char)"
                #         if x
                #         else (
                #             "📝Text Input (0 char)"
                #             if not x
                #             else "📝Text Input (0 char)"
                #         )
                #     ),
                #     inputs=[text_input],
                #     outputs=[input_title],
                # )
                with gr.Row():
                    contorl_tokens = [
                        "[laugh]",
                        "[uv_break]",
                        "[v_break]",
                        "[lbreak]",
                    ]

                    for tk in contorl_tokens:
                        t_btn = gr.Button(tk)
                        t_btn.click(
                            lambda text, tk=tk: text + " " + tk,
                            inputs=[text_input],
                            outputs=[text_input],
                        )

            with gr.Group():
                gr.Markdown("🎄Examples")
                sample_dropdown = gr.Dropdown(
                    choices=[sample["text"] for sample in example_texts],
                    show_label=False,
                    value=None,
                    interactive=True,
                )
                sample_dropdown.change(
                    fn=lambda x: x,
                    inputs=[sample_dropdown],
                    outputs=[text_input],
                )

            with gr.Group():
                gr.Markdown("🎨Output")
                tts_output = gr.Audio(label="Generated Audio")
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("🎶Refiner")
                refine_prompt_input = gr.Textbox(
                    label="Refine Prompt",
                    value="[oral_2][laugh_0][break_6]",
                )
                refine_button = gr.Button("✍️Refine Text")
                # TODO 分割句子，使用当前配置拼接为SSML，然后发送到SSML tab
                # send_button = gr.Button("📩Split and send to SSML")

            with gr.Group():
                gr.Markdown("🔊Generate")
                disable_normalize_input = gr.Checkbox(
                    value=False, label="Disable Normalize"
                )

                with gr.Group(visible=webui_config.experimental):
                    gr.Markdown("💪🏼Enhance")
                    enable_enhance = gr.Checkbox(value=False, label="Enable Enhance")
                    enable_de_noise = gr.Checkbox(value=False, label="Enable De-noise")
                tts_button = gr.Button(
                    "🔊Generate Audio",
                    variant="primary",
                    elem_classes="big-button",
                )

    refine_button.click(
        refine_text,
        inputs=[text_input, refine_prompt_input],
        outputs=[text_input],
    )

    tts_button.click(
        tts_generate,
        inputs=[
            text_input,
            temperature_input,
            top_p_input,
            top_k_input,
            spk_input_text,
            infer_seed_input,
            use_decoder_input,
            prompt1_input,
            prompt2_input,
            prefix_input,
            style_input_dropdown,
            disable_normalize_input,
            batch_size_input,
            enable_enhance,
            enable_de_noise,
        ],
        outputs=tts_output,
    )