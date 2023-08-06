# Video Editing Automation

This script automates some basic video/audio editing that I usually do for my YouTube videos.

## Usage

Run the script by passing a full filepath of the video you want to edit

```
python index.py -p /full/path/to/file.mp4
```

This will create a new video file with `-edited` suffix in the same location as the input video file. E.g. `/full/path/to/file-edited.mp4`.

The new file will have the following edits:
1. Remove all 'silent' parts of the video
2. Normalize the audio volume
3. Add compression to the audio
4. Basic EQ - high pass filter

## Todo:
1. denoise
2. deesser
3. better EQ for podcast voice