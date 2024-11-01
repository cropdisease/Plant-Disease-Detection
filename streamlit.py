import streamlit as st
import requests
from PIL import Image
import numpy as np
import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile
import logging
import textwrap
from streamlit_modal import Modal
from email.mime.multipart import MIMEMultipart
from email.mime.text  import MIMEText
import smtplib
import datetime
time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Tawk.to widget code
tawk_to_code = """
<!--Start of Tawk.to Script-->
<script type="text/javascript">
var Tawk_API=Tawk_API||{}, Tawk_LoadStart=new Date();
(function(){
var s1=document.createElement("script"),s0=document.getElementsByTagName("script")[0];
s1.async=true;
s1.src='https://embed.tawk.to/6712958c4304e3196ad3dbf8/1iag9gben';
s1.charset='UTF-8';
s1.setAttribute('crossorigin','*');
s0.parentNode.insertBefore(s1,s0);
})();
</script>
<!--End of Tawk.to Script-->
"""
css_code = """
<style>
  #tawk-widget {
    position: fixed;
    bottom: 0;
    right: 0;
  }
</style>
"""

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

if 'image' not in st.session_state:
    st.session_state.image = None
if 'prediction' not in st.session_state:
    st.session_state.prediction = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = []
if 'show_results' not in st.session_state:
    st.session_state.show_results = False

languages = ["EN", "FR"]

query_lang = st.query_params.get("lang", ["EN"])[0]

if query_lang not in languages:
    selected_lang = "EN"  
else:
    selected_lang = query_lang


with open('translations.json', 'r', encoding='utf-8') as f:
    translations=json.load(f)


texts=translations[selected_lang]
opposite_lang=languages[1] if selected_lang == languages[0] else languages[0]
selected_lang=st.sidebar.radio(texts["select_language"], [selected_lang, opposite_lang], index=0)

texts=translations[selected_lang]

st.query_params={"lang": selected_lang}


pages = [
    texts["home_page"],
    texts["community_sharing"]
]
page = st.sidebar.selectbox(texts["select_page"], pages)
if page == texts["home_page"]:
    def create_pdf(file_path, prediction, recommendations, image):
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter
        if image:
            img = Image.open(image)  
            
            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                img.save(temp_file.name)  
                img_size = 150  
                x = (width - img_size) / 2  
                c.drawImage(temp_file.name, x, height - img_size - 30, width=img_size, height=img_size)  
                c.translate(0, -img_size - 10)  

        # Title
        c.setFont("Helvetica-Bold", 15)
        c.drawString(100, height - 170, "Predicted Crop Disease Report")
        
        # Predicted disease
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 190, f"The predicted disease is: {prediction}")
        
        # Recommendations
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, height - 210, "Recommendations:")
        y = height - 230
        c.setFont("Helvetica", 12)  
        for rec in recommendations:
            wrapped_rec = textwrap.fill(f"✅ {rec}", width=70)
            for line in wrapped_rec.split('\n'):
                c.drawString(100, y, line)
                y -= 20 
                if y < 50: 
                    c.showPage()
                    y = height - 50 
        c.save()
    image=None


    st.title(texts["title"])
    st.write(texts["upload_image"])

    option = st.selectbox(texts["choose_image"], (texts["upload"], texts["capture"]))

    if option == texts["upload"]:
        uploaded_file = st.file_uploader(texts["choose"], type=["jpg", "jpeg", "png"])
        if uploaded_file:
            st.session_state.image  = Image.open(uploaded_file)
            st.image (st.session_state.image , caption=texts['uploaded_image'], use_column_width=True)

    elif option == texts["capture"]:
        camera_image = st.camera_input(texts["capture"])
        if camera_image is not None:
            st.session_state.image  = Image.open(camera_image)
            st.image (st.session_state.image , caption=texts['captured_image'], use_column_width=True)
    if st.button(texts["predict"]):
        if st.session_state.image is not None:
            with st.spinner(texts["spinner"]):
                image_bytes = io.BytesIO()
                st.session_state.image.save(image_bytes, format='JPEG')
                image_bytes.seek(0)
                files = {"file": image_bytes}
                try:
                    response = requests.post(f"http://localhost:5000/predict/{selected_lang}", files=files)
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.prediction = result.get("prediction", texts["unknown"])
                        st.session_state.recommendations = result.get("recommendations", [texts["consult_expert"]])

                        st.session_state.show_results = True
                        pdf_file_path = f"{texts["crop_disease_report"]}_{st.session_state.prediction}.pdf"
                        create_pdf(pdf_file_path, st.session_state.prediction, st.session_state.recommendations, image_bytes)
                        with open(pdf_file_path, "rb") as pdf_file:
                            st.session_state.pdf_byte = pdf_file.read()                      
                    else:
                        st.error(texts["error"])
                        compose_email(texts["error"])
                except Exception as e:
                    st.error(texts["error"])
                    compose_email(f"{texts["error"]}\n\n{e}")
                    print(e)
        else:
            st.warning(texts["warning"])
    if st.session_state.show_results:
        if st.session_state.prediction is not None:
            st.write(f"**{texts['prediction']}**: {st.session_state.prediction}")

        if st.session_state.recommendations:
            st.write(f"**{texts['recommendations']}:**")
            for rec in st.session_state.recommendations:
                st.write(f"✅ {rec}")
        if st.session_state.pdf_byte is not None:
            st.download_button(texts["download_pdf_report"], data=st.session_state.pdf_byte, file_name="crop_disease_report.pdf", mime="application/pdf", key='session')


        def submit_feedback(feedback_text, crop_name, feedback_rating, include_image):
            feedback_data = {
                "prediction": st.session_state.prediction,
                "crop": crop_name,
                "feedback_text": feedback_text,
                "feedback_rating": feedback_rating,
                "include_image": include_image,
                "lang": selected_lang
            }
            files = {}
            if include_image and st.session_state.image is not None:
                try:
                    image_bytes = io.BytesIO()
                    st.session_state.image.save(image_bytes, format='JPEG')
                    image_bytes.seek(0)
                    files = {"file": ("image.jpg", image_bytes.read(), "image/jpeg")}
                except Exception as e:
                    st.error(texts["image_error"])
                    print(e)
                    compose_email(f"{texts["image_error"]}\n\n{e}")

            feedback_data['json_data'] = json.dumps(feedback_data)
            try:
                response = requests.post("http://localhost:5000/feedback", data=feedback_data, files=files)
                if response.status_code == 200:
                    st.success(texts["thank_you"])
                else:
                    st.error(texts["submit_error"])
                    compose_email(texts["submit_error"])
            except requests.exceptions.RequestException as e:
                st.error(texts["feedback_processing_error"])
                compose_email(f"{texts["feedback_processing_error"]}\n\n{e}")    
                print(e)

        modal = Modal(texts["title"], key=texts["modal_key"])

        # Button to open the modal
        open_modal = st.button(texts["open_button"])
        if open_modal:
            modal.open()

        # Check if the modal is open
        if modal.is_open():
            with modal.container():
                # Add your feedback form content here
                st.subheader(texts["subheader"])
                crop_name=st.text_input(texts["crop_name"])
                feedback_text = st.text_area(texts["feedback_text"])
                feedback_rating = st.slider(texts["feedback_rating"], 0, 5, 3)
                include_image = st.checkbox(texts["include_image"])
                
                # Button to submit the feedback
                if st.button(texts["submit_button"]):
                    if feedback_text:
                        submit_feedback(feedback_text, crop_name, feedback_rating, include_image)
                        modal.close()
                    else:
                        st.warning(texts["feedback_warning"])
    st.components.v1.html(tawk_to_code + css_code, height=200, width=800)
elif page == texts["community_sharing"]:
    st.title(texts["community_sharing"])
    response = requests.get("http://localhost:5000/get_posts")
    
    if response.status_code == 200:
        posts = response.json()
        for post in posts:
            st.write(f"**{post['text']}**")
            if post["image"]:
                st.image(post["image"], use_column_width=False, width=150) 
            st.write(f"{texts['likes']}: **{post['likes']}**")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(texts["like_button"], key=f"like_{post['id']}"):
                    requests.post(f"http://localhost:5000/like_post/{post['id']}")
                    st.rerun()
            st.write(f"**{texts['comments']}**")
            for comment in post["comments"]:
                st.write(f"- {comment}")
            
            with col2:
                comment= st.text_input(texts["comment_input"], key=f"comment_input_{post['id']}")
                if st.button(texts["submit_comment"], key=f"submit_comment_{post['id']}"):
                    comment_data ={"comment": comment}
                    response =requests.post(f"http://localhost:5000/comment_post/{post['id']}", data=comment_data)
                    if response.status_code == 200:
                        st.success(texts["comment_added_success"])
                        st.rerun()
                    else:
                        st.error(texts["comment_added_failed"])
                        compose_email(texts["comment_added_failed"])
            st.markdown("---")
    
    with st.form(key='post_form'):
        post_text= st.text_area(texts["share_experience"])
        post_image=st.file_uploader(texts["upload_picture"], type=["jpg", "jpeg", "png"])
        submit_button =st.form_submit_button(label=texts["post_button"])
    
    if submit_button:
        post_data ={"text": post_text}
        files ={}
        if post_image:
            files ={"image": post_image}
        response =requests.post("http://localhost:5000/create_post", data=post_data, files=files)
        if response.status_code == 200:
            st.success(texts["post_shared_success"])
            st.rerun()
    st.components.v1.html(tawk_to_code + css_code, height=600, width=800)
