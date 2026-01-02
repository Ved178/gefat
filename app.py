import streamlit as st
import os

st.set_page_config(page_title="mwah", page_icon="🫶🏻", layout="wide")

st.title("🫶🏻mwah")

# Directory containing movies (now inside static)
# Streamlit serves files in 'static' at root URL
# So 'static/movies/foo.mp4' is accessible at 'app/static/movies/foo.mp4'
# But internally we need to list files from the physical path.
# Filter for BROWSER-SUPPORTED video extensions
video_extensions = {'.mp4', '.webm', '.ogg', '.mov'}

# Movie directory
MOVIE_DIR = os.path.join("static", "movies")
if not os.path.exists(MOVIE_DIR):
    os.makedirs(MOVIE_DIR)

files = [f for f in os.listdir(MOVIE_DIR) if os.path.isfile(os.path.join(MOVIE_DIR, f))]
movie_files = [f for f in files if os.path.splitext(f)[1].lower() in video_extensions]

selected_movie = st.sidebar.selectbox("Select a Movie", movie_files)

if selected_movie:
    st.subheader(f"Now Playing: {selected_movie}")
    
    # Play local video file
    video_file_path = os.path.join(MOVIE_DIR, selected_movie)
    if os.path.exists(video_file_path):
        with open(video_file_path, 'rb') as f:
            st.video(f.read(), format='video/mp4' if selected_movie.endswith('.mp4') else None)
    else:
        st.error(f"Video file not found: {video_file_path}")
