import streamlit as st
from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch
import PyPDF2
from summary import NewsSummaryModel
import base64

# Load the fine-tuned model
tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
model = NewsSummaryModel()
model.load_state_dict(torch.load("fine_tuned_model.pth"))


# Function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
        
    return text

# Function to generate summary
def generate_summary(text, tokenizer, model):
    # Tokenize input text
    input_ids = tokenizer.encode(
        text,
        truncation=True,
        return_attention_mask=True,
        add_special_tokens=True,
        return_tensors="pt"
    )

    # Generate summary
    output_ids = model.model.generate(
        input_ids=input_ids,
        max_length=512,
        num_beams=4,
        repetition_penalty=2.5,
        length_penalty=1.0,
        early_stopping=True
    )

    # Decode summary
    summary = tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True
    )

    return summary 

# Main Streamlit app
def main():
    st.title("PDF Summarizer")
    # File upload widget
    uploaded_file = st.file_uploader("Upload PDF")
    
    if uploaded_file is not None:
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(uploaded_file)
        st.subheader("Extracted text:")
        st.write(extracted_text)
        # Button to trigger summarization
        if st.button("Summarize"):
            # Generate summary
            summary = generate_summary(extracted_text, tokenizer, model)
            # Display summary
            st.subheader("Summary:")
            st.write(summary)
            # Button to download summary
            download_button_str = create_download_link(summary, "summary.txt", "Download Summary")
            st.markdown(download_button_str, unsafe_allow_html=True)

# Function to create a download link
def create_download_link(content, filename, link_text):
    encoded_content = content.encode()
    b64 = base64.b64encode(encoded_content).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
    return st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
