from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure Gemini API
API_KEY = "your api key"
genai.configure(api_key=API_KEY)

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    return file

def wait_for_files_active(files):
    """Waits for uploaded files to be ready in Gemini."""
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")

@app.route('/analyze-video', methods=['POST'])
def analyze_video():
    try:
        # Check if a file is provided
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400

        # Save the uploaded file
        video = request.files['video']
        video_path = f"/tmp/{video.filename}"
        video.save(video_path)

        # Upload video to Gemini
        file = [ upload_to_gemini(video_path, mime_type="video/mp4"),
                upload_to_gemini(video_path, mime_type="video/mp4")]

        # Wait for file to be ready
        wait_for_files_active([file])

        # Generate response from Gemini
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config,
        )

        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [file],
                },
            ]
        )

        response = chat_session.send_message("just explain me about this video in 100 lines")
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000)
