#!/usr/bin/env python3
"""
XML Transcription to Turn-Based Conversation Processor

This script processes speaker transcription XML files and converts them into
a readable conversation format with timing information. Turns are based on
speech gaps rather than speaker changes - a turn continues as long as a speaker
keeps talking (even with overlaps), but ends when they stop for more than a
specified threshold.

Usage:
    python transcription_processor.py [directory] [speakers] [gap_threshold]
    
Arguments:
    directory: Directory containing XML files (default: current directory)
    speakers: Comma-separated list of speakers (e.g., "A,B,C,D") 
    gap_threshold: Silence gap in seconds to end a turn (default: 1.0)

Output:
    CSV file with columns: speaker, text, onset_time, offset_time
"""

import re
import os
import sys
import glob
import csv
import xml.etree.ElementTree as ET
import html
from typing import Dict, List, Tuple, Optional


def extract_speaker_from_filename(filename: str) -> str:
    """
    Extract speaker ID from XML filename.
    
    Args:
        filename: XML filename (e.g., "EN2002a.A.xml")
        
    Returns:
        Speaker ID (e.g., "A") or None if not found
    """
    match = re.search(r'\.([A-Z])\.xml$', filename)
    return match.group(1) if match else None


def discover_xml_files_and_speakers(directory: str) -> List[Tuple[str, str]]:
    """
    Automatically discover XML files and their corresponding speakers.
    
    Args:
        directory: Directory path to search for XML files
        
    Returns:
        List of (file_path, speaker_id) tuples sorted by speaker
    """
    xml_files = glob.glob(os.path.join(directory, "*.xml"))
    file_speaker_pairs = []
    
    for file_path in xml_files:
        filename = os.path.basename(file_path)
        speaker_id = extract_speaker_from_filename(filename)
        if speaker_id:
            file_speaker_pairs.append((file_path, speaker_id))
    
    # Sort by speaker ID to ensure consistent order
    file_speaker_pairs.sort(key=lambda x: x[1])
    return file_speaker_pairs


def extract_words_from_xml(xml_file_path: str, speaker_id: str) -> Dict[float, str]:
    """
    Extract words and their timestamps from a single XML file.
    
    This function parses XML files containing <w> elements with timestamp information
    and extracts word content, preserving the exact timing of each word.
    
    Args:
        xml_file_path: Path to the XML file
        speaker_id: Speaker identifier (e.g., "A", "B", etc.)
        
    Returns:
        Dictionary mapping timestamp to "speaker:word" string
    """
    word_timestamps = {}
    
    try:
        # Parse the XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Define namespace for NITE XML format
        namespace = {'nite': 'http://nite.sourceforge.net/'}
        
        # Find all word elements, excluding punctuation and vocal sounds
        for word_element in root.findall('w', namespace):
            start_time = word_element.get('starttime')
            word_text = word_element.text
            is_punctuation = word_element.get('punc') == 'true'
            
            # Process only actual words (not punctuation marks)
            if start_time and word_text and not is_punctuation:
                timestamp = float(start_time)
                # Decode HTML entities (e.g., &#39; -> ')
                clean_word = html.unescape(word_text.strip())
                # Store in format "speaker:word" 
                word_timestamps[timestamp] = f"{speaker_id}:{clean_word}"
                
    except ET.ParseError as e:
        print(f"Warning: XML Parse Error in {xml_file_path}: {e}")
    except FileNotFoundError:
        print(f"Warning: Could not find file {xml_file_path}")
    except Exception as e:
        print(f"Warning: Error processing {xml_file_path}: {e}")
    
    return word_timestamps


def build_chronological_word_dictionary(file_speaker_pairs: List[Tuple[str, str]]) -> Dict[float, str]:
    """
    Build a dictionary of all words from all speakers in chronological order.
    
    This combines words from all speakers into a single timeline, preserving
    the exact timing of overlapping speech.
    
    Args:
        file_speaker_pairs: List of (file_path, speaker_id) tuples
        
    Returns:
        Dictionary mapping timestamp to "speaker:word" string for all speakers
    """
    combined_word_dict = {}
    
    # Process each speaker's file
    for file_path, speaker_id in file_speaker_pairs:
        print(f"Processing {speaker_id}: {os.path.basename(file_path)}")
        
        # Extract words from this speaker's XML file
        speaker_words = extract_words_from_xml(file_path, speaker_id)
        
        # Add to combined dictionary
        combined_word_dict.update(speaker_words)
    
    return combined_word_dict


def create_turns_with_gap_logic(word_dict: Dict[float, str], gap_threshold: float = 1.0) -> List[Tuple[str, str, float, float]]:
    """
    Create conversation turns based on speech gaps within each speaker.
    
    NEW LOGIC: A turn continues as long as a speaker keeps talking, even if other
    speakers overlap. A turn only ends when the speaker stops speaking for more
    than the gap_threshold (default 1 second).
    
    Args:
        word_dict: Dictionary mapping timestamp to "speaker:word"
        gap_threshold: Gap in seconds to end a turn for the same speaker
        
    Returns:
        List of (speaker, text, onset_time, offset_time) tuples
    """
    # Sort timestamps to process words chronologically
    sorted_timestamps = sorted(word_dict.keys())
    
    if not sorted_timestamps:
        return []
    
    turns = []
    # Track the last timestamp and ongoing turn for each speaker
    speaker_last_timestamp = {}
    speaker_current_turn = {}  # speaker -> {'words': [], 'start': timestamp, 'end': timestamp}
    
    print(f"Creating turns with gap threshold: {gap_threshold} seconds")
    
    # Process each word in chronological order
    for timestamp in sorted_timestamps:
        speaker_and_word = word_dict[timestamp].split(':', 1)
        speaker = speaker_and_word[0]
        word = speaker_and_word[1]
        
        # Check if this speaker has an ongoing turn
        if speaker in speaker_current_turn:
            # Calculate gap since this speaker's last word
            gap = timestamp - speaker_last_timestamp[speaker]
            
            if gap > gap_threshold:
                # Gap is too long - end the current turn and start a new one
                current_turn = speaker_current_turn[speaker]
                text = " ".join(current_turn['words'])
                turns.append((speaker, text, current_turn['start'], current_turn['end']))
                
                # Start new turn
                speaker_current_turn[speaker] = {
                    'words': [word],
                    'start': timestamp,
                    'end': timestamp
                }
            else:
                # Continue the current turn
                speaker_current_turn[speaker]['words'].append(word)
                speaker_current_turn[speaker]['end'] = timestamp
        else:
            # No ongoing turn for this speaker - start a new one
            speaker_current_turn[speaker] = {
                'words': [word],
                'start': timestamp,
                'end': timestamp
            }
        
        # Update the last timestamp for this speaker
        speaker_last_timestamp[speaker] = timestamp
    
    # Finalize any remaining ongoing turns
    for speaker, turn_data in speaker_current_turn.items():
        text = " ".join(turn_data['words'])
        turns.append((speaker, text, turn_data['start'], turn_data['end']))
    
    # Sort turns by start time to maintain chronological order in output
    turns.sort(key=lambda x: x[2])
    
    return turns


def merge_cross_talk_turns(turns: List[Tuple[str, str, float, float]], 
                          split_parameter: int = 4) -> List[Tuple[str, str, float, float]]:
    """
    Merge short consecutive turns from the same speaker.
    
    This implements a simplified version of the original cross-talk merging logic,
    adapted for the new turn structure that includes timing information.
    
    Args:
        turns: List of (speaker, text, onset, offset) tuples
        split_parameter: Maximum words per turn for merging eligibility
        
    Returns:
        List of merged turns
    """
    if not turns:
        return []
    
    merged_turns = []
    current_turn = turns[0]
    
    for next_turn in turns[1:]:
        current_speaker, current_text, current_onset, current_offset = current_turn
        next_speaker, next_text, next_onset, next_offset = next_turn
        
        # Check if we should merge consecutive turns from the same speaker
        if (current_speaker == next_speaker and 
            len(current_text.split()) <= split_parameter and 
            len(next_text.split()) <= split_parameter):
            
            # Merge the turns
            merged_text = current_text + " " + next_text
            merged_turn = (current_speaker, merged_text, current_onset, next_offset)
            current_turn = merged_turn
        else:
            # Can't merge - add current turn to results and move to next
            merged_turns.append(current_turn)
            current_turn = next_turn
    
    # Add the final turn
    merged_turns.append(current_turn)
    
    return merged_turns


def write_turns_to_csv(turns: List[Tuple[str, str, float, float]], 
                       output_file: str = "conversation_turns.csv") -> None:
    """
    Write conversation turns to a CSV file with timing information.
    
    Args:
        turns: List of (speaker, text, onset_time, offset_time) tuples
        output_file: Output CSV filename
    """
    # Prepare data for CSV output
    csv_data = []
    csv_headers = ['speaker', 'text', 'onset_time', 'offset_time']
    
    for speaker, text, onset_time, offset_time in turns:
        # Add to CSV data
        csv_data.append([speaker, text, f"{onset_time:.2f}", f"{offset_time:.2f}"])
    
    # Write to CSV file
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_headers)
            writer.writerows(csv_data)
        print(f"Conversation turns written to {output_file}")
    except Exception as e:
        print(f"Error writing CSV file: {e}")


def parse_command_line_arguments() -> Tuple[str, Optional[List[str]], float]:
    """
    Parse command line arguments for directory, speaker list, and gap threshold.
    
    Returns:
        Tuple of (directory_path, speaker_list, gap_threshold)
    """
    # Set default values
    directory = "."  # Current directory
    speakers = None
    gap_threshold = 1.0  # Default 1 second gap threshold
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    if len(sys.argv) > 2:
        # Parse speaker list (comma-separated)
        speakers = [s.strip() for s in sys.argv[2].split(',')]
    
    if len(sys.argv) > 3:
        # Parse gap threshold
        try:
            gap_threshold = float(sys.argv[3])
        except ValueError:
            print(f"Warning: Invalid gap threshold '{sys.argv[3]}', using default 1.0")
            gap_threshold = 1.0
    
    return directory, speakers, gap_threshold


def main():
    """
    Main function that orchestrates the transcription processing pipeline.
    
    This function implements the complete workflow with the new turn logic:
    1. Parse command line arguments (including gap threshold)
    2. Discover XML files and speakers
    3. Extract words from XML files
    4. Create turns based on speech gaps (NEW LOGIC)
    5. Optionally merge short consecutive turns
    6. Write results to CSV with timestamps
    """
    print("=== XML Transcription to Conversation Processor ===")
    print("NEW: Turns based on speech gaps, not speaker changes")
    
    # Parse command line arguments
    directory, specified_speakers, gap_threshold = parse_command_line_arguments()
    print(f"Processing directory: {directory}")
    print(f"Gap threshold for ending turns: {gap_threshold} seconds")
    
    # Discover XML files and their speakers
    if specified_speakers:
        # Use specified speakers and find corresponding files
        print(f"Using specified speakers: {specified_speakers}")
        file_speaker_pairs = []
        for speaker in specified_speakers:
            # Find XML file for this speaker
            pattern = os.path.join(directory, f"*.{speaker}.xml")
            matches = glob.glob(pattern)
            if matches:
                file_speaker_pairs.append((matches[0], speaker))
            else:
                print(f"Warning: No XML file found for speaker {speaker}")
    else:
        # Auto-discover files and speakers
        print("Auto-discovering XML files and speakers...")
        file_speaker_pairs = discover_xml_files_and_speakers(directory)
    
    if not file_speaker_pairs:
        print("Error: No XML files found!")
        sys.exit(1)
    
    print(f"Found {len(file_speaker_pairs)} speaker files:")
    for file_path, speaker in file_speaker_pairs:
        print(f"  {speaker}: {os.path.basename(file_path)}")
    
    # Step 1: Extract words with timestamps from all XML files
    print("\n=== Extracting words from XML files ===")
    word_dict = build_chronological_word_dictionary(file_speaker_pairs)
    print(f"Extracted {len(word_dict)} words total")
    
    # Step 2: Create turns based on speech gaps (NEW LOGIC)
    print(f"\n=== Creating turns based on {gap_threshold}s gap threshold ===")
    turns = create_turns_with_gap_logic(word_dict, gap_threshold)
    print(f"Created {len(turns)} turns based on speech gaps")
    
    # Step 3: Optionally merge short consecutive turns from same speaker
    print("\n=== Merging short consecutive turns ===")
    split_parameter = 4  # Maximum words per turn for merging
    merged_turns = merge_cross_talk_turns(turns, split_parameter)
    print(f"After merging: {len(merged_turns)} final turns")
    
    # Step 4: Write results to CSV with timestamps
    print("\n=== Writing results to CSV ===")
    output_file = os.path.join(directory, "conversation_turns.csv")
    write_turns_to_csv(merged_turns, output_file)
    
    # Print preview of results
    print("\n=== Preview of first 5 turns ===")
    for turn in merged_turns[:5]:
        speaker, text, onset, offset = turn
        print(f"{speaker}: {text} ({onset:.2f} - {offset:.2f})")
    
    print(f"\nProcessing complete! Results saved to {output_file}")
    print(f"Total turns created: {len(merged_turns)}")


if __name__ == "__main__":
    main()