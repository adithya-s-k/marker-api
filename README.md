# Marker API

> [!IMPORTANT]
>
> Marker API provides a simple endpoint for converting PDF documents to Markdown quickly and accurately. With just one click, you can deploy the Marker API endpoint and start converting PDFs seamlessly.

## Features

- Converts PDF to Markdown.
- Can convert Multiple PDFs at the same time.
- Supports a wide range of documents, including books and scientific papers.
- Supports all languages.
- Removes headers, footers, and other artifacts.
- Formats tables and code blocks.
- Extracts and saves images along with the Markdown.
- Converts most equations to LaTeX.
- Works on GPU, CPU, or MPS.

## Comparison

| Original PDF | Marker-API | PyPDF |
|--------------|------------|-------|
| ![Original PDF](./data/images/original_pdf.png) | ![Marker-API](./data/images/marker_api.png) | ![PyPDF](./data/images/pypdf.png) |

## Installation and Setup

### 🐍 Python

To install Marker API in a Python environment, follow these steps:

1. Clone the Marker API repository from GitHub:

```bash
git clone https://github.com/adithya-s-k/marker-api
```

2. Navigate to the cloned repository directory:

```bash
cd marker-api
```

3. Install the dependencies using the following commands:

`poetry install` or `pip install -e .`

After installation, you can run the server through `marker_api` command 

```bash
marker_api
```

or 
```bash
python server.py
```

### 🛳️ Docker

To use Marker API with Docker, execute the following commands:

1. Pull the Marker API Docker image from Docker Hub:
2. Run the Docker container, exposing port 8000:
 👉🏼[Docker Image](https://hub.docker.com/r/savatar101/marker-api)
```bash
docker pull savatar101/marker-api:0.2
# if you are running on a gpu 
docker run --gpus all -p 8000:8000 savatar101/marker-api:0.2
# else
docker run -p 8000:8000 savatar101/marker-api:0.2
```

Alternatively, if you prefer to build the Docker image locally:
Then, run the Docker container as follows:

```bash
docker build -t marker-api .
# if you are running on a gpu
docker run --gpus all -p 8000:8000 marker-api
# else
docker run -p 8000:8000 marker-api

```

### ✈️ Skypilot
SkyPilot is a framework for running LLMs, AI, and batch jobs on any cloud, offering maximum cost savings, highest GPU availability, and managed execution.
To deploy Marker API using Skypilot on any cloud provider, execute the following command:

```bash
pip install skypilot-nightly[all]

# setup skypilot with the cloud provider our your

sky launch skypilot.yaml
```
please refer to skypilot [documentation](https://skypilot.readthedocs.io/en/latest/docs/index.html) for more information.

## Usage

### Endpoint

- **URL:** `/convert`
- **Method:** `POST`

### Request

- **Body Parameters:**
  - `pdf_file`: The PDF file to be converted. (Type: File)
  - `extract_images` (Optional): Specify whether to extract images from the PDF. Default is `true`. (Type: Boolean)

### Response

- **Success Response:**
  - **Code:** 200 OK
  - **Content:** JSON containing the converted Markdown text, metadata, and optionally extracted image data.

    ```json
    {
        "markdown": "Converted Markdown text...",
        "metadata": {...},
        "images": {
            "image_1": "data:image/png;base64,<base64_encoded_image_data>",
            "image_2": "data:image/png;base64,<base64_encoded_image_data>",
            ...
        }
    }
    ```

  If images are included in the response, they are provided in base64-encoded format. You can use this data to display the images in your application. Additionally, you can use the following Python script [invoke.py](/examples/invoke.py) to invoke the endpoint with a local PDF file and save the images locally

- **Error Response:**
  - **Code:** 415 Unsupported Media Type
  - **Content:** JSON containing error details.

### Invoke Endpoint

#### CURL

```bash
curl -X POST \
  -F "pdf_file=@example.pdf;type=application/pdf" \
  -F "extract_images=true" \
  http://localhost:8000/convert
```

#### Python

Please refer to examples on how to invoke the api and save it as Markdown [Notebook](./examples/invoke.ipynb) , [Script](./examples/invoke.py)

```python
import requests
import os

url = "http://localhost:8000/convert"
pdf_file_path = "example.pdf"
with open(pdf_file_path, 'rb') as pdf_file:
    pdf_content = pdf_file.read()
files = {'pdf_file': (os.path.basename(pdf_file_path), pdf_content, 'application/pdf')}
params = {'extract_images': True}  # Optional parameter
response = requests.post(url, files=files, params=params)

print(response.json())
```

#### JavaScript

```javascript
const fetch = require('node-fetch');
const fs = require('fs');

const url = "http://localhost:8000/convert";
const pdfFilePath = "example.pdf";

fs.readFile(pdfFilePath, (err, pdfContent) => {
    if (err) {
        console.error(err);
        return;
    }

    const formData = new FormData();
    formData.append('pdf_file', new Blob([pdfContent], { type: 'application/pdf' }), pdfFilePath);
    formData.append('extract_images', true); // Optional parameter

    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));
});
```



<details>
<summary><h3>Marker Readme</h3></summary>

Marker converts PDF to markdown quickly and accurately.

- Supports a wide range of documents (optimized for books and scientific papers)
- Supports all languages
- Removes headers/footers/other artifacts
- Formats tables and code blocks
- Extracts and saves images along with the markdown
- Converts most equations to latex
- Works on GPU, CPU, or MPS

## How it works

Marker is a pipeline of deep learning models:

- Extract text, OCR if necessary (heuristics, [surya](https://github.com/VikParuchuri/surya), tesseract)
- Detect page layout and find reading order ([surya](https://github.com/VikParuchuri/surya))
- Clean and format each block (heuristics, [texify](https://github.com/VikParuchuri/texify)
- Combine blocks and postprocess complete text (heuristics, [pdf_postprocessor](https://huggingface.co/vikp/pdf_postprocessor_t5))

It only uses models where necessary, which improves speed and accuracy.

## Examples

| PDF                                                                   | Type        | Marker                                                                                                 | Nougat                                                                                                 |
|-----------------------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [Think Python](https://greenteapress.com/thinkpython/thinkpython.pdf) | Textbook    | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/marker/thinkpython.md)         | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/nougat/thinkpython.md)         |
| [Think OS](https://greenteapress.com/thinkos/thinkos.pdf)             | Textbook    | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/marker/thinkos.md)             | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/nougat/thinkos.md)             |
| [Switch Transformers](https://arxiv.org/pdf/2101.03961.pdf)           | arXiv paper | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/marker/switch_transformers.md) | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/nougat/switch_transformers.md) |
| [Multi-column CNN](https://arxiv.org/pdf/1804.07821.pdf)              | arXiv paper | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/marker/multicolcnn.md)         | [View](https://github.com/VikParuchuri/marker/blob/master/data/examples/nougat/multicolcnn.md)         |

## Performance

![Benchmark overall](data/images/overall.png)

The above results are with marker and nougat setup so they each take ~4GB of VRAM on an A6000.

See [below](#benchmarks) for detailed speed and accuracy benchmarks, and instructions on how to run your own benchmarks.

# Commercial usage

I want marker to be as widely accessible as possible, while still funding my development/training costs.  Research and personal usage is always okay, but there are some restrictions on commercial usage.

The weights for the models are licensed `cc-by-nc-sa-4.0`, but I will waive that for any organization under $5M USD in gross revenue in the most recent 12-month period AND under $5M in lifetime VC/angel funding raised. If you want to remove the GPL license requirements (dual-license) and/or use the weights commercially over the revenue limit, check out the options [here](https://www.datalab.to).

# Community

[Discord](https://discord.gg//KuZwXNGnfH) is where we discuss future development.

# Limitations

PDF is a tricky format, so marker will not always work perfectly.  Here are some known limitations that are on the roadmap to address:

- Marker will not convert 100% of equations to LaTeX.  This is because it has to detect then convert.
- Tables are not always formatted 100% correctly - text can be in the wrong column.
- Whitespace and indentations are not always respected.
- Not all lines/spans will be joined properly.
- This works best on digital PDFs that won't require a lot of OCR.  It's optimized for speed, and limited OCR is used to fix errors.

# Installation

You'll need python 3.9+ and PyTorch.  You may need to install the CPU version of torch first if you're not using a Mac or a GPU machine.  See [here](https://pytorch.org/get-started/locally/) for more details.

Install with:

```shell
pip install marker-pdf
```

## Optional: OCRMyPDF

Only needed if you want to use the optional `ocrmypdf` as the ocr backend.  Note that `ocrmypdf` includes Ghostscript, an AGPL dependency, but calls it via CLI, so it does not trigger the license provisions.

See the instructions [here](docs/install_ocrmypdf.md)

# Usage

First, some configuration:

- Inspect the settings in `marker/settings.py`.  You can override any settings with environment variables.
- Your torch device will be automatically detected, but you can override this.  For example, `TORCH_DEVICE=cuda`.
  - If using GPU, set `INFERENCE_RAM` to your GPU VRAM (per GPU).  For example, if you have 16 GB of VRAM, set `INFERENCE_RAM=16`.
  - Depending on your document types, marker's average memory usage per task can vary slightly.  You can configure `VRAM_PER_TASK` to adjust this if you notice tasks failing with GPU out of memory errors.
- By default, marker will use `surya` for OCR.  Surya is slower on CPU, but more accurate than tesseract.  If you want faster OCR, set `OCR_ENGINE` to `ocrmypdf`. This also requires external dependencies (see above).  If you don't want OCR at all, set `OCR_ENGINE` to `None`.

## Convert a single file

```shell
marker_single /path/to/file.pdf /path/to/output/folder --batch_multiplier 2 --max_pages 10 --langs English
```

- `--batch_multiplier` is how much to multiply default batch sizes by if you have extra VRAM.  Higher numbers will take more VRAM, but process faster.  Set to 2 by default.  The default batch sizes will take ~3GB of VRAM.
- `--max_pages` is the maximum number of pages to process.  Omit this to convert the entire document.
- `--langs` is a comma separated list of the languages in the document, for OCR

Make sure the `DEFAULT_LANG` setting is set appropriately for your document.  The list of supported languages for OCR is [here](https://github.com/VikParuchuri/surya/blob/master/surya/languages.py).  If you need more languages, you can use any language supported by [Tesseract](https://tesseract-ocr.github.io/tessdoc/Data-Files#data-files-for-version-400-november-29-2016) if you set `OCR_ENGINE` to `ocrmypdf`.  If you don't need OCR, marker can work with any language.

## Convert multiple files

```shell
marker /path/to/input/folder /path/to/output/folder --workers 10 --max 10 --metadata_file /path/to/metadata.json --min_length 10000
```

- `--workers` is the number of pdfs to convert at once.  This is set to 1 by default, but you can increase it to increase throughput, at the cost of more CPU/GPU usage. Parallelism will not increase beyond `INFERENCE_RAM / VRAM_PER_TASK` if you're using GPU.
- `--max` is the maximum number of pdfs to convert.  Omit this to convert all pdfs in the folder.
- `--min_length` is the minimum number of characters that need to be extracted from a pdf before it will be considered for processing.  If you're processing a lot of pdfs, I recommend setting this to avoid OCRing pdfs that are mostly images. (slows everything down)
- `--metadata_file` is an optional path to a json file with metadata about the pdfs.  If you provide it, it will be used to set the language for each pdf.  If not, `DEFAULT_LANG` will be used. The format is:

```
{
  "pdf1.pdf": {"languages": ["English"]},
  "pdf2.pdf": {"languages": ["Spanish", "Russian"]},
  ...
}
```

You can use language names or codes.  The exact codes depend on the OCR engine.  See [here](https://github.com/VikParuchuri/surya/blob/master/surya/languages.py) for a full list for surya codes, and [here](https://tesseract-ocr.github.io/tessdoc/Data-Files#data-files-for-version-400-november-29-2016) for tesseract.

## Convert multiple files on multiple GPUs

```shell
MIN_LENGTH=10000 METADATA_FILE=../pdf_meta.json NUM_DEVICES=4 NUM_WORKERS=15 marker_chunk_convert ../pdf_in ../md_out
```

- `METADATA_FILE` is an optional path to a json file with metadata about the pdfs.  See above for the format.
- `NUM_DEVICES` is the number of GPUs to use.  Should be `2` or greater.
- `NUM_WORKERS` is the number of parallel processes to run on each GPU.  Per-GPU parallelism will not increase beyond `INFERENCE_RAM / VRAM_PER_TASK`.
- `MIN_LENGTH` is the minimum number of characters that need to be extracted from a pdf before it will be considered for processing.  If you're processing a lot of pdfs, I recommend setting this to avoid OCRing pdfs that are mostly images. (slows everything down)

Note that the env variables above are specific to this script, and cannot be set in `local.env`.

# Troubleshooting

There are some settings that you may find useful if things aren't working the way you expect:

- `OCR_ALL_PAGES` - set this to true to force OCR all pages.  This can be very useful if the table layouts aren't recognized properly by default, or if there is garbled text.
- `TORCH_DEVICE` - set this to force marker to use a given torch device for inference.
- `OCR_ENGINE` - can set this to `surya` or `ocrmypdf`.
- `DEBUG` - setting this to `True` shows ray logs when converting multiple pdfs
- Verify that you set the languages correctly, or passed in a metadata file.
- If you're getting out of memory errors, decrease worker count (increased the `VRAM_PER_TASK` setting).  You can also try splitting up long PDFs into multiple files.

In general, if output is not what you expect, trying to OCR the PDF is a good first step.  Not all PDFs have good text/bboxes embedded in them.

# Benchmarks

Benchmarking PDF extraction quality is hard.  I've created a test set by finding books and scientific papers that have a pdf version and a latex source.  I convert the latex to text, and compare the reference to the output of text extraction methods.  It's noisy, but at least directionally correct.

Benchmarks show that marker is 4x faster than nougat, and more accurate outside arXiv (nougat was trained on arXiv data).  We show naive text extraction (pulling text out of the pdf with no processing) for comparison.

**Speed**

| Method | Average Score | Time per page | Time per document |
|--------|---------------|---------------|-------------------|
| marker | 0.613721      | 0.631991      | 58.1432           |
| nougat | 0.406603      | 2.59702       | 238.926           |

**Accuracy**

First 3 are non-arXiv books, last 3 are arXiv papers.

| Method | multicolcnn.pdf | switch_trans.pdf | thinkpython.pdf | thinkos.pdf | thinkdsp.pdf | crowd.pdf |
|--------|-----------------|------------------|-----------------|-------------|--------------|-----------|
| marker | 0.536176        | 0.516833         | 0.70515         | 0.710657    | 0.690042     | 0.523467  |
| nougat | 0.44009         | 0.588973         | 0.322706        | 0.401342    | 0.160842     | 0.525663  |

Peak GPU memory usage during the benchmark is `4.2GB` for nougat, and `4.1GB` for marker.  Benchmarks were run on an A6000 Ada.

**Throughput**

Marker takes about 4.5GB of VRAM on average per task, so you can convert 10 documents in parallel on an A6000.

![Benchmark results](data/images/per_doc.png)

## Running your own benchmarks

You can benchmark the performance of marker on your machine. Install marker manually with:

```shell
git clone https://github.com/VikParuchuri/marker.git
poetry install
```

Download the benchmark data [here](https://drive.google.com/file/d/1ZSeWDo2g1y0BRLT7KnbmytV2bjWARWba/view?usp=sharing) and unzip. Then run `benchmark.py` like this:

```shell
python benchmark.py data/pdfs data/references report.json --nougat
```

This will benchmark marker against other text extraction methods.  It sets up batch sizes for nougat and marker to use a similar amount of GPU RAM for each.

Omit `--nougat` to exclude nougat from the benchmark.  I don't recommend running nougat on CPU, since it is very slow.

# Thanks

This work would not have been possible without amazing open source models and datasets, including (but not limited to):

- Surya
- Texify
- Pypdfium2/pdfium
- DocLayNet from IBM
- ByT5 from Google

Thank you to the authors of these models and datasets for making them available to the community!

</details>

## To Do

- [x] Create server
- [x] Add support for single PDF upload
- [x] Add support for multi PDF upload
- [x] Docker support and Skypilot support
- [ ] Implement handling for multiple PDF uploads simultaneously.
- [ ] Live update API on progress of conversion
- [ ] Enhance GPU utilization and optimize performance for efficient processing.
- [ ] Introduce a toggle mode to generate Markdown without including images in the output.
- [ ] Implement dynamic adjustment of batch size based on available VRAM.

## Throughput Benchmarks

Updates on throughput benchmarks will be available soon.

## Acknowledgements

This project is built on top of the remarkable [marker](https://github.com/VikParuchuri/marker) project created by [VikParuchuri](https://twitter.com/VikParuchuri). We express our gratitude for the inspiration and foundation provided by this project.

<p align="center">
  <a href="https://adithyask.com">
    <img src="https://api.star-history.com/svg?repos=adithya-s-k/marker-api&type=Date" alt="Star History Chart">
  </a>
</p>
