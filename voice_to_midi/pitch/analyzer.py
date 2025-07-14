"""
Pitch analysis utilities for advanced pitch processing.

This module provides additional pitch analysis utilities including
note stability analysis, vibrato detection, and pitch tracking.
"""

import logging
from typing import List, Tuple, Optional
import numpy as np
from collections import deque

from ..utils.helpers import frequency_to_note_name, midi_note_to_name


logger = logging.getLogger(__name__)


class PitchAnalyzer:
    """
    Advanced pitch analysis utilities.
    
    This class provides additional pitch analysis functionality including
    note stability analysis, vibrato detection, and pitch tracking over time.
    
    Example:
        >>> analyzer = PitchAnalyzer()
        >>> analyzer.add_pitch_sample(440.0, 0.9)
        >>> stability = analyzer.get_pitch_stability()
        >>> vibrato = analyzer.detect_vibrato()
    """
    
    def __init__(self, history_size: int = 100):
        """
        Initialize the pitch analyzer.
        
        Args:
            history_size: Number of pitch samples to keep in history
        """
        self.history_size = history_size
        self.pitch_history = deque(maxlen=history_size)
        self.confidence_history = deque(maxlen=history_size)
        self.time_history = deque(maxlen=history_size)
        
        # Analysis parameters
        self.stability_threshold = 0.05  # 5% frequency variation
        self.vibrato_min_rate = 4.0  # Hz
        self.vibrato_max_rate = 8.0  # Hz
        self.vibrato_min_depth = 0.02  # 2% frequency variation
        
        logger.debug("Pitch analyzer initialized")
    
    def add_pitch_sample(self, frequency: Optional[float], confidence: float, 
                        timestamp: Optional[float] = None) -> None:
        """
        Add a pitch sample to the analysis history.
        
        Args:
            frequency: Detected frequency (None for silence)
            confidence: Detection confidence
            timestamp: Sample timestamp (None for auto-generated)
        """
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        self.pitch_history.append(frequency)
        self.confidence_history.append(confidence)
        self.time_history.append(timestamp)
    
    def get_pitch_stability(self, window_size: int = 20) -> float:
        """
        Calculate pitch stability over recent samples.
        
        Args:
            window_size: Number of recent samples to analyze
            
        Returns:
            Stability score (0-1, higher = more stable)
        """
        if len(self.pitch_history) < window_size:
            return 0.0
        
        # Get recent valid pitches
        recent_pitches = []
        for i in range(-window_size, 0):
            if i < -len(self.pitch_history):
                break
            pitch = self.pitch_history[i]
            if pitch is not None:
                recent_pitches.append(pitch)
        
        if len(recent_pitches) < 2:
            return 0.0
        
        # Calculate coefficient of variation
        mean_pitch = np.mean(recent_pitches)
        std_pitch = np.std(recent_pitches)
        
        if mean_pitch == 0:
            return 0.0
        
        cv = std_pitch / mean_pitch
        
        # Convert to stability score (lower CV = higher stability)
        stability = max(0.0, 1.0 - cv / self.stability_threshold)
        
        return stability
    
    def detect_vibrato(self, window_size: int = 50) -> Tuple[bool, float, float]:
        """
        Detect vibrato in recent pitch samples.
        
        Args:
            window_size: Number of recent samples to analyze
            
        Returns:
            Tuple of (has_vibrato, rate_hz, depth_percent)
        """
        if len(self.pitch_history) < window_size or len(self.time_history) < window_size:
            return False, 0.0, 0.0
        
        # Get recent valid pitches and times
        recent_pitches = []
        recent_times = []
        
        for i in range(-window_size, 0):
            if i < -len(self.pitch_history):
                break
            pitch = self.pitch_history[i]
            if pitch is not None:
                recent_pitches.append(pitch)
                recent_times.append(self.time_history[i])
        
        if len(recent_pitches) < 10:
            return False, 0.0, 0.0
        
        try:
            # Detrend the pitch data
            pitches = np.array(recent_pitches)
            times = np.array(recent_times)
            
            # Remove linear trend
            coeffs = np.polyfit(times, pitches, 1)
            trend = np.polyval(coeffs, times)
            detrended = pitches - trend
            
            # Calculate FFT to find dominant frequency
            dt = np.mean(np.diff(times))
            if dt <= 0:
                return False, 0.0, 0.0
            
            sample_rate = 1.0 / dt
            fft = np.fft.rfft(detrended)
            freqs = np.fft.rfftfreq(len(detrended), dt)
            
            # Find peak in vibrato frequency range
            vibrato_mask = (freqs >= self.vibrato_min_rate) & (freqs <= self.vibrato_max_rate)
            if not np.any(vibrato_mask):
                return False, 0.0, 0.0
            
            vibrato_freqs = freqs[vibrato_mask]
            vibrato_mags = np.abs(fft[vibrato_mask])
            
            if len(vibrato_mags) == 0:
                return False, 0.0, 0.0
            
            peak_idx = np.argmax(vibrato_mags)
            vibrato_rate = vibrato_freqs[peak_idx]
            
            # Calculate vibrato depth
            vibrato_depth = 2 * np.std(detrended) / np.mean(pitches)
            
            # Check if vibrato is significant
            has_vibrato = (vibrato_depth >= self.vibrato_min_depth and 
                          self.vibrato_min_rate <= vibrato_rate <= self.vibrato_max_rate)
            
            return has_vibrato, vibrato_rate, vibrato_depth * 100
            
        except Exception as e:
            logger.debug(f"Vibrato detection failed: {e}")
            return False, 0.0, 0.0
    
    def get_pitch_trend(self, window_size: int = 30) -> str:
        """
        Analyze pitch trend over recent samples.
        
        Args:
            window_size: Number of recent samples to analyze
            
        Returns:
            Trend description ('rising', 'falling', 'stable', 'unknown')
        """
        if len(self.pitch_history) < window_size:
            return 'unknown'
        
        # Get recent valid pitches
        recent_pitches = []
        for i in range(-window_size, 0):
            if i < -len(self.pitch_history):
                break
            pitch = self.pitch_history[i]
            if pitch is not None:
                recent_pitches.append(pitch)
        
        if len(recent_pitches) < 5:
            return 'unknown'
        
        # Calculate linear trend
        try:
            x = np.arange(len(recent_pitches))
            coeffs = np.polyfit(x, recent_pitches, 1)
            slope = coeffs[0]
            
            # Normalize by mean frequency
            mean_freq = np.mean(recent_pitches)
            if mean_freq == 0:
                return 'unknown'
            
            normalized_slope = slope / mean_freq
            
            # Classify trend
            if normalized_slope > 0.001:  # 0.1% rise per sample
                return 'rising'
            elif normalized_slope < -0.001:  # 0.1% fall per sample
                return 'falling'
            else:
                return 'stable'
                
        except Exception as e:
            logger.debug(f"Trend analysis failed: {e}")
            return 'unknown'
    
    def get_note_duration(self, note_name: str) -> float:
        """
        Get the duration of the current note.
        
        Args:
            note_name: Note name to check duration for
            
        Returns:
            Duration in seconds
        """
        if len(self.pitch_history) < 2 or len(self.time_history) < 2:
            return 0.0
        
        # Find the start of the current note
        start_idx = None
        for i in range(len(self.pitch_history) - 1, -1, -1):
            pitch = self.pitch_history[i]
            if pitch is not None:
                current_note = frequency_to_note_name(pitch)
                if current_note == note_name:
                    start_idx = i
                else:
                    break
            else:
                break
        
        if start_idx is None:
            return 0.0
        
        # Calculate duration from start to end
        start_time = self.time_history[start_idx]
        end_time = self.time_history[-1]
        
        return end_time - start_time
    
    def get_confidence_trend(self, window_size: int = 20) -> float:
        """
        Get the trend in detection confidence.
        
        Args:
            window_size: Number of recent samples to analyze
            
        Returns:
            Confidence trend (-1 to 1, negative = decreasing confidence)
        """
        if len(self.confidence_history) < window_size:
            return 0.0
        
        recent_confidence = list(self.confidence_history)[-window_size:]
        
        try:
            x = np.arange(len(recent_confidence))
            coeffs = np.polyfit(x, recent_confidence, 1)
            slope = coeffs[0]
            
            # Normalize to -1 to 1 range
            return np.clip(slope * 100, -1.0, 1.0)
            
        except Exception as e:
            logger.debug(f"Confidence trend analysis failed: {e}")
            return 0.0
    
    def get_pitch_statistics(self) -> dict:
        """
        Get statistical information about pitch history.
        
        Returns:
            Dictionary with pitch statistics
        """
        if not self.pitch_history:
            return {}
        
        valid_pitches = [p for p in self.pitch_history if p is not None]
        
        if not valid_pitches:
            return {'valid_samples': 0}
        
        stats = {
            'valid_samples': len(valid_pitches),
            'total_samples': len(self.pitch_history),
            'mean_frequency': np.mean(valid_pitches),
            'std_frequency': np.std(valid_pitches),
            'min_frequency': np.min(valid_pitches),
            'max_frequency': np.max(valid_pitches),
            'frequency_range': np.max(valid_pitches) - np.min(valid_pitches),
        }
        
        # Add confidence statistics
        if self.confidence_history:
            stats.update({
                'mean_confidence': np.mean(self.confidence_history),
                'std_confidence': np.std(self.confidence_history),
                'min_confidence': np.min(self.confidence_history),
                'max_confidence': np.max(self.confidence_history),
            })
        
        return stats
    
    def get_note_histogram(self) -> dict:
        """
        Get histogram of detected notes.
        
        Returns:
            Dictionary with note names as keys and counts as values
        """
        note_counts = {}
        
        for pitch in self.pitch_history:
            if pitch is not None:
                note_name = frequency_to_note_name(pitch)
                note_counts[note_name] = note_counts.get(note_name, 0) + 1
        
        return note_counts
    
    def clear_history(self) -> None:
        """Clear all analysis history."""
        self.pitch_history.clear()
        self.confidence_history.clear()
        self.time_history.clear()
        logger.debug("Pitch analysis history cleared")
    
    def export_history(self) -> dict:
        """
        Export pitch history for analysis.
        
        Returns:
            Dictionary with history data
        """
        return {
            'pitches': list(self.pitch_history),
            'confidences': list(self.confidence_history),
            'timestamps': list(self.time_history),
            'parameters': {
                'stability_threshold': self.stability_threshold,
                'vibrato_min_rate': self.vibrato_min_rate,
                'vibrato_max_rate': self.vibrato_max_rate,
                'vibrato_min_depth': self.vibrato_min_depth,
            }
        }