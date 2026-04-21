# Portfolio

Course and project work collected in this repository.

## Assignment 1 (`a1/`)

**Neural Image Classifier — Oxford-IIIT Pets**  
A Jupyter notebook that trains a **SimpleCNN** on the [Oxford-IIIT Pet Dataset](https://www.robots.ox.ac.uk/~vgg/data/pets/) (37 breed classes). It compares ten training configurations (learning rate, epochs, dropout, batch size) and reports accuracy and loss.

| Path | Description |
|------|-------------|
| [`a1/Neural_Image_Classifier_Annotated.ipynb`](a1/Neural_Image_Classifier_Annotated.ipynb) | Annotated notebook with experiment log and results |

### Run locally

1. Python 3.9+ recommended  
2. Install dependencies: `pip install torch torchvision jupyter` (or use a `requirements.txt` if you add one)  
3. Open the notebook: `jupyter notebook a1/Neural_Image_Classifier_Annotated.ipynb`  
4. First run downloads the dataset into `./data` relative to the notebook’s working directory.

GPU optional; the notebook falls back to CPU.
