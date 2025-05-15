# XML Transcription to Turn-Based Conversation Processor

A sophisticated Python script for processing AMI Corpus XML transcription files and converting them into readable conversation format with precise timing information.

## Overview

This project is a **fork and significant enhancement** of the original AMI Corpus transcription processor from [Utkichaps/AMICorpus-Meeting-Transcript-Extraction](https://github.com/Utkichaps/AMICorpus-Meeting-Transcript-Extraction). The new implementation features improved turn detection logic, robust XML parsing, comprehensive error handling, and configurable output formatting.

## Key Features

- **XML-First Approach**: Processes XML files directly instead of plain text
- **Intelligent Turn Detection**: Uses speech gap detection rather than simple speaker changes
- **Precise Timing**: Preserves exact onset and offset times for each turn
- **Overlap Handling**: Correctly processes simultaneous speech from multiple speakers
- **Configurable Gap Threshold**: Customizable silence duration for turn detection
- **Automatic Discovery**: Can auto-detect XML files and speakers in a directory
- **CSV Output**: Structured output with speaker, text, and timing columns
- **Error Resilience**: Comprehensive error handling for malformed XML files

## Installation

### Requirements

- Python 3.6+
- Standard library modules only (no external dependencies)

### Setup

```bash
# Clone the repository
git clone [your-repo-url]
cd transcription-processor

# Make the script executable (optional)
chmod +x transcription_processor.py
```

## Usage

### Basic Usage

```bash
# Process all XML files in current directory
python transcription_processor.py

# Process specific directory
python transcription_processor.py /path/to/xml/files

# Specify speakers explicitly
python transcription_processor.py . A,B,C,D

# Custom gap threshold (2 seconds)
python transcription_processor.py . A,B,C,D 2.0
```

### Command Line Arguments

```
python transcription_processor.py [directory] [speakers] [gap_threshold]
```

- **directory**: Directory containing XML files (default: current directory)
- **speakers**: Comma-separated list of speakers (e.g., "A,B,C,D")
- **gap_threshold**: Silence gap in seconds to end a turn (default: 1.0)

### Input Format

The script expects XML files in the AMI Corpus format:
- Files named like: `EN2002a.A.xml`, `EN2002a.B.xml`, etc.
- XML structure with `<w>` elements containing:
  - `starttime` attribute with timestamp
  - Word content as element text
  - Optional `punc` attribute for punctuation

### Output Format

Creates a CSV file (`conversation_turns.csv`) with columns:
- **speaker**: Speaker identifier (A, B, C, D)
- **text**: Complete turn text
- **onset_time**: Start time in seconds
- **offset_time**: End time in seconds

## Major Improvements Over Original Code

### 1. XML Processing vs. Text Processing
- **Original**: Processed plain text files with basic regex parsing
- **New**: Uses proper XML parsing with `xml.etree.ElementTree`
- **Benefit**: More reliable extraction, handles XML entities and attributes

### 2. Turn Detection Logic
- **Original**: Simple speaker change detection
- **New**: Gap-based turn detection within speakers
- **Benefit**: More natural conversation flow, handles interruptions and overlaps

### 3. Timing Preservation
- **Original**: Lost precise timing information
- **New**: Preserves exact onset/offset times for each turn
- **Benefit**: Enables temporal analysis and synchronization

### 4. Error Handling
- **Original**: No error handling for malformed files
- **New**: Comprehensive try-catch blocks with informative warnings
- **Benefit**: Continues processing even with problematic files

### 5. Configurability
- **Original**: Hardcoded parameters and file lists
- **New**: Command-line arguments and auto-discovery
- **Benefit**: Flexible usage without code modification

### 6. Code Organization
- **Original**: Single monolithic block of code
- **New**: Modular functions with clear responsibilities
- **Benefit**: Maintainable, testable, and reusable code

### 7. Cross-talk Handling
- **Original**: Simple rule-based merging of consecutive turns
- **New**: Gap-based detection prevents over-aggressive merging
- **Benefit**: Preserves natural conversation patterns

## Algorithm Details

### Turn Creation Process

1. **Word Extraction**: Extract all words with timestamps from XML files
2. **Chronological Sorting**: Sort all words by timestamp across speakers
3. **Gap Detection**: For each speaker, detect gaps exceeding threshold
4. **Turn Formation**: Create turns when gaps occur, preserve overlaps
5. **Turn Merging**: Optionally merge short consecutive turns from same speaker

### Gap Threshold Logic

A turn ends for a speaker when they stop speaking for more than the gap threshold:
- **Default**: 1.0 second
- **Adjustable**: Can be modified via command line
- **Speaker-specific**: Each speaker tracked independently

## Example Output

```csv
speaker,text,onset_time,offset_time
A,Good morning everyone let's get started,10.45,14.32
B,Yes I think we should begin with the agenda,14.55,18.12
A,Okay first item is the budget review,19.01,22.87
C,I have some concerns about that,23.15,25.44
```

## Configuration Options

### Split Parameter
Controls merging of short consecutive turns (defined in `merge_cross_talk_turns`):
- **Default**: 4 words maximum per turn for merging eligibility
- **Effect**: Higher values reduce cross-talk but may create unnaturally long turns

### Gap Threshold
Determines when a speaker's turn ends:
- **Lower values** (0.5s): More turn boundaries, captures brief pauses
- **Higher values** (2.0s): Fewer turn boundaries, merges across longer pauses

## Troubleshooting

### Common Issues

1. **No XML files found**
   - Check file naming convention (*.A.xml, *.B.xml, etc.)
   - Verify directory path

2. **Empty output**
   - Check XML structure matches expected format
   - Verify `<w>` elements have `starttime` attributes

3. **Missing speakers**
   - Ensure XML files exist for all specified speakers
   - Check file permissions

### Debug Mode

Add print statements in `extract_words_from_xml()` to debug XML parsing:

```python
print(f"Processing element: {word_element.tag}, text: {word_element.text}")
```

## License

[Specify your license here]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Acknowledgments

- Original implementation by [Utkichaps](https://github.com/Utkichaps/AMICorpus-Meeting-Transcript-Extraction)
- AMI Corpus project for the dataset format
- Python community for excellent XML processing libraries

## Future Enhancements

- [ ] Support for additional XML formats
- [ ] Export to other formats (JSON, Excel)
- [ ] Visualization of conversation timelines
- [ ] Speaker identification confidence scores
- [ ] Parallel processing for large corpora