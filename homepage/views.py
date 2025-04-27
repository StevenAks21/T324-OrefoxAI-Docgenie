import openai
import base64
import fitz  # PyMuPDF
from docx import Document
from PIL import Image
from django.shortcuts import render
from .forms import UploadFileForm
import io

client = openai.OpenAI(api_key="")

def encode_image_base64(image_bytes, file_type):
    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/{file_type};base64,{base64_str}"

def extract_images_from_pdf(file):
    file.seek(0)
    images = []
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            images.append((image_bytes, ext))
    return images

def extract_images_from_docx(file):
    file.seek(0)
    images = []
    doc = Document(file)

    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_bytes = rel.target_part.blob
            ext = rel.target_part.content_type.split('/')[-1]
            images.append((image_bytes, ext))
    return images

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            filename = uploaded_file.name.lower()

            image_payloads = []

            if filename.endswith(('.png', '.jpg', '.jpeg')):
                file_type = filename.split('.')[-1]
                image_bytes = uploaded_file.read()
                image_payloads.append(encode_image_base64(image_bytes, file_type))

            elif filename.endswith('.pdf'):
                extracted_images = extract_images_from_pdf(uploaded_file)
                for img_bytes, img_type in extracted_images:
                    image_payloads.append(encode_image_base64(img_bytes, img_type))

            elif filename.endswith('.docx'):
                extracted_images = extract_images_from_docx(uploaded_file)
                for img_bytes, img_type in extracted_images:
                    image_payloads.append(encode_image_base64(img_bytes, img_type))
            else:
                return render(request, 'result.html', {'output': 'Unsupported file type.'})

            if not image_payloads:
                return render(request, 'result.html', {'output': 'No images found in the file.'})

            message_content = [
                {"type": "text", "text": "Analyze all the attached images carefully."},
            ]

            for img_b64 in image_payloads:
                message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": img_b64
                }
            })


            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": message_content}
                ],
                max_tokens=1500
            )


            gpt_output = response.choices[0].message.content
            print(gpt_output)

            return render(request, 'result.html', {'output': gpt_output})
    
    # ✅ For GET request (or fallback)
    form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})
