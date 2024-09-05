from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
import base64
import os
import random
import json
import logging
from gradio_client import Client

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize FLUX.1 schnell client
flux_client = Client("black-forest-labs/FLUX.1-schnell")

# Updated templates to support multiple images
TEMPLATES = [
    {
        "objects": [
            {"type":"text","left":"10%","top":"10%","fontSize":26,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"10%","top":"20%","fontSize":36,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"center","text":""},
            {"type":"image","left":"50%","top":"10%","src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":"5%","top":"5%","fontSize":22,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"5%","top":"15%","fontSize":36,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"center","text":""},
            {"type":"image","left":"5%","top":"30%","src":""},
            {"type":"image","left":"55%","top":"30%","src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":"10%","top":"10%","fontSize":48,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":"10%","top":"25%","fontSize":22,"fill":"","fontWeight":"","fontStyle":"bold","textAlign":"left","text":""},
            {"type":"image","left":"10%","top":"40%","src":""}
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
    # The result is a path to the generated image
    return result

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def generate_banner(promotion, theme, resolution, color_palette, image_data_list):
    try:
        template = random.choice(TEMPLATES)
        width, height = map(int, resolution.split('x'))

        # Generate background image
        background_image_path = generate_background(theme, color_palette, width, height)[0]
        background_image_base64 = image_to_base64(background_image_path)
        
        
        prompt = f"""
        Create a banner design based on the following:
        Template: {template['objects']}
        Promotion: {promotion}
        Theme: {theme}
        Resolution: {width}x{height}
        Color Palette: {color_palette}

        Provide the following in a JSON format (without any comments):
        {{
            "mainText": "Main text for the promotion (be creative)",
            "secondaryText": "Secondary text (if applicable)",
            "textColors": {{
                "mainText": "Color for main text",
                "secondaryText": "Color for secondary text"
            }},
            "objectPositions": [ (decide based on resolution and design principles)
                {{"type": "text", "left": "10-90%", "top": "10-90%"}},
                {{"type": "text", "left": "10-90%", "top": "10-90%"}},
                {{"type": "image", "left": "10-90%", "top": "10-90%", "width": "based on other factors", "height": "based on other factors"}}
            ]
        }}
        
        Use proper design principles to position and size the objects based on given resolution. Ensure text is readable and images are prominently displayed.
        Percentages for positions should be within the specified ranges. The response should be json only.
        """
        # prompt = f"""
        # Create a banner design based on the following:
        # Template: {template['objects']}
        # Promotion: {promotion}
        # Theme: {theme}
        # Resolution: {width}x{height}
        # Color Palette: {color_palette}

        # Provide the following in a JSON format (without any comments):
        # {{
        #     "mainText": "Main text for the promotion (be creative)",
        #     "secondaryText": "Secondary text (if applicable)",
        #     "textColors": {{
        #         "mainText": "Color for main text",
        #         "secondaryText": "Color for secondary text"
        #     }}
        # }}
        
        # Use proper design principles to position and size the objects based on given resolution. Ensure text is readable and images are prominently displayed.
        # Percentages for positions should be within the specified ranges. The response should be json only.
        # """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        logging.debug(f"Gemini API response: {response.text}")
        
        design_choices = parse_gemini_response(response.text)
        
        modified_template = apply_design_choices(template, design_choices, width, height, image_data_list)        
        
        # Add background image to the template (flux ai generated image)
        template['objects'].insert(0, {
            "type": "image",
            "left": "0%",
            "top": "0%",
            "width": "100%",
            "height": "100%",
            "src": f"data:image/png;base64,{background_image_base64}"
        })
        
        return modified_template
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
    for obj, position in zip(template['objects'], choices['objectPositions']):
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
        
        obj['left'] = position['left']
        obj['top'] = position['top']
        if 'width' in position:
            obj['width'] = position['width']
        if 'height' in position:
            obj['height'] = position['height']
    
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

if __name__ == '__main__':
    app.run(debug=True)

