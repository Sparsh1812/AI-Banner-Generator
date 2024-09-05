from flask import Flask, request, jsonify
import google.generativeai as genai
from PIL import Image
import io
import base64
import os
import random
import json  
from flask import render_template
import logging



app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


# Predefined templates
TEMPLATES = [
    {
        "objects": [
            {"type":"text","left":721,"top":151,"fontSize":26,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":651,"top":206,"fontSize":36,"fill":"","fontWeight":"italic","fontStyle":"","textAlign":"center","text":""},
            {"type":"image","left":95,"top":128,"width":480,"height":240,"src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":479,"top":36,"fontSize":22,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":407,"top":83,"fontSize":36,"fill":"","fontWeight":"italic","fontStyle":"","textAlign":"center","text":""},
            {"type":"image","left":373,"top":158,"width":480,"height":240,"src":""}
        ]
    },
    {
        "objects": [
            {"type":"text","left":91,"top":126,"width":271.9453125,"height":54.23999999999999,"fontSize":48,"fill":"","fontWeight":"bold","fontStyle":"","textAlign":"left","text":""},
            {"type":"text","left":372,"top":275,"width":254.21875,"height":36.16,"fontSize":22,"fill":"","fontWeight":"","fontStyle":"italic","textAlign":"left","text":""},
            {"type":"image","left":697,"top":119,"width":480,"height":240,"src":""}
        ]
    }
]

def generate_banner(promotion, theme, resolution, color_palette, image_data):
    try:
        template = random.choice(TEMPLATES)
        
        prompt = f"""
        Create a banner design based on the following:
        Template: {template['objects']}
        Promotion: {promotion}
        Theme: {theme}
        Resolution: {resolution}
        Color Palette: {color_palette}

        Provide the following in a JSON format (without any comments):
        {{
            "mainText": "Main text for the promotion (be creative)",
            "secondaryText": "Secondary text (if applicable)",
            "textColors": {{
                "mainText": "Color for main text",
                "secondaryText": "Color for secondary text"
            }}
            # optional: add more properties as needed like font size, font family, tertiary text, etc. make sure the text length aren't too long
        }}
        """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        logging.debug(f"Gemini API response: {response.text}")
        
        design_choices = parse_gemini_response(response.text)
        modified_template = apply_design_choices(template, design_choices, resolution, image_data)
        
        return modified_template
    except Exception as e:
        logging.error(f"Error in generate_banner: {str(e)}")
        raise

def parse_gemini_response(response_text):
    try:
        # Remove any potential markdown formatting
        clean_text = response_text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {str(e)}")
        logging.error(f"Raw response: {response_text}")
        raise ValueError("Invalid JSON response from Gemini API")

def apply_design_choices(template, choices, resolution, image_data):
    for obj in template['objects']:
        if obj['type'] == 'text':
            if 'mainText' in choices and obj['fontSize'] > 35:
                obj['text'] = choices['mainText'] or ""  # Provide a default if empty
                obj['fill'] = choices['textColors'].get('mainText', '#000000')
            elif 'secondaryText' in choices and obj['fontSize'] <= 35:
                obj['text'] = choices['secondaryText'] or ""  # Provide a default if empty
                obj['fill'] = choices['textColors'].get('secondaryText', '#000000')
            
            # Ensure all necessary properties are set
            obj['fontFamily'] = obj.get('fontFamily', 'Arial')
            obj['fontSize'] = obj.get('fontSize', 20)
            obj['fontWeight'] = obj.get('fontWeight', 'normal')
            obj['fontStyle'] = obj.get('fontStyle', 'normal')
            obj['textAlign'] = obj.get('textAlign', 'left')
            
        elif obj['type'] == 'image':
            obj['src'] = f"data:image/jpeg;base64,{image_data}"
    
    width, height = map(int, resolution.split('x'))
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
        image_data = data['image']
        
        banner_data = generate_banner(promotion, theme, resolution, color_palette, image_data)
        # logging.debug(f"Generated banner data: {banner_data}")
        return jsonify(banner_data)
    except Exception as e:
        logging.error(f"Error in create_banner: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)