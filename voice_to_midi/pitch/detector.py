"""
Pitch detection module using autocorrelation and other algorithms.

This module implements various pitch detection algorithms optimized for
real-time vocal input with confidence scoring and filtering.
"""

import logging
from typing import Optional, Tuple, List
import numpy as np
from scipy import signal

from ..core.exceptions import PitchDetectionError
from ..utils.helpers import frequency_to_midi_note


logger = logging.getLogger(__name__)


class PitchDetector:
    """
    Real-time pitch detection using autocorrelation and other algorithms.
    
    This class implements pitch detection algorithms optimized for vocal input
    with configurable parameters for frequency range, confidence thresholds,
    and smoothing.
    
    Example:
        >>> detector = PitchDetector()
        >>> detector.configure(min_freq=80, max_freq=800, confidence_threshold=0.8)
        >>> frequency, confidence = detector.detect_pitch(audio_data)
        >>> midi_note = detector.frequency_to_midi(frequency)
    """
    
    def __init__(self):
        """Initialize the pitch detector."""
        self.sample_rate = 44100
        self.min_freq = 80.0
        self.max_freq = 800.0
        self.confidence_threshold = 0.8
        self.algorithm = 'autocorrelation'
        
        # Smoothing parameters
        self.smoothing_enabled = True
        self.smoothing_factor = 0.3
        self.last_frequency = None
        
        # Octave correction
        self.octave_correction = True
        
        logger.debug("Pitch detector initialized")
    
    def configure(self, sample_rate: int = 44100, min_freq: float = 80.0,
                  max_freq: float = 800.0, confidence_threshold: float = 0.8,
                  algorithm: str = 'autocorrelation') -> None:
        """
        Configure pitch detection parameters.
        
        Args:
            sample_rate: Sample rate in Hz
            min_freq: Minimum frequency to detect
            max_freq: Maximum frequency to detect
            confidence_threshold: Minimum confidence for valid detection
            algorithm: Detection algorithm ('autocorrelation', 'yin', 'fft')
            
        Raises:
            PitchDetectionError: If configuration is invalid
        """
        if sample_rate <= 0:
            raise PitchDetectionError("Sample rate must be positive")
        if min_freq <= 0:
            raise PitchDetectionError("Minimum frequency must be positive")
        if max_freq <= min_freq:
            raise PitchDetectionError("Maximum frequency must be greater than minimum")
        if not (0 <= confidence_threshold <= 1):
            raise PitchDetectionError("Confidence threshold must be between 0 and 1")
        if algorithm not in ['autocorrelation', 'yin', 'fft']:
            raise PitchDetectionError("Unknown algorithm")
        
        self.sample_rate = sample_rate
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.confidence_threshold = confidence_threshold
        self.algorithm = algorithm
        
        logger.info(f"Pitch detector configured: {min_freq}-{max_freq}Hz, threshold={confidence_threshold}")
    
    def detect_pitch(self, audio_data: np.ndarray) -> Tuple[Optional[float], float]:
        """
        Detect pitch in audio data.
        
        Args:
            audio_data: Audio data to analyze
            
        Returns:
            Tuple of (frequency, confidence) or (None, 0.0) if no pitch detected
            
        Raises:
            PitchDetectionError: If detection fails
        """
        if audio_data is None or len(audio_data) == 0:
            return None, 0.0
        
        try:
            if self.algorithm == 'autocorrelation':
                frequency, confidence = self._autocorrelation_pitch(audio_data)
            elif self.algorithm == 'yin':
                frequency, confidence = self._yin_pitch(audio_data)
            elif self.algorithm == 'fft':
                frequency, confidence = self._fft_pitch(audio_data)
            else:
                raise PitchDetectionError(f"Unknown algorithm: {self.algorithm}")
            
            # Apply octave correction if enabled
            if self.octave_correction and frequency is not None:
                frequency = self._apply_octave_correction(frequency, audio_data)
            
            # Apply smoothing if enabled
            if self.smoothing_enabled and frequency is not None:
                frequency = self._apply_smoothing(frequency)
            
            # Update last frequency
            self.last_frequency = frequency
            
            return frequency, confidence
            
        except Exception as e:
            raise PitchDetectionError(f"Pitch detection failed: {e}")
    
    def _autocorrelation_pitch(self, audio_data: np.ndarray) -> Tuple[Optional[float], float]:
        """
        Detect pitch using autocorrelation method.
        
        Args:
            audio_data: Audio data
            
        Returns:
            Tuple of (frequency, confidence)
        """
        # Compute autocorrelation
        autocorr = np.correlate(audio_data, audio_data, mode='full')
        autocorr = autocorr[len(autocorr) // 2:]
        
        # Find peaks in autocorrelation
        peaks, properties = signal.find_peaks(
            autocorr, 
            height=np.max(autocorr) * 0.1,
            distance=int(self.sample_rate / self.max_freq)
        )
        
        if len(peaks) == 0:
            return None, 0.0
        
        # Find the first significant peak within frequency range
        for peak in peaks:
            if peak > 0:
                frequency = self.sample_rate / peak
                if self.min_freq <= frequency <= self.max_freq:
                    confidence = autocorr[peak] / np.max(autocorr)
                    return frequency, confidence
        
        return None, 0.0
    
    def _yin_pitch(self, audio_data: np.ndarray) -> Tuple[Optional[float], float]:
        """
        Detect pitch using YIN algorithm.
        
        Args:
            audio_data: Audio data
            
        Returns:
            Tuple of (frequency, confidence)
        """
        # Simplified YIN implementation
        # This is a basic version - full YIN is more complex
        
        buffer_size = len(audio_data)
        yin_buffer = np.zeros(buffer_size // 2)
        
        # Step 1: Autocorrelation
        for lag in range(1, buffer_size // 2):
            for i in range(buffer_size // 2):
                if i + lag < buffer_size:
                    yin_buffer[lag] += (audio_data[i] - audio_data[i + lag]) ** 2
        
        # Step 2: Cumulative mean normalized difference
        yin_buffer[0] = 1.0
        running_sum = 0.0
        
        for lag in range(1, buffer_size // 2):
            running_sum += yin_buffer[lag]
            if running_sum == 0:
                yin_buffer[lag] = 1.0
            else:
                yin_buffer[lag] *= lag / running_sum
        
        # Step 3: Find minimum
        min_lag = np.argmin(yin_buffer[1:]) + 1
        
        if min_lag > 0:
            frequency = self.sample_rate / min_lag
            if self.min_freq <= frequency <= self.max_freq:
                confidence = 1.0 - yin_buffer[min_lag]
                return frequency, confidence
        
        return None, 0.0
    
    def _fft_pitch(self, audio_data: np.ndarray) -> Tuple[Optional[float], float]:
        """
        Detect pitch using FFT-based method.
        
        Args:
            audio_data: Audio data
            
        Returns:
            Tuple of (frequency, confidence)
        """
        # Compute FFT
        fft = np.fft.rfft(audio_data)
        magnitudes = np.abs(fft)
        frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / self.sample_rate)
        
        # Find frequency range indices
        min_idx = np.argmax(frequencies >= self.min_freq)
        max_idx = np.argmax(frequencies >= self.max_freq)
        if max_idx == 0:
            max_idx = len(frequencies) - 1
        
        # Find peak in frequency range
        range_magnitudes = magnitudes[min_idx:max_idx]
        if len(range_magnitudes) == 0:
            return None, 0.0
        
        peak_idx = np.argmax(range_magnitudes)
        frequency = frequencies[min_idx + peak_idx]
        
        # Calculate confidence as normalized magnitude
        confidence = range_magnitudes[peak_idx] / np.max(magnitudes)
        
        return frequency, confidence
    
    def _apply_octave_correction(self, frequency: float, audio_data: np.ndarray) -> float:
        """
        Apply octave correction to detected frequency.
        
        Args:
            frequency: Detected frequency
            audio_data: Original audio data
            
        Returns:
            Corrected frequency
        """
        # Check for strong harmonics that might indicate octave errors
        try:
            fft = np.fft.rfft(audio_data)
            magnitudes = np.abs(fft)
            frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / self.sample_rate)
            
            # Check octave below (half frequency)
            half_freq = frequency / 2
            if half_freq >= self.min_freq:
                half_idx = np.argmin(np.abs(frequencies - half_freq))
                if half_idx < len(magnitudes):
                    # Find the original frequency index
                    orig_idx = np.argmin(np.abs(frequencies - frequency))
                    
                    # If the lower octave has significantly higher magnitude,
                    # it's likely the fundamental
                    if magnitudes[half_idx] > magnitudes[orig_idx] * 1.5:
                        return half_freq
            
            # Check octave above (double frequency)
            double_freq = frequency * 2
            if double_freq <= self.max_freq:
                double_idx = np.argmin(np.abs(frequencies - double_freq))
                if double_idx < len(magnitudes):
                    orig_idx = np.argmin(np.abs(frequencies - frequency))
                    
                    # If the higher octave has much higher magnitude,
                    # the detected frequency might be a subharmonic
                    if magnitudes[double_idx] > magnitudes[orig_idx] * 2.0:
                        return double_freq
            
            return frequency
            
        except Exception as e:
            logger.debug(f"Octave correction failed: {e}")
            return frequency
    
    def _apply_smoothing(self, frequency: float) -> float:
        """
        Apply smoothing to frequency.
        
        Args:
            frequency: Current frequency
            
        Returns:
            Smoothed frequency
        """
        if self.last_frequency is None:
            return frequency
        
        # Apply exponential smoothing
        smoothed = (self.last_frequency * self.smoothing_factor + 
                   frequency * (1 - self.smoothing_factor))
        
        return smoothed
    
    def frequency_to_midi(self, frequency: float, transpose: int = 0) -> int:
        """
        Convert frequency to MIDI note number.
        
        Args:
            frequency: Frequency in Hz
            transpose: Transpose in semitones
            
        Returns:
            MIDI note number
        """
        return frequency_to_midi_note(frequency, transpose)
    
    def get_detection_info(self) -> dict:
        """
        Get information about current detection settings.
        
        Returns:
            Dictionary with detection information
        """
        return {
            'sample_rate': self.sample_rate,
            'min_freq': self.min_freq,
            'max_freq': self.max_freq,
            'confidence_threshold': self.confidence_threshold,
            'algorithm': self.algorithm,
            'smoothing_enabled': self.smoothing_enabled,
            'smoothing_factor': self.smoothing_factor,
            'octave_correction': self.octave_correction,
            'last_frequency': self.last_frequency,
        }
    
    def reset(self) -> None:
        """Reset detector state."""
        self.last_frequency = None
        logger.debug("Pitch detector reset")
    
    def set_smoothing(self, enabled: bool, factor: float = 0.3) -> None:
        """
        Configure frequency smoothing.
        
        Args:
            enabled: Whether to enable smoothing
            factor: Smoothing factor (0-1, higher = more smoothing)
        """
        self.smoothing_enabled = enabled
        self.smoothing_factor = max(0.0, min(1.0, factor))
        logger.debug(f"Smoothing configured: enabled={enabled}, factor={factor}")
    
    def set_octave_correction(self, enabled: bool) -> None:
        """
        Enable or disable octave correction.
        
        Args:
            enabled: Whether to enable octave correction
        """
        self.octave_correction = enabled
        logger.debug(f"Octave correction: {enabled}")
    
    def analyze_harmonics(self, audio_data: np.ndarray, fundamental: float) -> List[Tuple[float, float]]:
        """
        Analyze harmonics of a fundamental frequency.
        
        Args:
            audio_data: Audio data
            fundamental: Fundamental frequency
            
        Returns:
            List of (frequency, magnitude) tuples for harmonics
        """
        try:
            fft = np.fft.rfft(audio_data)
            magnitudes = np.abs(fft)
            frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / self.sample_rate)
            
            harmonics = []
            
            # Check up to 8 harmonics
            for harmonic in range(1, 9):
                harmonic_freq = fundamental * harmonic
                if harmonic_freq > self.sample_rate / 2:
                    break
                
                # Find closest frequency bin
                idx = np.argmin(np.abs(frequencies - harmonic_freq))
                if idx < len(magnitudes):
                    harmonics.append((harmonic_freq, magnitudes[idx]))
            
            return harmonics
            
        except Exception as e:
            logger.error(f"Harmonic analysis failed: {e}")
            return []