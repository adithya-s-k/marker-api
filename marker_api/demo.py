import os
import base64
import mimetypes
import requests
from PIL import Image
from io import BytesIO
import gradio as gr
# from omniparse.documents import parse_pdf


def fetch_readme_content():
    url = "https://raw.githubusercontent.com/adithya-s-k/marker-api/refs/heads/master/README.md"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching README: {e}")
        return "Failed to load README content. Please check the GitHub repository."


header_markdown = fetch_readme_content()


def decode_base64_to_pil(base64_str):
    return Image.open(BytesIO(base64.b64decode(base64_str)))


parse_document_docs = {
    "curl": """curl -X POST -F "file=@/path/to/document" http://localhost:8000/parse_document""",
    "python": """
    coming soon⌛
    """,
    "javascript": """
    coming soon⌛
    """,
}


def parse_document(input_file_path, parameters, request: gr.Request):
    # Validate file extension
    allowed_extensions = [".pdf", ".ppt", ".pptx", ".doc", ".docx"]
    file_extension = os.path.splitext(input_file_path)[1].lower()
    if file_extension not in allowed_extensions:
        raise gr.Error(f"File type not supported: {file_extension}")
    try:
        host_url = request.headers.get("host")

        post_url = f"http://{host_url}/convert"
        # Determine the MIME type of the file
        mime_type, _ = mimetypes.guess_type(input_file_path)
        if not mime_type:
            mime_type = "application/octet-stream"  # Default MIME type if not found

        with open(input_file_path, "rb") as f:
            files = {"file": (input_file_path, f, mime_type)}
            response = requests.post(
                post_url, files=files, headers={"accept": "application/json"}
            )

        document_response = response.json()

        images = document_response.get("images", [])

        # Decode each base64-encoded image to a PIL image
        pil_images = [
            decode_base64_to_pil(image_dict["image"]) for image_dict in images
        ]

        return (
            str(document_response["text"]),
            gr.Gallery(value=pil_images, visible=True),
            str(document_response["text"]),
            gr.JSON(value=document_response, visible=True),
        )

    except Exception as e:
        raise gr.Error(f"Failed to parse: {e}")


demo_ui = gr.Blocks(theme=gr.themes.Monochrome(radius_size=gr.themes.sizes.radius_none))

with demo_ui:
    gr.Markdown(
        "<h1>Marker-API</h1> \n Easily deployable 🚀 API to convert PDF to markdown quickly with high accuracy."
    )
    gr.Markdown(
        "📄 [Documentation](https://docs.cognitivelab.in/) | ✅ [Follow](https://x.com/adithya_s_k) | 🐈‍⬛ [Github](https://github.com/adithya-s-k/omniparse) | ⭐ [Give a Star](https://github.com/adithya-s-k/omniparse)"
    )
    with gr.Tabs():
        with gr.TabItem("Documents"):
            with gr.Row():
                with gr.Column(scale=80):
                    document_file = gr.File(
                        label="Upload Document",
                        type="filepath",
                        file_count="single",
                        interactive=True,
                        file_types=[".pdf", ".ppt", ".doc", ".pptx", ".docx"],
                    )
                    with gr.Accordion("Parameters", visible=True):
                        document_parameter = gr.Dropdown(
                            [
                                "Fixed Size Chunking",
                                "Regex Chunking",
                                "Semantic Chunking",
                            ],
                            label="Chunking Stratergy",
                        )
                        if document_parameter == "Fixed Size Chunking":
                            document_chunk_size = gr.Number(
                                minimum=250, maximum=10000, step=100, show_label=False
                            )
                            document_overlap_size = gr.Number(
                                minimum=250, maximum=1000, step=100, show_label=False
                            )
                    document_button = gr.Button("Parse Document")
                with gr.Column(scale=200):
                    with gr.Accordion("Markdown"):
                        document_markdown = gr.Markdown()
                    with gr.Accordion("Extracted Images"):
                        document_images = gr.Gallery(visible=False)
                    with gr.Accordion("Chunks", visible=False):
                        document_chunks = gr.Markdown()
            with gr.Accordion("JSON Output"):
                document_json = gr.JSON(label="Output JSON", visible=False)
            with gr.Accordion("Use API", open=True):
                gr.Code(
                    language="shell",
                    value=parse_document_docs["curl"],
                    lines=1,
                    label="Curl",
                )
                gr.Code(
                    language="python", value="Coming Soon⌛", lines=1, label="python"
                )

        gr.Markdown(header_markdown)

    document_button.click(
        fn=parse_document,
        inputs=[document_file, document_parameter],
        outputs=[document_markdown, document_images, document_chunks, document_json],
    )
