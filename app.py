
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
flux_client = Client("black-forest-labs/FLUX.1-schnell")

# Updated templates to support multiple images
TEMPLATES = [
    {
        "objects": [
            {"type":"text","left":"53.92%","top":"36.33%","width":"25.64%","height":"11.00%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"56.52%","top":"50.44%","width":"19.16%","height":"8.98%","fontSize":22,"fill":"s","fontWeight":"","fontStyle":"italic","textAlign":"left","text":""},
            {"type":"image","left":"4.33%","top":"29.33%","width":"40.00%","height":"40.00%","src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":"44.00%","top":"9.50%","width":"9.66%","height":"4.14%","fontSize":22,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"37.58%","top":"16.17%","width":"21.09%","height":"9.05%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"center","text":""},
            {"type":"image","left":"11.67%","top":"43.33%","width":"40.00%","height":"40.00%","src":""},
            {"type":"image","left":"47.00%","top":"43.50%","width":"40.00%","height":"43.33%","src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":"15.91%","top":"44.83%","width":"15.81%","height":"6.78%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"67.11%","top":"78.44%","width":"8.84%","height":"4.14%","fontSize":22,"fill":"s","fontWeight":"","fontStyle":"italic","textAlign":"left","text":""},
            {"type":"image","left":"48.67%","top":"21.77%","width":"45.92%","height":"52.33%","src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":"6.92%","top":"34.00%","width":"33.08%","height":"14.19%","fontSize":22,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"9.42%","top":"48.33%","width":"27.48%","height":"11.79%","fontSize":36,"fill":"s","fontWeight":"bold","fontStyle":"","textAlign":"center","text":""},
            {"type":"image","left":"55.33%","top":"14.00%","width":"40.00%","height":"40.00%","src":""},
            {"type":"image","left":"51.08%","top":"28.00%","width":"40.00%","height":"40.00%","src":""}
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
    for item in template:
        for obj in item['objects']:
            # Update 'left', 'top', 'width', 'height' values
            for key in ['left', 'top', 'width', 'height']:
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

def generate_banner(promotion, theme, resolution, color_palette, image_data_list):
    try:
        updated_templates = round_percentages(TEMPLATES)
        template = random.choice(updated_templates)
       
        width, height = map(int, resolution.split('x'))

        prompt = f"""
        Create a banner design based on the following:
        Template: {template['objects']}
        Promotion: {promotion}
        Theme: {theme}
        Resolution: {width}x{height}
        Color Palette: {color_palette} (background image consists of combination of these colors)

        Provide the following in a JSON format (without any comments):
        {{
            "mainText": "Main text for the promotion (be creative)",
            "secondaryText": "Secondary text (if applicable)",
            "textColors": {{
                "mainText": "Color for main text",
                "secondaryText": "Color for secondary text"
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