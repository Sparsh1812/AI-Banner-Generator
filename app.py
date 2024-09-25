
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
import base64
import os
import random
import json
import logging
import math
from gradio_client import Client
import copy

from flask_cors import CORS
# from huggingface_hub import login
# login(token=os.environ.get("HF_TOKEN"))


app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Enable CORS for all routes and origins
CORS(app)

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


flux_client = Client("black-forest-labs/FLUX.1-schnell")



# Updated templates to support multiple images
TEMPLATES = [
    # templates for 1360x800 resolution
    {
        "resolution": "1360x800",
        "num_images": 1,    
        "objects": [
        {"type":"text","left":"7.86%","bottom":"49.62%","width":"48%","height":"100%","fontSize":48,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":"","fontFamily":"Gill Sans MT"},
        {"type":"text","left":"7.44%","bottom":"36.78%","width":"48%","height":"100%","fontSize":64,"fill":"","fontWeight":"bold","fontStyle":"normal","textAlign":"left","text":"","fontFamily":"Arial Black"},
        {"type":"image","left":"62%","bottom":"7%","width":"70%","height":"70%","src":""},
        ]
    },
    {
        "resolution": "1360x800",
        "num_images": 1,
        "objects": [
            {"type":"text","left":"7.52%","bottom":"49.90%","width":"48.99%","height":"100%","fontSize":48,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":"","fontFamily":"Gill Sans MT"},
            {"type":"text","left":"7.02%","bottom":"38.15%","width":"48.00%","height":"100%","fontSize":64,"fill":"","fontWeight":"bold","fontStyle":"normal","textAlign":"left","text":"","fontFamily":"Arial Black"},
            {"type":"image","left":"70.34%","bottom":"8.05%","width":"70%","height":"70%","src":""}
        ]
    },
    {
        "resolution": "1360x800",
        "num_images": 2,    
        "objects": [
            {"type":"text","left":"6.00%","bottom":"49.55%","width":"44.23%","height":"100%","fontSize":50,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":"","fontFamily":"Trebuchet MS"},
            {"type":"text","left":"6.00%","bottom":"33.03%","width":"43.91%","height":"100%","fontSize":60,"fill":"","fontWeight":"bold","fontStyle":"normal","textAlign":"left","text":"","fontFamily":"Verdana"},
            {"type":"image","left":"60.42%","bottom":"15.57%","width":"50%","height":"50%","src":""},
            {"type":"image","left":"70.42%","bottom":"15.46%","width":"50%","height":"50%","src":""},
        ]
    },
    {
        "resolution": "1360x800",
        "num_images": 3,    
        "objects": [
            {"type":"text","left":"7.52%","bottom":"49.90%","width":"48.99%","height":"100%","fontSize":48,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":"","fontFamily":"Gill Sans MT"},
            {"type":"text","left":"7.02%","bottom":"38.15%","width":"48.00%","height":"100%","fontSize":64,"fill":"","fontWeight":"bold","fontStyle":"normal","textAlign":"left","text":"","fontFamily":"Arial Black"},
            {"type":"image","left":"60.42%","bottom":"15.57%","width":"50%","height":"50%","src":""},
            {"type":"image","left":"70.42%","bottom":"15.46%","width":"50%","height":"50%","src":""},
            {"type":"image","left":"82.47%","bottom":"16.39%","width":"50%","height":"50%","src":""}
        ]
    }
]




def generate_background(theme, color_palette, canvasWidth, canvasHeight):
    colors = ",".join(color_palette)
    prompt = f"abstract background image banner, background theme: {theme}, background colors: {colors}"
    print(f"Generating background image for: {prompt}")
    # flux_client = Client("black-forest-labs/FLUX.1-schnell")
    result = flux_client.predict(
        prompt=prompt,
        seed=0,
        randomize_seed=True,
        width=canvasWidth,
        height=canvasHeight,
        num_inference_steps=4,
        api_name="/infer"
    )
    return result

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def round_percentages(template):
    for obj in template['objects']:
        # Update 'left', 'top', 'width', 'height' values
        for key in ['left', 'bottom', 'width', 'height']:
            if key in obj:
                value = obj[key]
                if isinstance(value, str) and value.endswith('%'):
                    numeric_value = float(value.strip('%'))
                    rounded_value = math.ceil(numeric_value)
                    obj[key] = f"{rounded_value}%"
                elif isinstance(value, (int, float)):
                    # Assuming the value is in percentage and needs rounding
                    rounded_value = math.ceil(value)
                    obj[key] = f"{rounded_value}%"
    return template

def select_template(resolution, num_images):
    """
    Selects the appropriate template based on resolution and number of images.
    Falls back to a default template if no exact match is found.
    """
    filtered_templates = []
    for template in TEMPLATES:
        if template['resolution'] == resolution and template['num_images'] == num_images:
            # add to filtered templates
            filtered_templates.append(template)
    # if filtered templates are not empty, return a random template from filtered templates
    if filtered_templates:
        return random.choice(filtered_templates)
    else:
        # Fallback: match resolution regardless of image count
        for template in TEMPLATES:
            if template['resolution'] == resolution:
                filtered_templates.append(template)
    # if filtered templates are not empty, return a random template from filtered templates
    if filtered_templates:
        return random.choice(filtered_templates)
    else:
        # Fallback: return a default template
        return random.choice(TEMPLATES)
    

def generate_banner(promotion, theme, resolution, color_palette, image_data_list):
    # modify this such that the PIL is used to convert the background image path to file which could be passed 
    # to the gemini api for figuring out text colors based on background image.
    try:
        num_images = len(image_data_list)
        # print("Number of images: ", num_images)

        input_images_list = []
        has_atleast_one_potrait_image = False
        for image_data in image_data_list: # converting base64 encoded data to image for gemini api request
            decoded_image = Image.open(io.BytesIO( base64.b64decode(image_data.split(",")[1])))
            input_images_list.append(decoded_image)
            img_width, img_height = decoded_image.size #could be used for checking if image is landscape or potrait
            print("IMAGE RES: ", f'{img_width}, {img_height}')
            if img_height > img_width:
                has_atleast_one_potrait_image = True
        
        
        selected_template = select_template(resolution, num_images)
        template = round_percentages(copy.deepcopy(selected_template))
        
        # modifying the current template position of images if all images are of landscape resolution
        if not has_atleast_one_potrait_image:
            for obj in template['objects']:
                if obj['type'] == 'image':
                    if 'bottom' in obj and 'left' in obj:
                        bottom = int(obj['bottom'].rstrip('%'))
                        left = int(obj['left'].rstrip('%'))
                        obj['bottom'] = str(min(100, bottom + 15)) + "%" #inc by 15%
                        obj['left'] = str(max(0, left - 5)) + "%" #dec by 5%

        width, height = map(int, resolution.split('x'))

        # Generate background image
        background_image_path = generate_background(theme, color_palette, width, height)[0]
        background_image_base64 = image_to_base64(background_image_path)
        background_image = Image.open(io.BytesIO( base64.b64decode(background_image_base64))) # for sending background image to gemini
       
        
        prompt = f"""
        Create a banner design based on the following:
        Template: {template['objects']}
        Promotion: {promotion}
        Theme: {theme}
        Resolution: {width}x{height}
        Background image: <the first image is background image of banner design>
        Product images: <the images except the first one are product images of banner design>
        Color Palette: {color_palette} (background image may consist of combination of these colors)

        Return JSON only:
        {{
        "backgroundImage": <concise and brief description of background image>,
        "products": <write name of each product seperated by ",">,
        "mainText": "<promotion text, keep it short>",
        "secondaryText": "<if applicable, max 7 words, be creative based on products>",
        "textColors": {{
            "mainText": "<hex color value for primary text based on colors from the first image>",
            "secondaryText": "<hex color value for secondary text based on colors from the first image>"
        }}

        }}
        Apply design principles for readability and prominence. Return JSON only.
        """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt, background_image]+input_images_list) #input_images_list has input images

        logging.debug(f"Gemini API response: {response.text}")

        design_choices = parse_gemini_response(response.text)

        # Apply design choices 
        modified_template = apply_design_choices(template, design_choices, width, height, image_data_list)

        # Generate background image
        # background_image_path = generate_background(theme, color_palette, width, height)[0]
        # background_image_base64 = image_to_base64(background_image_path)

        modified_template['objects'].insert(0, {
            "type": "image",
            "left": "0%",
            "top": "0%",
            "width": "100%",
            "height": "100%",
            "src": f"data:image/png;base64,{background_image_base64}"
        })

        return modified_template
        # return responsive_template
    except Exception as e:
        logging.error(f"Error in generate_banner: {str(e)}")
        raise

def parse_gemini_response(response_text):
    try:
        clean_text = response_text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {str(e)}")
        logging.error(f"Raw response: {response_text}")
        raise ValueError("Invalid JSON response from Gemini API")
    
def get_smallest_font_size(template):
    smallest_font_size = float('inf')
    for obj in template['objects']:
        if obj['type'] == 'text':
            if obj['fontSize'] < smallest_font_size:
                smallest_font_size = obj['fontSize']
    return smallest_font_size

def apply_design_choices(template, choices, width, height, image_data_list):
    # Reset image_index for each function call
    image_index = 0
    # compare font size of text objects and store the smallest one
    smallest_font_size = get_smallest_font_size(template)

    for obj in template['objects']:
        if obj['type'] == 'text':
            if 'mainText' in choices and obj['fontSize'] > smallest_font_size:
                obj['text'] = choices['mainText'] or ""
                obj['fill'] = choices['textColors'].get('mainText', '#000000')
            elif 'secondaryText' in choices and obj['fontSize'] <= smallest_font_size:
                obj['text'] = choices['secondaryText'] or ""
                obj['fill'] = choices['textColors'].get('secondaryText', '#000000')

            obj['fontFamily'] = obj.get('fontFamily', 'Arial')
            obj['fontSize'] = obj.get('fontSize', 20)
            obj['fontWeight'] = obj.get('fontWeight', 'normal')
            obj['fontStyle'] = obj.get('fontStyle', 'normal')
            obj['textAlign'] = obj.get('textAlign', 'left')

        elif obj['type'] == 'image':
            if image_index < len(image_data_list) and image_data_list[image_index]:
                obj['src'] = f"data:image/jpeg;base64,{image_data_list[image_index]}"
                image_index += 1
            else:
                # Remove the image object if no data is available
                obj['src'] = ''

    # Remove any image objects with empty src
    template['objects'] = [obj for obj in template['objects'] if obj['type'] != 'image' or obj['src']]

    template['width'] = width
    template['height'] = height

    return template

@app.route('/generate_banner', methods=['POST'])
def create_banner():
    try:
        data = request.json
        promotion = data['promotion']
        theme = data['theme']
        resolution = data['resolution']
        color_palette = data['color_palette']
        image_data_list = data['images']

        banner_data = generate_banner(promotion, theme, resolution, color_palette, image_data_list)
        return jsonify(banner_data)
    except Exception as e:
        logging.error(f"Error in create_banner: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/advanced-editor')
def advanced_editor():
    return render_template('advanced-editor.html')

if __name__ == '__main__':
    app.run(debug=True)