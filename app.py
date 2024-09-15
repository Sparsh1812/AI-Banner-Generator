
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

from flask_cors import CORS


app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Enable CORS for all routes and origins
CORS(app)

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize FLUX.1 schnell client
# HF_TOKEN = os.environ.get("HF_TOKEN")

# flux_client = Client.duplicate("black-forest-labs/FLUX.1-schnell", hf_token=HF_TOKEN)
flux_client = Client("black-forest-labs/FLUX.1-schnell")
# flux_client = Client("ChristianHappy/FLUX.1-schnell")

# Updated templates to support multiple images
TEMPLATES = [
    # templates for 1360x800 resolution
    {
        "resolution": "1360x800",
        "num_images": 1,    
        "objects": [
            {"type":"text","left":"6.00%","bottom":"55.89%","width":"100%","height":"100%","fontSize":22,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"6.00%","bottom":"36.91%","width":"100%","height":"100%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"normal","textAlign":"center","text":""},
            {"type":"image","left":"70.42%","bottom":"15.46%","width":"50%","height":"50%","src":""},
        ]
    },
    {
        "resolution": "1360x800",
        "num_images": 2,    
        "objects": [
            {"type":"text","left":"6.00%","bottom":"55.89%","width":"100%","height":"100%","fontSize":22,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"6.00%","bottom":"36.91%","width":"100%","height":"100%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"normal","textAlign":"center","text":""},
            {"type":"image","left":"60.42%","bottom":"15.57%","width":"50%","height":"50%","src":""},
            {"type":"image","left":"70.42%","bottom":"15.46%","width":"50%","height":"50%","src":""},
        ]
    },
    {
        "resolution": "1360x800",
        "num_images": 3,    
        "objects": [
            {"type":"text","left":"6.00%","bottom":"55.89%","width":"100%","height":"100%","fontSize":22,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"6.00%","bottom":"36.91%","width":"100%","height":"100%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"normal","textAlign":"center","text":""},
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

def calculate_responsive_position(element_type, index, total_elements, width, height):
    if element_type == "text":
        return {
            "left": f"{20 + (index * 30)}%",
            "top": f"{20 + (index * 20)}%",
            "width": f"{min(60, 100 - (20 + (index * 30)))}%",
            "height": "auto"
        }
    elif element_type == "image":
        image_width = min(40, 90 / total_elements)
        return {
            "left": f"{10 + (index * (image_width + 5))}%",
            "top": "30%",
            "width": f"{image_width}%",
            "height": f"{image_width * (height / width)}%"
        }
    
def apply_responsive_design(template, width, height):
    text_elements = [obj for obj in template["objects"] if obj["type"] == "text"]
    image_elements = [obj for obj in template["objects"] if obj["type"] == "image"]
    
    for i, element in enumerate(text_elements):
        element.update(calculate_responsive_position("text", i, len(text_elements), width, height))
        element["fontSize"] = max(12, min(36, int(height * 0.05)))  # Responsive font size
    
    for i, element in enumerate(image_elements):
        element.update(calculate_responsive_position("image", i, len(image_elements), width, height))
    
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
    try:
        num_images = len(image_data_list)
        print("Number of images: ", num_images)
        selected_template = select_template(resolution, num_images)
        print("Selected template: ", selected_template)
        template = round_percentages(selected_template.copy())
        print("Rounded template: ", template)
       
        width, height = map(int, resolution.split('x'))

        prompt = f"""
        Create a banner design based on the following:
        Template: {template['objects']}
        Promotion: {promotion}
        Theme: {theme}
        Resolution: {width}x{height}
        Color Palette (background image): {color_palette} (background image consists of combination of these colors)

        Provide the following in a JSON format (without any comments):
        {{
            "mainText": "Main text for the promotion (be creative, smaller than secondary text, should have promotion message)", 
            "secondaryText": "Secondary text (if applicable)", (should be less than 8 words)
            "textColors": {{
                "mainText": "Color for main text", (should look good on the background colors)
                "secondaryText": "Color for secondary text" (should look good on the background colors)
            }},
            "objectPositions": [ # don't add src for image objects
                {{"type": "text", "left": "10-90%", "top": "10-90%"}},
                {{"type": "text", "left": "10-90%", "top": "10-90%"}},
                {{"type": "image", "left": "10-90%", "top": "10-90%", "width": "20-80%", "height": "20-80%"}}
            ]
        }}

        Use proper design principles to position and size the objects based on given resolution. Ensure text is readable and images are prominently displayed.
        Percentages for positions should be within the specified ranges. The response should be json only.
        """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        logging.debug(f"Gemini API response: {response.text}")

        design_choices = parse_gemini_response(response.text)

                # Apply design choices and responsive design
        modified_template = apply_design_choices(template, design_choices, width, height, image_data_list)
        # responsive_template = apply_responsive_design(modified_template, width, height)

        # Generate background image
        background_image_path = generate_background(theme, color_palette, width, height)[0]
        background_image_base64 = image_to_base64(background_image_path)
        # responsive_template['objects'].insert(0, {
        #     "type": "image",
        #     "left": "0%",
        #     "top": "0%",
        #     "width": "100%",
        #     "height": "100%",
        #     "src": f"data:image/png;base64,{background_image_base64}"
        # })
        # modified_template = apply_design_choices(template, design_choices, width, height, image_data_list)

        # Add background image to the template (flux ai generated image)
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

def apply_design_choices(template, choices, width, height, image_data_list):
    image_index = 0
    for i, (obj, position) in enumerate(zip(template['objects'], choices['objectPositions'])):
        if obj['type'] == 'text':
            if 'mainText' in choices and obj['fontSize'] > 35:
                obj['text'] = choices['mainText'] or ""
                obj['fill'] = choices['textColors'].get('mainText', '#000000')
            elif 'secondaryText' in choices and obj['fontSize'] <= 35:
                obj['text'] = choices['secondaryText'] or ""
                obj['fill'] = choices['textColors'].get('secondaryText', '#000000')

            obj['fontFamily'] = obj.get('fontFamily', 'Arial')
            obj['fontSize'] = obj.get('fontSize', 20)
            obj['fontWeight'] = obj.get('fontWeight', 'normal')
            obj['fontStyle'] = obj.get('fontStyle', 'normal')
            obj['textAlign'] = obj.get('textAlign', 'left')

        elif obj['type'] == 'image' and image_index < len(image_data_list):
            obj['src'] = f"data:image/jpeg;base64,{image_data_list[image_index]}"
            image_index += 1


        # Update position values using Gemini response
        # obj['left'] = position['left']
        # obj['top'] = position['top']
        # if 'width' in position:
        #     obj['width'] = position['width']
        # if 'height' in position:
        #     obj['height'] = position['height']

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