## How this works:
This Flask app dynamically generates image banners based on user-provided themes, color palettes, and target resolutions. It leverages the **Gemini** large language model (LLM) for text-based tasks and utilizes the **Flux** model for image generation. Here's a detailed breakdown of its system design:

1. **Template Management:**
    - The app maintains a predefined set of `TEMPLATES` (stored as a list of dictionaries), where each dictionary represents a template layout for banners. These templates define object placements, including text and images, for a variety of target resolutions and image counts. Each template acts as a blueprint that ensures consistency in design while offering flexibility for different layout needs.
    - The `select_template` function is responsible for selecting the most appropriate template based on the user's requested resolution and the number of images to be displayed. It searches for an exact match but may fallback to a closest match or dynamically generate one if no perfect template is available, ensuring adaptability.
    - The `round_percentages` function is used to fine-tune the selected template by adjusting percentage-based dimensions (like width, height, or margins) to the nearest integer. This step ensures pixel-perfect alignment of elements, avoiding any rendering inaccuracies across different screen resolutions.

2. **LLM-powered Template Generation:**
    - When a suitable template is not found from the predefined list, the app dynamically generates one using the Gemini API through the `generate_template_with_gemini` function.
    - This function employs a few-shot prompting technique, where it provides the Gemini LLM with input parameters `resolution` and `num_images` and their corresponding desired JSON output (template structures). This enables the LLM to understand the pattern and format expected for template generation.
    - The `parse_gemini_response` function is used to handle the JSON output, ensuring proper formatting and error handling,. This function is crucial for converting the raw LLM-generated JSON into a usable template that can be further processed by the app for image rendering.

3. **Background Image Generation:**
    - The `generate_background` function is responsible for creating dynamic backgrounds for image banners. It accepts the following input parameters:
        - **theme:** A user-defined theme that guides the visual style of the background.
        - **color palette:** A set of colors that dictate the overall color scheme of the background, ensuring it aligns with the banner's design.
        - **canvas width and height:** These define the dimensions of the canvas where the background image will be applied, ensuring the background is generated at the correct resolution.
    - The function constructs a prompt for the Flux image generation model, specifically `Flux-1-schnell`, based on the theme and color palette. This prompt specifies the  details required to generate a background image that fits the provided input.

    - The Flux image generation model is invoked with the constructed prompt, along with other parameters, ensuring that the output matches the desired design.

    - Finally, the generated background image is returned to be used within the banner creation process. The flexibility in input allows the background to match the overall theme, color scheme, and dimensions of the final banner.


4. **Gemini API Integration:**
    - The `generate_banner` function utilizes the Gemini API to generate textual and color information for the banner design.
    - It constructs a prompt that includes the generated template from step 2, the promotion details, theme, resolution, the base64 encoded background image from step 3, and the base64 encoded product images from the input.
    - The Gemini API response, which is expected to be in JSON format, contains descriptions for the background image, a list of hex color values present in the background image, a comma-separated list of product names, the main promotional text, optional secondary text, and hex color values for both main and secondary text.
    - Robust error handling (e.g., `try-except` blocks) is implemented to manage potential issues with the API response or JSON parsing.  The function likely checks for valid JSON structure and handles cases where the API call fails or returns unexpected data.
    - The extracted textual and color information from the Gemini API response is then used to finalize the banner design, integrating it with the background and product images.  This likely involves using image manipulation libraries (like Pillow) to overlay text onto the image.
    - 
5. **Image Encoding:**
    -The `image_to_base64` function is responsible for converting the generated background image into a base64 encoded string. This process is essential when the image needs to be transmitted as part of a larger data structure (like JSON) or embedded directly into HTML for efficient web delivery.

This design allows for flexible banner creation, adapting to various resolutions and image counts. The use of an LLM for template generation adds a layer of automation and adaptability, reducing the need for manually defined templates. The image generation component (Flux or similar) provides the visual content based on user-provided themes and colors.
