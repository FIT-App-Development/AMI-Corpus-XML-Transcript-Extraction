import streamlit as st
import pandas as pd
import os
import sys
import glob
import time
from pathlib import Path
import subprocess
from typing import List, Tuple, Optional

# Import the transcription processor functions
# Note: This assumes transcription_processor.py is in the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transcription_processor import (
    discover_xml_files_and_speakers,
    build_chronological_word_dictionary,
    create_turns_with_gap_logic,
    merge_cross_talk_turns,
    write_turns_to_csv
)

# Page configuration
st.set_page_config(
    page_title="XML Transcription Processor",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .status-info {
        color: #17a2b8;
        font-weight: bold;
    }
    .dataframe-container {
        width: 100%;
    }
    .stDataFrame > div:first-child > div > div > div > table {
        width: 100% !important;
    }
    .stDataFrame [data-testid="column-text"] {
        width: 60% !important;
    }
    .stDataFrame [data-testid="column-speaker"] {
        width: 10% !important;
    }
    .stDataFrame [data-testid="column-onset time"] {
        width: 15% !important;
    }
    .stDataFrame [data-testid="column-offset time"] {
        width: 15% !important;
    }
    .directory-input-container {
        position: relative;
    }
    .browse-button {
        position: absolute;
        right: 5px;
        top: 50%;
        transform: translateY(-50%);
        background: #ff4b4b;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        z-index: 1000;
    }
    .browse-button:hover {
        background: #ff3333;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Tkinter for file dialog (hidden window)
@st.cache_resource
def init_tkinter():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    return root

def select_directory_dialog():
    """Open a directory selection dialog"""
    try:
        root = init_tkinter()
        # Force the dialog to appear on top
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        directory = filedialog.askdirectory(parent=root, title="Select Directory Containing XML Files")
        return directory if directory else None
    except Exception as e:
        st.error(f"Error opening directory dialog: {e}")
        return None

# Initialize Tkinter for file dialog (hidden window)
@st.cache_resource
def init_tkinter():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    return root

def select_directory_dialog():
    """Open a directory selection dialog"""
    try:
        root = init_tkinter()
        # Force the dialog to appear on top
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        directory = filedialog.askdirectory(parent=root, title="Select Directory Containing XML Files")
        return directory if directory else None
    except Exception as e:
        st.error(f"Error opening directory dialog: {e}")
        return None

# Initialize session state
if 'transcription_complete' not in st.session_state:
    st.session_state.transcription_complete = False
if 'transcript_data' not in st.session_state:
    st.session_state.transcript_data = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'directory' not in st.session_state:
    st.session_state.directory = "."

# Header
st.title("🎙️ XML Transcription to Conversation Processor")
st.markdown("Convert speaker transcription XML files into readable conversation format with timing information.")

# Sidebar for configuration
st.sidebar.header("Configuration")

# Directory selection
st.sidebar.subheader("Directory Selection")

# Create a modern, single-line directory selector with common paths
current_dir = os.getcwd()
common_paths = [
    ("Current Directory", current_dir),
    ("Home Directory", os.path.expanduser("~")),
    ("Desktop", os.path.join(os.path.expanduser("~"), "Desktop")),
    ("Documents", os.path.join(os.path.expanduser("~"), "Documents")),
    ("Downloads", os.path.join(os.path.expanduser("~"), "Downloads")),
]

# Add quick select for common directories
selected_path = st.sidebar.selectbox(
    "Quick Select",
    options=[path[1] for path in common_paths],
    format_func=lambda x: next((name for name, path in common_paths if path == x), x),
    help="Select a common directory or use custom path below"
)

# Manual directory input with built-in validation
directory = st.sidebar.text_input(
    "Directory Path",
    value=selected_path if selected_path else st.session_state.directory,
    help="Directory containing XML files"
)

# Directory validation and status
if directory and os.path.exists(directory):
    # Count XML files in directory
    xml_files = glob.glob(os.path.join(directory, "*.xml"))
    if xml_files:
        st.sidebar.success(f"✅ {len(xml_files)} XML files found")
    else:
        st.sidebar.warning("⚠️ No XML files found in directory")
    st.session_state.directory = directory
elif directory:
    st.sidebar.error("❌ Directory does not exist")
else:
    st.sidebar.info("Please select or enter a directory path")

# Gap threshold slider
gap_threshold = st.sidebar.slider(
    "Gap Threshold (seconds)",
    min_value=0.1,
    max_value=5.0,
    value=1.0,
    step=0.1,
    help="Silence gap in seconds to end a turn. A turn continues as long as a speaker keeps talking."
)

# Speaker specification options
st.sidebar.subheader("Speaker Selection")
auto_discover = st.sidebar.radio(
    "Speaker Discovery Method",
    ["Auto-discover from files", "Specify speakers manually"],
    help="Choose whether to automatically find speakers from XML files or specify them manually."
)

speakers_list = None
if auto_discover == "Specify speakers manually":
    speakers_input = st.sidebar.text_input(
        "Speakers (comma-separated)",
        placeholder="A,B,C,D",
        help="Enter speaker IDs separated by commas (e.g., A,B,C,D)"
    )
    if speakers_input:
        speakers_list = [s.strip() for s in speakers_input.split(',') if s.strip()]

# Merging options
st.sidebar.subheader("Turn Merging")
enable_merging = st.sidebar.checkbox(
    "Enable turn merging",
    value=True,
    help="Merge short consecutive turns from the same speaker"
)

split_parameter = st.sidebar.number_input(
    "Max words per turn for merging",
    min_value=1,
    max_value=20,
    value=4,
    help="Maximum words per turn to be eligible for merging"
)

# Process button
process_button = st.sidebar.button(
    "🚀 Start Processing",
    disabled=st.session_state.processing,
    use_container_width=True
)

# Status display
status_container = st.sidebar.container()

# Main content area
col1, col2 = st.columns([3, 1])

# File discovery preview
with col2:
    st.subheader("Found Files")
    
    if os.path.exists(directory):
        if speakers_list:
            # Show specified speakers and their files
            file_speaker_pairs = []
            for speaker in speakers_list:
                pattern = os.path.join(directory, f"*.{speaker}.xml")
                matches = glob.glob(pattern)
                if matches:
                    file_speaker_pairs.append((matches[0], speaker))
            
            if file_speaker_pairs:
                preview_df = pd.DataFrame([
                    {"Speaker": speaker, "File": os.path.basename(file_path)}
                    for file_path, speaker in file_speaker_pairs
                ])
                st.dataframe(preview_df, hide_index=True, use_container_width=True)
            else:
                st.warning("No XML files found for specified speakers")
        else:
            # Auto-discover files
            try:
                file_speaker_pairs = discover_xml_files_and_speakers(directory)
                if file_speaker_pairs:
                    preview_df = pd.DataFrame([
                        {"Speaker": speaker, "File": os.path.basename(file_path)}
                        for file_path, speaker in file_speaker_pairs
                    ])
                    st.dataframe(preview_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No XML files found in directory")
            except Exception as e:
                st.error(f"Error discovering files: {e}")
    else:
        st.error("Directory does not exist")

# Processing logic
if process_button and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.transcription_complete = False
    
    # Clear previous results
    with col1:
        st.subheader("Processing Status")
        
    with status_container:
        st.markdown('<p class="status-info">🔄 Initializing processing...</p>', unsafe_allow_html=True)
    
    try:
        # Validate directory
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory '{directory}' does not exist")
        
        # Get file-speaker pairs
        if speakers_list:
            file_speaker_pairs = []
            for speaker in speakers_list:
                pattern = os.path.join(directory, f"*.{speaker}.xml")
                matches = glob.glob(pattern)
                if matches:
                    file_speaker_pairs.append((matches[0], speaker))
                else:
                    st.warning(f"No XML file found for speaker {speaker}")
        else:
            file_speaker_pairs = discover_xml_files_and_speakers(directory)
        
        if not file_speaker_pairs:
            raise ValueError("No XML files found!")
        
        # Create progress placeholder
        progress_placeholder = col1.empty()
        with progress_placeholder.container():
            st.info(f"Found {len(file_speaker_pairs)} speaker files")
            progress_bar = st.progress(0)
            step_text = st.empty()
        
        # Step 1: Extract words
        with status_container:
            st.markdown('<p class="status-info">📝 Extracting words from XML files...</p>', unsafe_allow_html=True)
        
        step_text.text("Step 1/4: Extracting words from XML files...")
        progress_bar.progress(25)
        
        word_dict = build_chronological_word_dictionary(file_speaker_pairs)
        
        # Step 2: Create turns
        with status_container:
            st.markdown(f'<p class="status-info">🔄 Creating turns (gap threshold: {gap_threshold}s)...</p>', unsafe_allow_html=True)
        
        step_text.text(f"Step 2/4: Creating turns (gap threshold: {gap_threshold}s)...")
        progress_bar.progress(50)
        
        turns = create_turns_with_gap_logic(word_dict, gap_threshold)
        
        # Step 3: Merge turns (optional)
        if enable_merging:
            with status_container:
                st.markdown('<p class="status-info">🔗 Merging short consecutive turns...</p>', unsafe_allow_html=True)
            
            step_text.text("Step 3/4: Merging short consecutive turns...")
            progress_bar.progress(75)
            
            turns = merge_cross_talk_turns(turns, split_parameter)
        else:
            progress_bar.progress(75)
        
        # Step 4: Write results
        with status_container:
            st.markdown('<p class="status-info">💾 Writing results to CSV...</p>', unsafe_allow_html=True)
        
        step_text.text("Step 4/4: Writing results to CSV...")
        progress_bar.progress(90)
        
        output_file = os.path.join(directory, "conversation_turns.csv")
        write_turns_to_csv(turns, output_file)
        
        # Convert to DataFrame for display
        df = pd.DataFrame(turns, columns=['Speaker', 'Text', 'Onset Time', 'Offset Time'])
        st.session_state.transcript_data = df
        st.session_state.transcription_complete = True
        
        progress_bar.progress(100)
        step_text.text("✅ Processing complete!")
        
        with status_container:
            st.markdown('<p class="status-success">✅ Processing complete!</p>', unsafe_allow_html=True)
            st.info(f"Results saved to: {output_file}")
            st.info(f"Total turns created: {len(turns)}")
        
    except Exception as e:
        with status_container:
            st.markdown(f'<p class="status-error">❌ Error: {str(e)}</p>', unsafe_allow_html=True)
        
        with col1:
            st.error(f"Error during processing: {str(e)}")
    
    finally:
        st.session_state.processing = False

# Display results
with col1:
    if st.session_state.transcription_complete and st.session_state.transcript_data is not None:
        st.subheader("Conversation Turns")
        
        # Display summary statistics
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("Total Turns", len(st.session_state.transcript_data))
        with col_stats2:
            speakers = st.session_state.transcript_data['Speaker'].unique()
            st.metric("Speakers", len(speakers))
        with col_stats3:
            avg_words = st.session_state.transcript_data['Text'].str.split().str.len().mean()
            st.metric("Avg Words/Turn", f"{avg_words:.1f}")
        
        # Preview first few turns
        st.markdown("**Preview of first 10 turns:**")
        preview_df = st.session_state.transcript_data.head(10).copy()
        
        # Format timing for better readability
        preview_df['Onset Time'] = preview_df['Onset Time'].astype(float).apply(lambda x: f"{x:.2f}s")
        preview_df['Offset Time'] = preview_df['Offset Time'].astype(float).apply(lambda x: f"{x:.2f}s")
        
        # Configure column widths for better text display
        st.dataframe(
            preview_df, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Text": st.column_config.TextColumn(
                    "Text",
                    width="large",
                    help="Turn text content"
                ),
                "Speaker": st.column_config.TextColumn(
                    "Speaker",
                    width="small"
                ),
                "Onset Time": st.column_config.TextColumn(
                    "Onset Time",
                    width="small"
                ),
                "Offset Time": st.column_config.TextColumn(
                    "Offset Time",
                    width="small"
                )
            }
        )
        
        # Full data view
        with st.expander("View All Turns"):
            full_df = st.session_state.transcript_data.copy()
            full_df['Onset Time'] = full_df['Onset Time'].astype(float).apply(lambda x: f"{x:.2f}s")
            full_df['Offset Time'] = full_df['Offset Time'].astype(float).apply(lambda x: f"{x:.2f}s")
            st.dataframe(
                full_df, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Text": st.column_config.TextColumn(
                        "Text",
                        width="large",
                        help="Turn text content"
                    ),
                    "Speaker": st.column_config.TextColumn(
                        "Speaker",
                        width="small"
                    ),
                    "Onset Time": st.column_config.TextColumn(
                        "Onset Time",
                        width="small"
                    ),
                    "Offset Time": st.column_config.TextColumn(
                        "Offset Time",
                        width="small"
                    )
                }
            )
        
        # Download button
        csv = st.session_state.transcript_data.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="conversation_turns.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    elif not st.session_state.processing:
        st.info("Configure settings in the sidebar and click 'Start Processing' to begin.")
        
        # Show help information
        with st.expander("How to use this tool"):
            st.markdown("""
            ### Steps to process transcription files:
            
            1. **Set directory path**: Point to the folder containing your XML transcription files
            2. **Choose gap threshold**: Set how long a speaker must pause before ending a turn (default: 1.0 seconds)
            3. **Select speakers**: Either auto-discover from files or specify manually (e.g., A,B,C,D)
            4. **Configure merging**: Choose whether to merge short consecutive turns from the same speaker
            5. **Click 'Start Processing'**: The tool will process all XML files and create conversation turns
            
            ### Output:
            - **CSV file**: Saved as `conversation_turns.csv` in the source directory
            - **Columns**: Speaker, Text, Onset Time, Offset Time
            - **Interactive preview**: View results directly in the interface
            
            ### XML File Format:
            Files should be named like `EN2002a.A.xml` where `A` is the speaker ID.
            The tool extracts words with timestamps from `<w>` elements in the XML.
            """)

# Footer
st.markdown("---")
st.markdown(
    "Built with Streamlit | Based on the XML Transcription to Turn-Based Conversation Processor",
    help="This interface provides a user-friendly way to process XML transcription files into conversation turns."
) 