from flask import Flask, request, jsonify
import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np
import io
import uuid
import os
import logging
import json
from PIL import Image
from flask_caching import Cache
from email.mime.multipart import MIMEMultipart
from email.mime.text  import MIMEText
import smtplib
import datetime
time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

POSTS_FILE="posts.json"
# Ensure posts.json exists
if not os.path.exists(POSTS_FILE):
    with open("posts.json", 'w') as f:
        json.dump({"posts": []}, f)

# Load posts
def load_posts():
    with open("posts.json", 'r') as f:
        return json.load(f)

# Save posts
def save_posts(data):
    with open("posts.json", 'w') as f:
        json.dump(data, f, indent=4)

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(lineno)s)',
                    handlers=[logging.FileHandler("app.log"),
                              logging.StreamHandler()])

#Function to send an email to me if any error
def compose_email(error_msg):
        global Server, Port, From, Pass, To, msg
        Server='smtp.gmail.com'#smtp server for gmail 
        Port=587 #Tsl port
        From='cropdiseasedetectionsystem@gmail.com'
        To='cropdiseasedetectionsystem@gmail.com'
        Pass='hjkl isea yuia fbfn'#smtp password for the google account
        msg=MIMEMultipart() 
        msg['Subject']=f'Error message from Plant detection API {time}' #Email subject
        msg['From']=From
        msg['To']=To
        msg.attach(MIMEText(error_msg)) #attaching content in the form of a website
        try:
            server=smtplib.SMTP(Server,Port)
            server.set_debuglevel(1) # 1 for debuging and 0 for no debuging
            server.ehlo()
            server.starttls() #encrypt message
            server.login(From, Pass)
            server.sendmail(From,To, msg.as_string())
            logging.info("Error email sent.")
        except:
            logging.error("Failed to send error email", exc_info=True)
        server.quit

app = Flask(__name__)
cache=Cache(app, config={'CACHE_TYPE': 'simple'})

# Load trained model
model=load_model('model.keras')
def translate(lang):
    with open(f'{lang}_recommendations.json', 'r') as f:
        return json.load(f) 

# Function to process image for the model
def preprocess_image(image_data):
    image= tf.keras.preprocessing.image.load_img(io.BytesIO(image_data), target_size=(128, 128))
    input_arr=tf.keras.preprocessing.image.img_to_array(image) 
    return np.array([input_arr])

@app.route('/predict/<language>', methods=['POST'])
@cache.cached(timeout=60)
def predict(language):
    try:
        recommendations = translate(language)
    except FileNotFoundError:
        compose_email(f"error: Language data not found")
        return jsonify({"error": "Language data not found"}), 404
    try:
        logging.info("File received")
        file = request.files.get('file')
        image = file.read()
        processed_image = preprocess_image(image)
        prediction = model.predict(processed_image)
        result_index = np.argmax(prediction)
        model_prediction = list(recommendations.keys())[result_index]
        model_recommendations = recommendations.get(model_prediction)
        return jsonify({'prediction': model_prediction, 'recommendations': model_recommendations})
    except Exception as e:
        error_message = f"Error during prediction: {str(e)}"
        logging.error(error_message, exc_info=True)
        compose_email(error_message)
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict() 
            json_data = data.get('json_data')  
            if json_data:
                data.update(json.loads(json_data)) 
        else:
            compose_email(f'error: Content-Type must be multipart/form-data')
            return jsonify({'error': 'Content-Type must be multipart/form-data'}), 415
        image_name = None
        if data.get('include_image') and 'file' in request.files:
            image = request.files['file']  
            if image:
                image_name = f"{uuid.uuid4()}.jpg" 
                image.save(os.path.join('feedback_images', image_name)) 

        # Create a feedback entry
        feedback_entry = {
            'prediction': data['prediction'],
            'feedback_text': data['feedback_text'],
            'feedback_rating': data['feedback_rating'],
            'image_name': image_name,
            'lang': data['lang']
        }

        # Save feedback to a JSON file
        with open('feedback.json', 'a') as f:
            json.dump(feedback_entry, f)
            f.write('\n') 
        return jsonify({'message': 'Feedback received'}), 200
    except Exception as e:
        compose_email(f"Error receiving feedback: {str(e)}")
        logging.error(f"Error receiving feedback: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Create a new post
@app.route('/create_post', methods=['POST'])
def create_post():
    text = request.form.get('text')
    image = request.files.get('image')
    if text is None:
        return jsonify({"error": "Text is required"}), 400
    post = {"id": len(load_posts()["posts"]) + 1, "text": text, "image": None, "likes": 0, "comments": []}
    if image:
        image_path = f"uploads/{image.filename}"
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)
        post["image"] = image_path

    posts_data = load_posts()
    posts_data["posts"].append(post)
    save_posts(posts_data)

    return jsonify(post), 200

@app.route('/get_posts', methods=['GET'])
def get_posts():
    posts_data = load_posts()
    return jsonify(posts_data["posts"]), 200
# Like a post
@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    posts_data = load_posts()
    for post in posts_data["posts"]:
        if post["id"] == post_id:
            post["likes"] += 1
            save_posts(posts_data)
            return jsonify(post), 200
    compose_email(f"Error: Post not found")
    return jsonify({"error": "Post not found"}), 404
# Comment on a post
@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    posts_data = load_posts()
    comment = request.form.get('comment')  # Ensure the form key matches
    print(f"Received comment: {comment}")
    for post in posts_data["posts"]:
        if post["id"] == post_id:
            if comment:
                post["comments"].append(comment)
                save_posts(posts_data)
                return jsonify(post), 200
            return jsonify({"error": "Comment is required"}), 400
    compose_email(f"Error: Post not found")
    return jsonify({"error": "Post not found"}), 404





if __name__ == '__main__':
    app.run(debug=True)





