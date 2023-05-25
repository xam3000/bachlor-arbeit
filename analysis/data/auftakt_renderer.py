import numpy as np
import scipy.io.wavfile
from librosa import load
import pandas as pd
import os


class BeepGenerator:
    def __init__(self):
        # Audio will contain a long list of samples (i.e. floating point
        # numbers describing the waveform).  If you were working with a very
        # long sound you'd want to stream this to disk instead of buffering it
        # all in memory list this.  But most sounds will fit in memory.
        self.audio = []
        self.sample_rate = 44100.0
        self.existing = []

    def load_existing(self, FileName):
        sr, data = readAudio(FileName)
        self.sample_rate = sr
        self.existing = data

    def append_existing(self, startS, endS, toEnd=False):
        start = round(self.sample_rate * startS)
        end = round(self.sample_rate * endS)
        if toEnd:
            for x in range(start, len(self.existing)-1):
                self.audio.append(self.existing[x])
        else:
            for x in range(start, end):
                self.audio.append(self.existing[x])
        return

    def append_silence(self, duration_milliseconds=500):
        """
        Adding silence is easy - we add zeros to the end of our array
        """
        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)

        for x in range(int(num_samples)):
            self.audio.append(0.0)

        return

    def append_sinewave(
            self,
            freq=440.0,
            duration_milliseconds=500,
            volume=1.0):
        """
        The sine wave generated here is the standard beep.  If you want
        something more aggressive you could try a square or saw tooth waveform.
        Though there are some rather complicated issues with making high
        quality square and sawtooth waves... which we won't address here
        """

        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)

        x = np.array([i for i in range(int(num_samples))])

        sine_wave = volume * np.sin(2 * np.pi * freq * (x / self.sample_rate))

        self.audio.extend(list(sine_wave))
        return

    def append_sinewaves(
            self,
            freqs=[440.0],
            duration_milliseconds=500,
            volumes=[1.0]):
        """
        The sine wave generated here is the standard beep.  If you want
        something more aggressive you could try a square or saw tooth waveform.
        Though there are some rather complicated issues with making high
        quality square and sawtooth waves... which we won't address here
        len(freqs) must be the same as len(volumes)
        """

        volumes = list(np.array(volumes)/sum(volumes))
        num_samples = duration_milliseconds * (self.sample_rate / 1000.0)
        x = np.array([i for i in range(int(num_samples))])

        first_it = True
        for volume, freq in zip(volumes, freqs):
            print(freq)
            if first_it:
                sine_wave = volume * \
                    np.sin(2 * np.pi * freq * (x / self.sample_rate))
                first_it = False
            else:
                sine_wave += volume * \
                    np.sin(2 * np.pi * freq * (x / self.sample_rate))

        self.audio.extend(list(sine_wave))
        return

    def save_wav(self, file_name):
        # Open up a wav file
        # wav params

        # 44100 is the industry standard sample rate - CD quality.
        # If you need to save on file size you can adjust it downwards.
        # The standard for low quality is 8000 or 8kHz.

        # WAV files here are using short, 16 bit, signed integers for the
        # sample size.  So we multiply the floating point data we have
        # by 32767, the maximum value for a short integer.
        # NOTE: It is theoretically possible to use the floating point
        # -1.0 to 1.0 data directly in a WAV file but not obvious how to do
        # that using the wave module in python.
        self.audio = np.array(self.audio).astype(np.float32)
        scipy.io.wavfile.write(file_name, int(
            self.sample_rate), np.array(self.audio))

        return


# Loads audio
def readAudio(filePath):
    data, samplerate = load(filePath, sr=None)
    return samplerate, data


# Gets Auftakt v2 beats from csv file
def getBeatTimings(video_name, sampleRate):
    data = readCsv(video_name)
    timings = data['Position']
    bpms = data['BPM']
    converted = []
    for timing in timings:
        timingInSeconds = timing / sampleRate
        converted.append(timingInSeconds)
    bpm = np.average(bpms)
    return converted, bpm


# Gets auftakt v4 beats from 2 txt files
def getBeatTimingsTxT(video_name, sampleRate):
    data = readTxt(video_name)
    timings = data['Position']
    bpm = data['BPM']
    return timings, bpm


# Filters auftakt v2 results to only correct beats (ignore every second etc)
# Params:
#   beatTimings = Auftakt result
#   bpm = bpm of wav
#   offset = which offset to use when filtering
#   divi = which division to use (double time etc) -> also calculated
#       automatically by calcBeatDivision if not supplied
def augmentBeatTimings(beatTimings, bpm, offset=0, divi=None):
    div = calcBeatDivision(beatTimings, bpm)
    if divi:
        div = divi
    print(f'Beat Division is {div}, Offset is {offset}')
    augmented = beatTimings[offset::div]
    return augmented


# Calculates division between which bpm auftakt detected and
# which bpm auftakt actually rendered out
def calcBeatDivision(beatTimings, bpm):
    timePerBeat = 60/bpm
    dists = []
    for index, timing in enumerate(beatTimings):
        if index > 0:
            dist = timing - beatTimings[index-1]
            dists.append(dist)
    averageDist = np.average(dist)
    division = timePerBeat/averageDist
    retval = round(division)
    return retval


# Method to read in csv data corresponding to a wav file
def readCsv(filePath):
    # get file name without type ending
    dirPath, fileName = os.path.split(filePath)
    nameString = os.path.splitext(fileName)[0]
    data = None
    # read 'processed_nameOfWav.csv'
    if os.path.exists('processed_' + str(nameString) + '.csv'):
        data = pd.read_csv('processed_' + nameString + '.csv')
    return data


# Method to read in txt data corresponding to a wav file
def readTxt(filePath):
    # get file name without type ending
    dirPath, fileName = os.path.split(filePath)
    nameString = os.path.splitext(fileName)[0]

    data = dict()
    data['Position'] = []

    # read beats from 'beats_nameOfWav.txt'
    if os.path.exists('beats_' + str(nameString) + '.txt'):
        with open('beats_' + str(nameString) + '.txt') as f:
            for line in f:
                timing = float(line.strip())
                data['Position'].append(timing)

    # read bpm from 'bpm_nameOfWav.txt'
    if os.path.exists('bpm_' + str(nameString) + '.txt'):
        with open('bpm_' + str(nameString) + '.txt') as f:
            line = f.readline()
            data['BPM'] = float(line.strip())
    return data


# Adds Beeps to audio file based on auftakt beat meter
# Requires:
#   wav file to be in the same folder,
#   auftakt v2 result to be in the same folder in
#       format 'processed_nameOfWav.csv'
#   auftakt v4 results to be in the same folder in
#       format 'beats_nameOfWav.txt' and 'bpm_nameOfWav.txt'
# Param:
#   Path = File Path to wav file
#   vol = volume, range 0.0 - 1.0
#   dur = duration of each beep in MS
#   beatType = Auftakt version, new equals 4, old equals 2
#   offset = needed for auftakt 2, which offset to use when double time
#       beats are generated
#   div = needed for auftakt 2, describes which beat division was generated,
#       1 equals correct timing, 2 equals double time etc
def addBeeps(Path, vol=0.7, dur=10, beatType='New', offset=None, div=None):
    bg = BeepGenerator()
    bg.load_existing(Path)
    if beatType == 'New':
        timings, bpm = getBeatTimingsTxT(Path, bg.sample_rate)
    elif beatType == 'Old':
        timings, bpm = getBeatTimings(Path, bg.sample_rate)
    if offset or div:
        timings = augmentBeatTimings(timings, bpm, offset, div)
    prev = 0.0
    for timing in timings:
        bg.append_existing(prev, timing)
        bg.append_sinewave(volume=vol, duration_milliseconds=dur)
        prev = timing + float(dur)/1000
    bg.append_existing(prev, 0, toEnd=True)
    dirPath, fileName = os.path.split(Path)
    if dirPath == '':
        dirPath = os.getcwd()
    nameString = os.path.splitext(fileName)[0]
    savePath = f'self_processed_{beatType}_{nameString}.wav'
    if offset or div:
        savePath = f'offset{offset}_div{div}_{savePath}'
    bg.save_wav(f"{dirPath}/{savePath}")


# Adds beeps to both auftakt versions of wav file
def addBeepsBothVer(Path, vol=0.7, dur=10):
    addBeeps(Path, beatType='New', vol=vol, dur=dur)
    addBeeps(Path, beatType='Old', vol=vol, dur=dur)


# Adds beeps to both offsets of a wav file (used for auftakt v2)
def addBeepsBothOffset(Path, vol=0.7, dur=10):
    addBeeps(Path, beatType='Old', vol=vol, dur=dur, offset=0, div=2)
    addBeeps(Path, beatType='Old', vol=vol, dur=dur, offset=1, div=2)


if __name__ == "__main__":
    addBeeps('cut.wav')
    print('Done')
