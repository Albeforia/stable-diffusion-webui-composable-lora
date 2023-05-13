#
# Composable-Diffusion with Lora
#
import torch
import gradio as gr

import composable_lora
import composable_lora_function_handler
import modules.scripts as scripts
from modules import script_callbacks
from modules.processing import StableDiffusionProcessing

def unload():
    torch.nn.Linear.forward = torch.nn.Linear_forward_before_lora
    torch.nn.Conv2d.forward = torch.nn.Conv2d_forward_before_lora
    torch.nn.MultiheadAttention.forward = torch.nn.MultiheadAttention_forward_before_lora

if not hasattr(torch.nn, 'Linear_forward_before_lora'):
    if hasattr(torch.nn, 'Linear_forward_before_lyco'):
        torch.nn.Linear_forward_before_lora = torch.nn.Linear_forward_before_lyco
    else:
        torch.nn.Linear_forward_before_lora = torch.nn.Linear.forward

if not hasattr(torch.nn, 'Conv2d_forward_before_lora'):
    if hasattr(torch.nn, 'Conv2d_forward_before_lyco'):
        torch.nn.Conv2d_forward_before_lora = torch.nn.Conv2d_forward_before_lyco
    else:
        torch.nn.Conv2d_forward_before_lora = torch.nn.Conv2d.forward

if not hasattr(torch.nn, 'MultiheadAttention_forward_before_lora'):
    if hasattr(torch.nn, 'MultiheadAttention_forward_before_lyco'):
        torch.nn.MultiheadAttention_forward_before_lora = torch.nn.MultiheadAttention_forward_before_lyco
    else:
        torch.nn.MultiheadAttention_forward_before_lora = torch.nn.MultiheadAttention.forward

torch.nn.Linear.forward = composable_lora.lora_Linear_forward
torch.nn.Conv2d.forward = composable_lora.lora_Conv2d_forward

script_callbacks.on_script_unloaded(unload)

class ComposableLoraScript(scripts.Script):
    def title(self):
        return "Composable Lora"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("Composable Lora", open=False):
                enabled = gr.Checkbox(value=False, label="Enabled")
                opt_composable_with_step = gr.Checkbox(value=False, label="Composable LoRA with step")
                opt_uc_text_model_encoder = gr.Checkbox(value=False, label="Use Lora in uc text model encoder")
                opt_uc_diffusion_model = gr.Checkbox(value=False, label="Use Lora in uc diffusion model")
                opt_plot_lora_weight = gr.Checkbox(value=False, label="Plot the LoRA weight in all steps")
                opt_single_no_uc = gr.Checkbox(value=False, label="Don't use LoRA in uc if there're no subprompts")

        return [enabled, opt_composable_with_step, opt_uc_text_model_encoder, opt_uc_diffusion_model, opt_plot_lora_weight, opt_single_no_uc]

    def process(self, p: StableDiffusionProcessing, enabled: bool, opt_composable_with_step: bool, opt_uc_text_model_encoder: bool, opt_uc_diffusion_model: bool, opt_plot_lora_weight: bool, opt_single_no_uc: bool):
        composable_lora.enabled = enabled
        composable_lora.opt_uc_text_model_encoder = opt_uc_text_model_encoder
        composable_lora.opt_uc_diffusion_model = opt_uc_diffusion_model
        composable_lora.opt_composable_with_step = opt_composable_with_step
        composable_lora.opt_plot_lora_weight = opt_plot_lora_weight
        composable_lora.opt_single_no_uc = opt_single_no_uc

        composable_lora.num_batches = p.batch_size
        composable_lora.num_steps = p.steps

        composable_lora_function_handler.on_enable()
        composable_lora.reset_step_counters()

        prompt = p.all_prompts[0]
        composable_lora.negative_prompt = p.all_negative_prompts[0]
        composable_lora.load_prompt_loras(prompt)
        composable_lora.sd_processing = p

    def process_batch(self, p: StableDiffusionProcessing, *args, **kwargs):
        composable_lora.sd_processing = p
        composable_lora.reset_counters()

    def postprocess(self, p, processed, *args):
        composable_lora_function_handler.on_disable()
        if composable_lora.enabled:
            if composable_lora.opt_plot_lora_weight:
                processed.images.extend([composable_lora.plot_lora()])
