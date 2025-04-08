import pygame
import random
import numpy as np

class P300Test:
    def __init__(self, tone_callback=None):
        # Constants
        self.total_tones = 10000
        self.tone_duration_ms = 200
        self.interval_ms = 800
        self.tones_ratio = [0.8, 0.2]
        self.first_tone_frequency = 1000
        self.second_tone_frequency = 1200

        self.running = False
        self.tone_callback = tone_callback

        # Pre-generate two Sound objects, one for each frequency
        self.sound_map = {}
        self._create_sounds()

        # Create a shuffled list of tones
        self.tones = self._create_tone_sequence()

    def _create_sounds(self):
        """Generate two Pygame Sound objects (one per frequency)."""
        sample_rate = 44100
        duration_sec = self.tone_duration_ms / 1000.0
        t = np.arange(0, duration_sec, 1.0 / sample_rate)

        for freq in [self.first_tone_frequency, self.second_tone_frequency]:
            audio_waveform = np.sin(2 * np.pi * freq * t)
            audio_waveform = (audio_waveform * 32767.0).astype(np.int16)
            stereo_waveform = np.column_stack((audio_waveform, audio_waveform))
            self.sound_map[freq] = pygame.sndarray.make_sound(stereo_waveform)

    def _create_tone_sequence(self):
        """Return the list of frequencies according to ratio, ensuring no two consecutive second tones."""
        num_first = int(self.total_tones * self.tones_ratio[0])
        num_second = int(self.total_tones * self.tones_ratio[1])

        tones = [self.first_tone_frequency] * num_first + \
                [self.second_tone_frequency] * num_second
        random.shuffle(tones)

        # Ensure no two consecutive second tones
        for i in range(1, len(tones) - 1):
            if (tones[i] == self.second_tone_frequency and
                    tones[i - 1] == self.second_tone_frequency):
                tones[i], tones[i + 1] = tones[i + 1], tones[i]

        return tones

    def play_tone(self, frequency):
        """Play a single tone and wait."""
        # Fire callback for LSL logging
        if self.tone_callback:
            self.tone_callback(frequency)

        # Play pre-generated sound
        self.sound_map[frequency].play()

        # Wait tone duration + interval
        pygame.time.delay(self.tone_duration_ms)
        pygame.time.delay(self.interval_ms)

    def start(self):
        """Begin playing the entire tone list in a loop."""
        self.running = True
        self.run()

    def stop(self):
        """Stop playing tones."""
        self.running = False

    def run(self):
        """Loop through the tones; stop if self.running becomes False."""
        for freq in self.tones:
            if not self.running:
                break
            self.play_tone(freq)

        # DO NOT call pygame.quit() here if the main app still needs pygame.
        # The main script can do a global pygame.quit() upon full exit if needed.
