import gradio as gr
import torch    
import os
from utils import call
from diffusers.pipelines import StableDiffusionXLPipeline
StableDiffusionXLPipeline.__call__ = call
import os
from trainscripts.textsliders.lora import LoRANetwork, DEFAULT_TARGET_REPLACE, UNET_TARGET_REPLACE_MODULE_CONV
from trainscripts.textsliders.demotrain import train_xl

os.environ['CURL_CA_BUNDLE'] = ''

model_map = {
             'Age' : 'models/age.pt', 
             'Chubby': 'models/chubby.pt',
             'Muscular': 'models/muscular.pt',
             'Surprised Look': 'models/suprised_look.pt',
             'Smiling' : 'models/smiling.pt',
             'Professional': 'models/professional.pt',
             
             'Wavy Eyebrows': 'models/eyebrows.pt',
             'Small Eyes': 'models/eyesize.pt',
             
             'Long Hair' : 'models/longhair.pt',
             'Curly Hair' : 'models/curlyhair.pt',
             
             'Pixar Style' : 'models/pixar_style.pt',
             'Sculpture Style': 'models/sculpture_style.pt',
             
             'Repair Images': 'models/repair_slider.pt',
             'Fix Hands': 'models/fix_hands.pt',
             
            }

ORIGINAL_SPACE_ID = 'baulab/ConceptSliders'
SPACE_ID = os.getenv('SPACE_ID')

SHARED_UI_WARNING = f'''## Attention - Training does not work in this shared UI. You can either duplicate and use it with a gpu with at least 40GB, or clone this repository to run on your own machine.
<center><a class="duplicate-button" style="display:inline-block" target="_blank" href="https://huggingface.co/spaces/{SPACE_ID}?duplicate=true"><img style="margin-top:0;margin-bottom:0" src="https://img.shields.io/badge/-Duplicate%20Space-blue?labelColor=white&style=flat&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAP5JREFUOE+lk7FqAkEURY+ltunEgFXS2sZGIbXfEPdLlnxJyDdYB62sbbUKpLbVNhyYFzbrrA74YJlh9r079973psed0cvUD4A+4HoCjsA85X0Dfn/RBLBgBDxnQPfAEJgBY+A9gALA4tcbamSzS4xq4FOQAJgCDwV2CPKV8tZAJcAjMMkUe1vX+U+SMhfAJEHasQIWmXNN3abzDwHUrgcRGmYcgKe0bxrblHEB4E/pndMazNpSZGcsZdBlYJcEL9Afo75molJyM2FxmPgmgPqlWNLGfwZGG6UiyEvLzHYDmoPkDDiNm9JR9uboiONcBXrpY1qmgs21x1QwyZcpvxt9NS09PlsPAAAAAElFTkSuQmCC&logoWidth=14" alt="Duplicate Space"></a></center>
'''


class Demo:

    def __init__(self) -> None:

        self.training = False
        self.generating = False
        self.device = 'cuda'
        self.weight_dtype = torch.float16
        self.pipe = StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0', torch_dtype=self.weight_dtype).to(self.device)
        self.pipe.enable_xformers_memory_efficient_attention()
        with gr.Blocks() as demo:
            self.layout()
            demo.queue().launch(share=True, max_threads=3)


    def layout(self):

        with gr.Row():

            if SPACE_ID == ORIGINAL_SPACE_ID:

                self.warning = gr.Markdown(SHARED_UI_WARNING)
          
        with gr.Row():
                
            with gr.Tab("Test") as inference_column:

                with gr.Row():

                    self.explain_infr = gr.Markdown(value='This is a demo of [Concept Sliders: LoRA Adaptors for Precise Control in Diffusion Models](https://sliders.baulab.info/). To try out a model that can control a particular concept, select a model and enter any prompt, choose a seed, and finally choose the SDEdit timestep for structural preservation. Higher SDEdit timesteps results in more structural change. For example, if you select the model "Surprised Look" you can generate images for the prompt "A picture of a person, realistic, 8k" and compare the slider effect to the image generated by original model.  We have also provided several other pre-fine-tuned models like "repair" sliders to repair flaws in SDXL generated images (Check out the "Pretrained Sliders" drop-down). You can also train and run your own custom sliders. Check out the "train" section for custom concept slider training.')

                with gr.Row():

                    with gr.Column(scale=1):

                        self.prompt_input_infr = gr.Text(
                            placeholder="Enter prompt...",
                            label="Prompt",
                            info="Prompt to generate"
                        )

                        with gr.Row():

                            self.model_dropdown = gr.Dropdown(
                                label="Pretrained Sliders",
                                choices= list(model_map.keys()),
                                value='Age',
                                interactive=True
                            )

                            self.seed_infr = gr.Number(
                                label="Seed",
                                value=42
                            )
                            
                            self.slider_scale_infr = gr.Slider(
                                -6,
                                6,
                                label="Slider Scale",
                                value=2,
                                info="Larger slider scale result in stronger edit"
                            )

                            
                            self.start_noise_infr = gr.Slider(
                                600, 900, 
                                value=750, 
                                label="SDEdit Timestep", 
                                info="Choose smaller values for more structural preservation"
                            )

                    with gr.Column(scale=2):

                        self.infr_button = gr.Button(
                            value="Generate",
                            interactive=True
                        )

                        with gr.Row():

                            self.image_new = gr.Image(
                                label="Slider",
                                interactive=False,
                                type='pil',
                            )
                            self.image_orig = gr.Image(
                                label="Original SD",
                                interactive=False,
                                type='pil',
                            )

            with gr.Tab("Train") as training_column:

                with gr.Row():

                    self.explain_train= gr.Markdown(value='In this part you can train a concept slider for Stable Diffusion XL.   Enter a target concept you wish to make an edit on. Next, enter a enhance prompt of the attribute you wish to edit (for controlling age of a person, enter "person, old"). Then, type the supress prompt of the attribute (for our example, enter "person, young"). Then press "train" button. With default settings, it takes about 15 minutes to train a slider; then you can try inference above or download the weights. Code and details are at [github link](https://github.com/rohitgandikota/sliders).')

                with gr.Row():

                    with gr.Column(scale=3):

                        self.target_concept = gr.Text(
                            placeholder="Enter target concept to make edit on ...",
                            label="Prompt of concept on which edit is made",
                            info="Prompt corresponding to concept to edit (eg: 'person')",
                            value = ''
                        )
                        
                        self.positive_prompt = gr.Text(
                            placeholder="Enter the enhance prompt for the edit ...",
                            label="Prompt to enhance",
                            info="Prompt corresponding to concept to enhance (eg: 'person, old')",
                            value = ''
                        )
                        
                        self.negative_prompt = gr.Text(
                            placeholder="Enter the suppress prompt for the edit ...",
                            label="Prompt to suppress",
                            info="Prompt corresponding to concept to supress (eg: 'person, young')",
                            value = ''
                        )
                        
                        self.attributes_input = gr.Text(
                            placeholder="Enter the concepts to preserve (comma seperated). Leave empty if not required ...",
                            label="Concepts to Preserve",
                            info="Comma seperated concepts to preserve/disentangle (eg: 'male, female')",
                            value = ''
                        )
                        self.is_person = gr.Checkbox(
                            label="Person", 
                            info="Are you training a slider for person?")

                        self.rank = gr.Number(
                            value=4,
                            label="Rank of the Slider",
                            info='Slider Rank to train'
                        )
                        choices = ['xattn', 'noxattn', 'full']
                        self.train_method_input = gr.Dropdown(
                            choices=choices,
                            value='xattn',
                            label='Train Method',
                            info='Method of training. If xattn - loras will be on cross attns only. noxattn - all layers except cross attn (official implementation). full - all layers'
                        )
                        self.iterations_input = gr.Number(
                            value=1000,
                            precision=0,
                            label="Iterations",
                            info='iterations used to train'
                        )

                        self.lr_input = gr.Number(
                            value=2e-4,
                            label="Learning Rate",
                            info='Learning rate used to train'
                        )

                    with gr.Column(scale=1):

                        self.train_status = gr.Button(value='', variant='primary', interactive=False)

                        self.train_button = gr.Button(
                            value="Train",
                        )

                        self.download = gr.Files()

        self.infr_button.click(self.inference, inputs = [
            self.prompt_input_infr,
            self.seed_infr,
            self.start_noise_infr,
            self.slider_scale_infr,
            self.model_dropdown
            ],
            outputs=[
                self.image_new,
                self.image_orig
            ]
        )
        self.train_button.click(self.train, inputs = [
            self.target_concept,
            self.positive_prompt,
            self.negative_prompt,
            self.rank,
            self.iterations_input,
            self.lr_input,
            self.attributes_input,
            self.is_person
        ],
        outputs=[self.train_button,  self.train_status, self.download, self.model_dropdown]
        )

    def train(self, target_concept,positive_prompt, negative_prompt, rank, iterations_input, lr_input, attributes_input, is_person, pbar = gr.Progress(track_tqdm=True)):

        if attributes_input == '':
            attributes_input = None
        print(target_concept, positive_prompt, negative_prompt, attributes_input, is_person)
        
        randn = torch.randint(1, 10000000, (1,)).item()
        save_name = f"{randn}_{target_concept.replace(',','').replace(' ','').replace('.','')[:10]}_{positive_prompt.replace(',','').replace(' ','').replace('.','')[:10]}"
        save_name += f'_alpha-{1}'
        save_name += f'_noxattn'
        save_name += f'_rank_{rank}.pt'
        
        if torch.cuda.get_device_properties(0).total_memory * 1e-9 < 40:
            return [gr.update(interactive=True, value='Train'), gr.update(value='GPU Memory is not enough for training... Please upgrade to GPU atleast 40GB or clone the repo to your local machine.'), None, gr.update()]
        if self.training:
            return [gr.update(interactive=True, value='Train'), gr.update(value='Someone else is training... Try again soon'), None, gr.update()]
        
        attributes = attributes_input
        if is_person:
            attributes = 'white, black, asian, hispanic, indian, male, female'
        
        self.training = True
        train_xl(target=target_concept, positive=positive_prompt, negative=negative_prompt, lr=lr_input, iterations=iterations_input, config_file='trainscripts/textsliders/data/config-xl.yaml', rank=rank, device=self.device, attributes=attributes, save_name=save_name)
        self.training = False

        torch.cuda.empty_cache()
        model_map['Custom Slider'] = f'models/{save_name}'
        
        return [gr.update(interactive=True, value='Train'), gr.update(value='Done Training! \n Try your custom slider in the "Test" tab'), save_path, gr.Dropdown.update(choices=list(model_map.keys()), value='Custom Slider')]

    
    def inference(self, prompt, seed, start_noise, scale, model_name, pbar = gr.Progress(track_tqdm=True)):
        
        seed = seed or 42

        generator = torch.manual_seed(seed)

        model_path = model_map[model_name]
        unet = self.pipe.unet
        network_type = "c3lier"
        if 'full' in model_path:
            train_method = 'full'
        elif 'noxattn' in model_path:
            train_method = 'noxattn'
        elif 'xattn' in model_path:
            train_method = 'xattn'
            network_type = 'lierla'
        else:
            train_method = 'noxattn'

        modules = DEFAULT_TARGET_REPLACE
        if network_type == "c3lier":
            modules += UNET_TARGET_REPLACE_MODULE_CONV

        name = os.path.basename(model_path)
        rank = 4
        alpha = 1
        if 'rank' in model_path:
            rank = int(model_path.split('_')[-1].replace('.pt',''))
        if 'alpha1' in model_path:
            alpha = 1.0
        network = LoRANetwork(
                unet,
                rank=rank,
                multiplier=1.0,
                alpha=alpha,
                train_method=train_method,
            ).to(self.device, dtype=self.weight_dtype)
        network.load_state_dict(torch.load(model_path))


        generator = torch.manual_seed(seed)
        edited_image = self.pipe(prompt, num_images_per_prompt=1, num_inference_steps=50, generator=generator, network=network, start_noise=int(start_noise), scale=float(scale), unet=unet).images[0]
        
        generator = torch.manual_seed(seed)
        original_image = self.pipe(prompt, num_images_per_prompt=1, num_inference_steps=50, generator=generator, network=network, start_noise=start_noise, scale=0, unet=unet).images[0]
        
        del unet, network
        unet = None
        network = None
        torch.cuda.empty_cache()
        
        return edited_image, original_image 

demo = Demo()
