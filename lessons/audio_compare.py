import librosa
import numpy as np
import matplotlib.pyplot as plt
from pydub import AudioSegment
import os
from scipy.spatial.distance import cdist
from datetime import datetime
import pathlib

# ------------------------------------------------------------------
# Step 1: Convert .m4a to .wav using pydub
# ------------------------------------------------------------------
def convert_m4a_to_wav(m4a_path, wav_path="temp.wav"):
    """
    Convert an M4A audio file to WAV format using pydub.

    Args:
        m4a_path (str): Path to the source M4A file.
        wav_path (str, optional): Path where the WAV file will be saved. Defaults to "temp.wav".

    Returns:
        str: Path to the created WAV file.

    Raises:
        FileNotFoundError: If the source M4A file doesn't exist.
        AudioSegment.CouldntDecodeError: If the M4A file is corrupted or invalid.
    """
    audio = AudioSegment.from_file(m4a_path, format="m4a")
    audio.export(wav_path, format="wav")
    return wav_path

def compare_audio(teacher_audio_m4a, student_audio_m4a):
    """
    Compare two audio files (teacher's and student's) and analyze their musical performance.
    
    This function performs a comprehensive analysis of two audio recordings, comparing pitch,
    timing, and harmonic content. It generates visualizations and detailed metrics of the
    performance comparison.
    
    Args:
        teacher_audio_m4a (str): Path to the teacher's audio file in M4A format
        student_audio_m4a (str): Path to the student's audio file in M4A format
        
    Returns:
        dict: A dictionary containing the performance analysis results with the following keys:
            - overall_score (float): Overall performance score (0-100)
            - pitch_accuracy (float): Pitch matching score (0-100)
            - timing_accuracy (float): Timing alignment score (0-100)
            - harmonic_accuracy (float): Harmonic content matching score (0-100)
            - details (dict): Detailed metrics of the performance
            - results_dir (str): Path to the directory containing generated plots and analysis
    """
    # Convert to wav
    teacher_wav = convert_m4a_to_wav(teacher_audio_m4a, 'teacher_temp.wav')
    student_wav = convert_m4a_to_wav(student_audio_m4a, 'student_temp.wav')

    # Load the WAV files into librosa
    y_teacher, sr_teacher = librosa.load(teacher_wav, sr=None)
    y_student, sr_student = librosa.load(student_wav, sr=None)

    # If needed, resample them to a common sample rate
    sr = 22050  # Use fixed sample rate
    y_teacher = librosa.resample(y_teacher, orig_sr=sr_teacher, target_sr=sr)
    y_student = librosa.resample(y_student, orig_sr=sr_student, target_sr=sr)

    # Extract pitch (f0) using pyin
    f0_teacher, voiced_flag_teacher, voiced_probs_teacher = librosa.pyin(
        y_teacher,
        sr=sr,
        fmin=librosa.note_to_hz('E2'),  # low note for guitar
        fmax=librosa.note_to_hz('E6')   # high note for guitar
    )

    f0_student, voiced_flag_student, voiced_probs_student = librosa.pyin(
        y_student,
        sr=sr,
        fmin=librosa.note_to_hz('E2'),
        fmax=librosa.note_to_hz('E6')
    )

    times_teacher = librosa.times_like(f0_teacher, sr=sr)
    times_student = librosa.times_like(f0_student, sr=sr)

    # ------------------------------------------------------------------
    # Step 4: Extract chroma features with proper normalization
    # ------------------------------------------------------------------
    def normalize_chroma(y, sr):
        """
        Normalize chroma features to prevent NaN values in DTW calculation.
        
        Computes and normalizes chroma features from audio data using the following steps:
        1. Compute Short-Time Fourier Transform (STFT)
        2. Extract chroma features
        3. Add small constant to prevent zero vectors
        4. Apply L2 normalization per frame

        Args:
            y (numpy.ndarray): Audio time series (mono) with shape (n,)
            sr (int): Sampling rate of the audio data

        Returns:
            numpy.ndarray: Normalized chroma features with shape (12, t),
                          where t is the number of time frames.
                          Each column represents the 12 pitch classes.

        Note:
            The function adds a small epsilon (1e-6) to prevent division by zero
            during normalization.
        """
        # Compute STFT
        S = np.abs(librosa.stft(y))
        
        # Compute chroma features
        chroma = librosa.feature.chroma_stft(S=S, sr=sr)
        
        # Add small constant to avoid zero vectors
        eps = 1e-6
        chroma = chroma + eps
        
        # L2 normalize each frame
        norm = np.sqrt(np.sum(chroma**2, axis=0))
        norm[norm == 0] = 1
        chroma = chroma / norm
        
        return chroma

    # Extract and normalize chroma features
    chroma_teacher = normalize_chroma(y_teacher, sr)
    chroma_student = normalize_chroma(y_student, sr)

    # Verify no NaN values
    assert not np.any(np.isnan(chroma_teacher)), "NaN values in teacher chroma"
    assert not np.any(np.isnan(chroma_student)), "NaN values in student chroma"

    # ------------------------------------------------------------------
    # Step 5: Align with Dynamic Time Warping (DTW) on chroma
    # ------------------------------------------------------------------
    # Compute custom distance matrix
    def cosine_distance_matrix(X, Y):
        """
        Compute cosine distance matrix between two feature matrices with zero-vector handling.

        Calculates the pairwise cosine distances between columns of X and Y matrices,
        with special handling for zero vectors to prevent NaN values.

        Args:
            X (numpy.ndarray): First feature matrix with shape (d, n),
                              where d is feature dimension and n is number of frames
            Y (numpy.ndarray): Second feature matrix with shape (d, m),
                              where d is feature dimension and m is number of frames

        Returns:
            numpy.ndarray: Distance matrix with shape (n, m) containing cosine distances.
                          Values are in range [0, 1], where:
                          - 0 indicates identical vectors
                          - 1 indicates orthogonal vectors

        Note:
            - Adds small epsilon (1e-8) to norms to prevent division by zero
            - Clips similarity values to [-1, 1] range before converting to distance
        """
        # Ensure matrices are 2D
        X = np.atleast_2d(X)
        Y = np.atleast_2d(Y)
        
        # Normalize the vectors
        X_norm = np.sqrt(np.sum(X * X, axis=0))
        Y_norm = np.sqrt(np.sum(Y * Y, axis=0))
        
        # Add small constant to avoid division by zero
        eps = 1e-8
        X_norm = X_norm + eps
        Y_norm = Y_norm + eps
        
        # Normalize the matrices
        X = X / X_norm
        Y = Y / Y_norm
        
        # Compute cosine similarity
        similarity = np.dot(X.T, Y) / (X_norm[:, np.newaxis] * Y_norm[np.newaxis, :])
        
        # Convert to distance (1 - similarity) and ensure no negative values
        distance = 1 - np.clip(similarity, -1, 1)
        
        return distance

    # Compute distance matrix
    C = cosine_distance_matrix(chroma_teacher, chroma_student)

    # Verify no NaN values in cost matrix
    assert not np.any(np.isnan(C)), "NaN values in cost matrix"

    # Perform DTW with pre-computed cost matrix
    D, wp = librosa.sequence.dtw(C=C)

    # ------------------------------------------------------------------
    # Step 6: Compare pitch along the warping path
    # ------------------------------------------------------------------
    def pitch_at_time(f0_array, time_array, t):
        """
        Find the pitch value at a specific time point in the audio.

        Locates the nearest pitch value in f0_array corresponding to the given time t
        by finding the closest time index in time_array.

        Args:
            f0_array (numpy.ndarray): Array of fundamental frequency values (Hz)
            time_array (numpy.ndarray): Array of time points corresponding to f0_array
            t (float): Target time point (seconds) to find pitch for

        Returns:
            float: Pitch value (Hz) at the nearest time point to t.
                   May be NaN if no pitch was detected at that time.
        """
        idx = np.argmin(np.abs(time_array - t))
        return f0_array[idx]

    pitch_diffs = []
    aligned_times_teacher = []
    aligned_times_student = []

    for (i, j) in wp:
        t_teacher = librosa.frames_to_time(i, sr=sr)
        t_student = librosa.frames_to_time(j, sr=sr)

        pitch_t = pitch_at_time(f0_teacher, times_teacher, t_teacher)
        pitch_s = pitch_at_time(f0_student, times_student, t_student)

        if np.isnan(pitch_t) or np.isnan(pitch_s):
            continue

        # Convert to cents
        def hz_to_cents(freq):
            return 1200.0 * np.log2(freq / 440.0) + 6900  # offset so A4=440Hz ~ 6900 cents

        cents_t = hz_to_cents(pitch_t)
        cents_s = hz_to_cents(pitch_s)

        diff = cents_s - cents_t
        pitch_diffs.append(diff)
        aligned_times_teacher.append(t_teacher)
        aligned_times_student.append(t_student)

    pitch_diffs = np.array(pitch_diffs)
    mean_pitch_diff = np.mean(np.abs(pitch_diffs))
    print(f"Average absolute pitch difference: {mean_pitch_diff:.2f} cents")

    # ------------------------------------------------------------------
    # Step 7: Compare chroma distance
    # ------------------------------------------------------------------
    chroma_diffs = []
    for (i, j) in wp:
        chroma_t = chroma_teacher[:, i]
        chroma_s = chroma_student[:, j]
        dist = np.linalg.norm(chroma_t - chroma_s)  # Euclidean distance
        chroma_diffs.append(dist)

    chroma_diffs = np.array(chroma_diffs)
    mean_chroma_diff = np.mean(chroma_diffs)
    print(f"Average chroma distance: {mean_chroma_diff:.4f}")

    # ------------------------------------------------------------------
    # Step 9: Calculate Performance Score
    # ------------------------------------------------------------------
    def calculate_performance_score(pitch_diffs, chroma_diffs, wp):
        """
        Calculate a comprehensive performance score based on multiple musical metrics.

        Evaluates the performance by analyzing three main components:
        1. Pitch accuracy (60% weight): How well the pitches match
        2. Timing accuracy (20% weight): How well the timing aligns
        3. Harmonic accuracy (20% weight): How well the harmonic content matches

        Args:
            pitch_diffs (numpy.ndarray): Array of pitch differences in cents
            chroma_diffs (numpy.ndarray): Array of chroma feature distances
            wp (numpy.ndarray): Warping path from DTW alignment, shape (n, 2)

        Returns:
            dict: Performance scores and detailed metrics containing:
                - overall_score (float): Weighted average of all components (0-100)
                - pitch_accuracy (float): Pitch matching score (0-100)
                - timing_accuracy (float): Timing alignment score (0-100)
                - harmonic_accuracy (float): Harmonic content matching score (0-100)
                - details (dict):
                    - mean_pitch_error_cents (float): Average pitch difference
                    - max_pitch_error_cents (float): Maximum pitch difference
                    - timing_deviation (float): Average timing misalignment
                    - mean_chroma_distance (float): Average harmonic difference

        Note:
            - Perfect match returns 100% for all metrics
            - Pitch differences > 100 cents are considered complete mistakes
            - Timing score uses exponential decay based on path deviations
            - Harmonic score is normalized relative to maximum difference
        """
        # Check for perfect match condition
        if np.all(np.abs(pitch_diffs) < 1e-6) and np.all(np.abs(chroma_diffs) < 1e-6):
            return {
                'overall_score': 100.0,
                'pitch_accuracy': 100.0,
                'timing_accuracy': 100.0,
                'harmonic_accuracy': 100.0,
                'details': {
                    'mean_pitch_error_cents': 0.0,
                    'max_pitch_error_cents': 0.0,
                    'timing_deviation': 0.0,
                    'mean_chroma_distance': 0.0
                }
            }
        
        # 1. Pitch Accuracy Score
        pitch_errors = np.abs(pitch_diffs)
        pitch_scores = np.clip(1 - (pitch_errors / 100), 0, 1) * 100
        pitch_accuracy = np.mean(pitch_scores)
        
        # 2. Timing Score
        path_lengths = np.diff(wp, axis=0)
        timing_deviations = np.abs(path_lengths - 1)
        timing_scores = np.exp(-timing_deviations.mean(axis=0)) * 100
        timing_score = np.mean(timing_scores)
        
        # 3. Harmonic Accuracy Score
        if np.all(chroma_diffs < 1e-6):
            harmonic_score = 100.0
        else:
            max_chroma_diff = np.max(chroma_diffs)
            if max_chroma_diff > 0:
                chroma_scores = np.clip(1 - (chroma_diffs / max_chroma_diff), 0, 1) * 100
                harmonic_score = np.mean(chroma_scores)
            else:
                harmonic_score = 100.0
        
        # Calculate weighted final score
        weights = {
            'pitch': 0.7,      # Pitch accuracy is crucial for chord recognition
            'timing': 0.1,     # Timing is less critical for chord recognition
            'harmonic': 0.2    # Harmonic content is important but secondary
        }
        
        final_score = (
            weights['pitch'] * pitch_accuracy +
            weights['timing'] * timing_score +
            weights['harmonic'] * harmonic_score
        )
        
        # Prepare detailed scores
        scores = {
            'overall_score': final_score,
            'pitch_accuracy': pitch_accuracy,
            'timing_accuracy': timing_score,
            'harmonic_accuracy': harmonic_score,
            'details': {
                'mean_pitch_error_cents': np.mean(pitch_errors),
                'max_pitch_error_cents': np.max(pitch_errors),
                'timing_deviation': timing_deviations.mean(),
                'mean_chroma_distance': np.mean(chroma_diffs)
            }
        }
        
        return scores

    # Calculate performance scores
    scores = calculate_performance_score(pitch_diffs, chroma_diffs, wp)

    # Print detailed performance analysis
    print("\nPerformance Analysis:")
    print("=" * 50)
    print(f"Overall Score: {scores['overall_score']:.1f}%")
    print("\nComponent Scores:")
    print(f"Pitch Accuracy: {scores['pitch_accuracy']:.1f}%")
    print(f"Timing Accuracy: {scores['timing_accuracy']:.1f}%")
    print(f"Harmonic Accuracy: {scores['harmonic_accuracy']:.1f}%")
    print("\nDetailed Metrics:")
    print(f"Average Pitch Error: {scores['details']['mean_pitch_error_cents']:.1f} cents")
    print(f"Maximum Pitch Error: {scores['details']['max_pitch_error_cents']:.1f} cents")
    print(f"Timing Deviation: {scores['details']['timing_deviation']:.3f}")
    print(f"Mean Harmonic Distance: {scores['details']['mean_chroma_distance']:.3f}")

    # ------------------------------------------------------------------
    # Step 8: Create results directory and save plots
    # ------------------------------------------------------------------
    def create_results_directory(teacher_file, student_file):
        """
        Create a directory for storing comparison results with timestamp and file names.

        Creates a new directory with a name formatted as:
        'comparison_results_YYYY-MM-DD_HH-MM-SS_teacherfile_vs_studentfile'

        Args:
            teacher_file (str): Path to the teacher's audio file
            student_file (str): Path to the student's audio file

        Returns:
            str: Path to the created directory

        Note:
            - Creates parent directories if they don't exist
            - Directory name includes file stems (names without extension)
            - Timestamp uses 24-hour format
        """
        # Get current timestamp in readable format
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Get base filenames without extension
        teacher_name = pathlib.Path(teacher_file).stem
        student_name = pathlib.Path(student_file).stem
        
        # Create directory name
        dir_name = f"comparison_results_{timestamp}_{teacher_name}_vs_{student_name}"
        
        # Create directory if it doesn't exist
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        
        return dir_name

    # Create results directory
    results_dir = create_results_directory(teacher_audio_m4a, student_audio_m4a)

    # Save pitch difference plot
    plt.figure()
    plt.title("Pitch Difference (Teacher vs Student) Over Time")
    plt.plot(aligned_times_teacher, pitch_diffs, label='Pitch Difference (cents)')
    plt.xlabel("Teacher's Time (seconds)")
    plt.ylabel("Difference (cents)")
    plt.legend()
    plt.savefig(os.path.join(results_dir, "pitch_difference.png"))
    plt.close()

    # Save chroma distance plot
    plt.figure()
    plt.title("Chroma Distance Along DTW Path")
    plt.plot(chroma_diffs, label='Chroma Distance')
    plt.xlabel("DTW path index")
    plt.ylabel("Distance")
    plt.legend()
    plt.savefig(os.path.join(results_dir, "chroma_distance.png"))
    plt.close()

    # Save enhanced visualization plots
    plt.figure(figsize=(15, 5))
    plt.subplot(131)
    plt.title("Pitch Accuracy Distribution")
    plt.hist(pitch_diffs, bins=50, color='blue', alpha=0.7)
    plt.xlabel("Pitch Difference (cents)")
    plt.ylabel("Frequency")

    plt.subplot(132)
    plt.title("Timing Alignment")
    plt.plot([p[0] for p in wp], [p[1] for p in wp], 'r-', alpha=0.5)
    plt.xlabel("Teacher Timeline")
    plt.ylabel("Student Timeline")

    plt.subplot(133)
    plt.title("Harmonic Distance Over Time")
    plt.plot(chroma_diffs, 'g-', alpha=0.7)
    plt.xlabel("Time")
    plt.ylabel("Harmonic Distance")

    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "combined_analysis.png"))
    plt.close()

    # Save performance analysis to text file
    with open(os.path.join(results_dir, "performance_analysis.txt"), "w") as f:
        f.write("Performance Analysis:\n")
        f.write("=" * 50 + "\n")
        f.write(f"Overall Score: {scores['overall_score']:.1f}%\n")
        f.write("\nComponent Scores:\n")
        f.write(f"Pitch Accuracy: {scores['pitch_accuracy']:.1f}%\n")
        f.write(f"Timing Accuracy: {scores['timing_accuracy']:.1f}%\n")
        f.write(f"Harmonic Accuracy: {scores['harmonic_accuracy']:.1f}%\n")
        f.write("\nDetailed Metrics:\n")
        f.write(f"Average Pitch Error: {scores['details']['mean_pitch_error_cents']:.1f} cents\n")
        f.write(f"Maximum Pitch Error: {scores['details']['max_pitch_error_cents']:.1f} cents\n")
        f.write(f"Timing Deviation: {scores['details']['timing_deviation']:.3f}\n")
        f.write(f"Mean Harmonic Distance: {scores['details']['mean_chroma_distance']:.3f}\n")

    print(f"\nResults saved in directory: {results_dir}")

    # Clean up temp files if desired
    os.remove(teacher_wav)
    os.remove(student_wav)

    # Add results directory to the scores dictionary
    scores['results_dir'] = results_dir
    return scores

# Example usage:
if __name__ == "__main__":
    teacher_audio_m4a = 'AL_OG.m4a'
    student_audio_m4a = 'AL_good.m4a'
    results = compare_audio(teacher_audio_m4a, student_audio_m4a)