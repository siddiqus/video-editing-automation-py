from typing import List
import os
from pydub import AudioSegment, effects
from pydub.silence import detect_nonsilent
import itertools
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
import logging
import argparse

# Configure the logging format
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,  # You can set the desired log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)


def detect_non_silent(audio_file, min_silence_len=200, silence_thresh=-50):
    audio = AudioSegment.from_file(audio_file)
    non_silent_segments = split_on_silence(
        audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh
    )
    return non_silent_segments


def split_on_silence(
    audio_segment,
    min_silence_len=1000,
    silence_thresh=-16,
    keep_silence=100,
    seek_step=1,
):
    def pairwise(iterable):
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    if isinstance(keep_silence, bool):
        keep_silence = len(audio_segment) if keep_silence else 0

    output_ranges = [
        [start - keep_silence, end + keep_silence]
        for (start, end) in detect_nonsilent(
            audio_segment, min_silence_len, silence_thresh, seek_step
        )
    ]

    for range_i, range_ii in pairwise(output_ranges):
        last_end = range_i[1]
        next_start = range_ii[0]
        if next_start < last_end:
            range_i[1] = (last_end + next_start) // 2
            range_ii[0] = range_i[1]

    results = []

    for start, end in output_ranges:
        the_start = max(start, 0)
        the_end = min(end, len(audio_segment))
        results.append(
            {
                "segment": audio_segment[the_start:the_end],
                "start": the_start,
                "end": the_end,
            }
        )
    return results


def remove_silence_from_video(
    input_video_path, output_video_path, min_silence_len=200, silence_thresh=-50
):
    try:
        audio_file = "temp_audio.wav"

        video_clip = VideoFileClip(input_video_path)
        video_clip.audio.write_audiofile(audio_file)

        logging.info("detectings non silent parts")
        non_silent_segments = detect_non_silent(
            audio_file, min_silence_len, silence_thresh
        )
        logging.info(
            "non-silent parts detected, length:" + str(len(non_silent_segments))
        )

        video_clips = []
        count = 1
        for segment in non_silent_segments:
            print(
                "working on count "
                + str(count)
                + " of "
                + str(len(non_silent_segments))
            )
            video_clips.append(
                video_clip.subclip(
                    segment.get("start") / 1000, segment.get("end") / 1000
                )
            )
            count += 1

        logging.info("concatenating clips")
        final_clip = concatenate_videoclips(video_clips)

        logging.info("writing new video file")
        final_clip.write_videofile(output_video_path)

        # Clean up temporary audio file
        logging.info("cleaning up")
        video_clip.audio.reader.close_proc()
        video_clip.reader.close()
        final_clip.close()
        video_clip.close()
    except Exception as error:
        print(error)
    os.remove(audio_file)


def extract_audio_from_video(video_path, audio_path):
    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)

    video.audio.reader.close_proc()
    audio.close()
    video.reader.close()
    video.close()

def normalize_audio(audio_path, target_dBFS=-20.0):
    audio: AudioSegment = AudioSegment.from_file(audio_path, format="wav")
    change_in_dBFS = target_dBFS - audio.dBFS
    normalized_audio = audio.apply_gain(change_in_dBFS)
    normalized_audio.export(audio_path, format="wav")

def compress_audio(audio_path, target_bitrate="64k"):
    audio: AudioSegment = AudioSegment.from_file(audio_path, format="wav")
    compressed_audio = effects.compress_dynamic_range(audio, threshold=-12, attack=200, release=1000, ratio=2)
    compressed_audio.export(audio_path, format="wav", bitrate=target_bitrate)

def quick_eq(audio_path):
    audio: AudioSegment = AudioSegment.from_file(audio_path, format="wav")
    
    # 1. high pass filter 120
    audio = audio.high_pass_filter(120)  # Adjust the frequency as needed
    
    # 2. boost presence -> gentle boost, 2k to 5k hz
    
    # 3. reduce harshness -> gentle cut for 6k to 10k
    # 4. reduce boxiness -> gentle cut 300-500 hz

    audio.export(audio_path, format="wav")
    

def replace_audio_in_video(video_path, new_audio_path, output_video_path):
    video = VideoFileClip(video_path)
    new_audio = AudioFileClip(new_audio_path)
    video = video.set_audio(new_audio)
    video.write_videofile(output_video_path, codec="libx264")

    video.reader.close()
    video.close()
    new_audio.close()


def eq_audio(audio_path):
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)
    
    # High-Pass Filter (remove low-frequency noise)
    audio = audio.high_pass_filter(120)  # Adjust the frequency as needed

    # Low Shelf Filter (add warmth)
    # audio = audio.low_shelf(gain=3.0, frequency=100)  # Adjust gain and frequency as needed

    # Parametric EQ (fine-tune audio)
    # audio = scipy_effects.eq(audio,  500, 250, "L+R", "notch")
    # audio = scipy_effects.eq(audio, 500, 400, "L+R", "notch")
    # audio = scipy_effects.eq(audio, 500, 1000, "L+R", "notch", gain_dB=2)
    # audio = scipy_effects.eq(audio, 500, 5000, "L+R", "notch", gain_dB=-1)
    # audio = scipy_effects.eq(audio, 500, 6000, "L+R", "notch", gain_dB=-3)

    # # audio = scipy_effects.high_pass_filter(audio, )
    # audio = audio.filter("bandpass", frequency=250, Q=1.5)  # Cut frequencies around 250Hz
    # audio = audio.filter("bandpass", frequency=400, Q=1.5)  # Cut frequencies around 400Hz
    # audio = audio.filter("bandpass", frequency=1000, Q=1.0, gain=2.0)  # Boost frequencies around 1kHz
    # audio = audio.filter("bandpass", frequency=5000, Q=1.0, gain=-1.0)  # Cut frequencies around 5kHz
    # audio = audio.filter("bandpass", frequency=6000, Q=2.0, gain=-3.0)  # Cut sibilant range around 6kHz to 8kHz

    audio = audio.high_shelf(
        gain=2.0, frequency=10000
    )  # Boost high-end around 10kHz to 15kHz

    # High-Pass Filter (remove low-end muddiness)
    audio = audio.high_pass_filter(200)  # Adjust the frequency as needed

    # Export the enhanced audio to a new file
    audio.export(audio_path, format="wav")


def band_reject_filter(audio: AudioSegment, reject_start, reject_end):
    # Apply a low-pass filter (cut off frequencies above reject_start)
    low_pass_audio = audio.low_pass_filter(reject_start)

    # Apply a high-pass filter (cut off frequencies below reject_end)
    high_pass_audio = low_pass_audio.high_pass_filter(reject_end)

    return high_pass_audio


def de_ess_audio(audio_path):
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)

    # Define the frequency range for de-essing (typically 6kHz to 8kHz)
    de_ess_start = 6000
    de_ess_end = 8000

    # Create a notch filter to reduce the sibilant frequencies
    # filter_bandwidth = 100  # Adjust the bandwidth as needed
    notch_filter = band_reject_filter(audio, de_ess_start, de_ess_end)

    # Apply the notch filter to the audio
    de_essed_audio = audio.overlay(notch_filter)

    # Export the de-essed audio to a new file
    de_essed_audio.export(audio_path, format="wav")


def remove_plosives(audio_path):
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)

    # Apply a high-pass filter (cut off frequencies below cutoff_freq)
    cutoff_freq = 100
    audio = audio.high_pass_filter(cutoff_freq)

    # Apply a low-pass filter (cut off frequencies above cutoff_freq)
    audio = audio.low_pass_filter(cutoff_freq)

    # Export the plosive-removed audio to a new file
    audio.export(audio_path, format="wav")


def normalize_loudness(audio_path, target_lufs=-16.0):
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)

    # Calculate the current loudness in LUFS
    current_lufs = audio.dBFS

    # Calculate the gain adjustment needed for normalization
    gain_adjustment = target_lufs - current_lufs

    # Apply the gain adjustment to the audio
    normalized_audio = audio.apply_gain(gain_adjustment)

    # Export the normalized audio to a new file
    normalized_audio.export(audio_path, format="wav")


def improve_audio(video_path, output_video_path):
    audio_path = "tmp_extracted_audio.wav"

    logging.info("extracting audio from video")
    extract_audio_from_video(video_path, audio_path)

    # logging.info('removing plossives from audio')
    # remove_plosives(audio_path)

    # logging.info('de-essing audio')
    # de_ess_audio(audio_path)

    # logging.info('eq adjust audio')
    # eq_audio(audio_path)

    logging.info("normalizing audio")
    normalize_audio(audio_path)

    logging.info("compressing audio")
    compress_audio(audio_path)

    quick_eq(audio_path)

    # logging.info('normalize loudness in audio')
    # normalize_loudness(audio_path)

    # Step 6: Replace audio in the video
    logging.info("replacing audio in video")
    replace_audio_in_video(video_path, audio_path, output_video_path)

    # Clean up intermediate files
    os.remove(audio_path)


def remove_silence_and_normalize(input_video_file):
    tmp_output_video_file = str(input_video_file).replace(".mp4", "-tmp.mp4")
    output_video_file = str(input_video_file).replace(".mp4", "-edited.mp4")

    remove_silence_from_video(input_video_file, tmp_output_video_file)

    improve_audio(tmp_output_video_file, output_video_file)

    # os.unlink(tmp_output_video_file) # todo - remove this file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A CLI to remove silence and enhance audio in a video")
    
    parser.add_argument("-p", "--path", help="Full path to video file")

    args = parser.parse_args()

    if not args.path or not str(args.path).strip():
        logging.error('filepath not provided!\nRun script with -p argument e.g. "python index.py -p /full/path/to/file.mp4"')
        exit(1)        

    remove_silence_and_normalize("videos/raw3.mp4")
