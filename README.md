[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-24ddc0f5d75046c5622901739e7c5dd533143b0c8e959d652212380cedb1ea36.svg)](https://classroom.github.com/a/q9wGcN9U)
# CD 2023 Project

Here we have a sample code that loads one mp3 file and splits it 
into 4 tracks: vocals, drums, bass and other.

The codes uses one library named [demucs](https://github.com/facebookresearch/demucs),
this library uses a deep learning model to separate the tracks.
This library requires [ffmpeg](https://ffmpeg.org/) to work.
It should be present in most Linux distributions.

## Dependencies

For Ubuntu (and other debian based linux), run the following commands:

```bash
sudo apt install ffmpeg
```

## Setup

Run the following commands to setup the environement:
```bash
mkdir tracks

python3 -m venv venv
source venv/bin/activate

pip install pip --upgrade
pip install -r requirements_torch.txt
pip install -r requirements_demucs.txt
```

It is important to install the requirements following the previous instructions.
By default, PyTorch will install the CUDA version of the library (over 4G simple from the virtual environment).
As such, the current instructions force the installation of the CPU version of PyTorch and then installs Demucs.


## Usage

The sample main code only requires two parameters:
- **i** the mp3 file used for input
- **o** the folder for the output

Two audio tracks are given (download them from [here](https://filesender.fccn.pt/?s=download&token=cd4fcd29-b3f1-4a4d-9da3-50aae00e702d)):
- **test.mp3** a short sample (0:34) that allows for a quick validation
- **mudic.mp3** a long (59:04) sequence of royalty free rock musics that are the target of the work

Both audio files are royalty free.

To run test the sample code simple run:
```bash
python main.py -i test.mp3
```


## A uthors
 
* **Mário Antunes** - [mariolpantunes](https://github.com/mariolpantunes)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
