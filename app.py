import streamlit as st
import os
from pathlib import Path
import streamlit.components.v1 as components
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import socket
import base64
import subprocess
import time

st.set_page_config(page_title="mwah", page_icon="🫶🏻", layout="wide")

st.title("🫶🏻mwah")

video_extensions = {'.mp4', '.webm', '.ogg', '.mov'}

# Movie directory - use absolute path for reliability
MOVIE_DIR = Path(__file__).parent / "static" / "movies"
if not MOVIE_DIR.exists():
    MOVIE_DIR.mkdir(parents=True, exist_ok=True)

# Start a simple HTTP server to serve HLS files on localhost
@st.cache_resource
def start_http_server():
    """Start a simple HTTP server to serve static files"""
    class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(MOVIE_DIR), **kwargs)
        
        def log_message(self, format, *args):
            pass  # Suppress logging
    
    # Find an available port
    for port in range(8001, 8050):
        try:
            server = HTTPServer(('127.0.0.1', port), MyHTTPRequestHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            return port
        except OSError:
            continue
    return None

# Check if running on Streamlit Cloud
is_streamlit_cloud = os.environ.get('STREAMLIT_SERVER_HEADLESS') == 'true'

server_port = start_http_server()
if server_port:
    st.session_state.server_port = server_port
    
    # Set up ngrok for public tunneling
    @st.cache_resource
    def setup_ngrok():
        """Setup ngrok tunnel for public access"""
        try:
            import pyngrok
            from pyngrok import ngrok
            
            # Set ngrok auth token from environment (if available)
            ngrok_token = os.environ.get('NGROK_AUTHTOKEN')
            if ngrok_token:
                ngrok.set_auth_token(ngrok_token)
            
            # Create tunnel
            public_url = ngrok.connect(server_port, "http")
            return str(public_url).replace("http://", "").replace("https://", "").strip()
        except Exception as e:
            st.warning(f"ngrok setup failed: {e}\n\nTo use ngrok, install: `pip install pyngrok` and set NGROK_AUTHTOKEN")
            return None
    
    ngrok_url = setup_ngrok()
    
    with st.sidebar:
        if ngrok_url:
            st.success(f"✅ Public URL: `{ngrok_url}`")
            st.info(f"📡 Local port: `{server_port}`")
        else:
            st.info(f"📡 Server running on port `{server_port}`\n\nLocal access: `http://localhost:{server_port}`")
else:
    st.error("Could not start file server")

files = [f.name for f in MOVIE_DIR.iterdir() if f.is_file()]
movie_files = [f for f in files if Path(f).suffix.lower() in video_extensions]

selected_movie = st.sidebar.selectbox("Select a Movie", movie_files)

if selected_movie:
    base_name = os.path.splitext(selected_movie)[0]
    # Sanitize folder name to be safe
    safe_base_name = "".join([c for c in base_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    hls_dir_name = f"{safe_base_name}_hls"
    hls_dir_path = os.path.join(MOVIE_DIR, hls_dir_name)
    hls_playlist_path = os.path.join(hls_dir_path, "playlist.m3u8")
    
    import urllib.parse
    
    if os.path.exists(hls_playlist_path):
        # Play HLS stream via HTTP server (local or ngrok)
        encoded_dir = urllib.parse.quote(hls_dir_name)
        
        # Try to use ngrok URL if available, otherwise use localhost
        if 'ngrok_url' in st.session_state and st.session_state.ngrok_url:
            base_url = st.session_state.ngrok_url
        else:
            base_url = f"http://localhost:{server_port}"
        
        video_url = f"{base_url}/{encoded_dir}/playlist.m3u8"
        is_hls = "true"
    else:
        # Offer conversion
        st.warning("This file is not optimized for streaming. It may buffer.")
        
        if st.button("Optimize for Streaming (Create HLS)"):
            with st.spinner("Converting"):
                # Create HLS directory
                if not os.path.exists(hls_dir_path):
                    os.makedirs(hls_dir_path)
                    
                # FFmpeg command to convert to HLS
                input_path = os.path.join(MOVIE_DIR, selected_movie)
                output_path = hls_playlist_path
                
                # Basic HLS conversion command
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-codec:", "copy", "-start_number", "0", 
                    "-hls_time", "10", "-hls_list_size", "0", 
                    "-f", "hls", output_path
                ]
                
                try:
                    import subprocess
                    subprocess.run(cmd, check=True)
                    st.success("Conversion Complete! Please refresh the page.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Conversion failed: {e}")
                    st.error("Make sure FFmpeg is installed!")
        
        # Fallback to direct MP4 play
        encoded_name = urllib.parse.quote(selected_movie)
        video_url = f"app/static/movies/{encoded_name}"
        is_hls = "false"
    
    st.subheader(f"Now Playing: {selected_movie}")
    
    # Plyr HTML Code with HLS support
    plyr_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
            <style>
                body {{ margin: 0; background-color: #0e1117; display: flex; justify-content: center; align-items: center; height: 100vh; }}
                .container {{ 
                    width: 100%; 
                    max-width: 1200px; 
                    aspect-ratio: 16/9; 
                    margin: 0 auto;
                }}
                :root {{ --plyr-color-main: #ff4b4b; }}
                /* Ensure video fills container */
                .plyr {{ height: 100%; width: 100%; }}
            </style>
        </head>
        <body>
            <div class="container">
                <video id="player" playsinline controls crossorigin></video>
            </div>
            <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
            <script>
                document.addEventListener('DOMContentLoaded', () => {{
                    const source = "{video_url}";
                    const video = document.querySelector('video');
                    const isHls = {is_hls};
                    
                    const defaultOptions = {{
                        controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'captions', 'settings', 'pip', 'airplay', 'fullscreen'],
                        settings: ['captions', 'quality', 'speed', 'loop'],
                        ratio: '16:9'
                    }};

                    if (isHls && Hls.isSupported()) {{
                        const hls = new Hls();
                        hls.loadSource(source);
                        hls.attachMedia(video);
                        window.hls = hls;
                        
                        hls.on(Hls.Events.MANIFEST_PARSED, function() {{
                            const player = new Plyr(video, defaultOptions);
                        }});
                    }} else {{
                        video.src = source;
                        const player = new Plyr(video, defaultOptions);
                    }}
                }});
            </script>
        </body>
        </html>
        """
        
    # Embed the player with a flexible height
    components.html(plyr_html, height=700, scrolling=False)
