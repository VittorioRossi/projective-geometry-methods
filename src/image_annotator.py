import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates

LINE_KINDS = ['vertical', 'plane_1', 'plane_2']

def main():
    st.set_page_config(page_title="Image Annotator", layout="wide")
    
    st.title("Image Annotation Tool")
    
    # Initialize session state variables if they don't exist
    if 'annotations' not in st.session_state:
        st.session_state.annotations = pd.DataFrame(columns=['x', 'y', 'label', 'timestamp'])
    
    if 'image_width' not in st.session_state:
        st.session_state.image_width = 0
        
    if 'image_height' not in st.session_state:
        st.session_state.image_height = 0
        
    if 'display_width' not in st.session_state:
        st.session_state.display_width = 800
    
    if 'awaiting_label' not in st.session_state:
        st.session_state.awaiting_label = False
        
    if 'current_point' not in st.session_state:
        st.session_state.current_point = None
        
    # Sidebar for uploading image and other controls
    with st.sidebar:
        st.header("Upload Image")
        uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
        
        st.header("Annotation Controls")
        point_size = st.slider("Point Size", 5, 30, 15)
        
        # Image sizing options
        st.header("Image Display")
        st.session_state.display_width = st.slider("Display Width", 400, 1600, 800)
        
        # Download button (appears when annotations exist)
        if len(st.session_state.annotations) > 0:
            csv = convert_df_to_csv(st.session_state.annotations)
            st.download_button(
                label="Download Annotations (CSV)",
                data=csv,
                file_name="image_annotations.csv",
                mime="text/csv",
            )
            
            # Also add clear button
            if st.button("Clear All Annotations"):
                st.session_state.annotations = pd.DataFrame(columns=['x', 'y', 'label', 'timestamp'])
                st.session_state.awaiting_label = False
                st.session_state.current_point = None
                st.rerun()

    # Main area for image display and annotation
    if uploaded_file is not None:
        # Convert uploaded file to PIL Image
        image = Image.open(uploaded_file)
        width, height = image.size
        st.session_state.image_width = width
        st.session_state.image_height = height
        
        # Create two columns - one for the image, one for the form
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Display image with canvas overlay for annotation
            st.subheader("Click on the image to annotate")
            
            # Resize image for display while maintaining aspect ratio
            aspect_ratio = height / width
            display_width = st.session_state.display_width
            display_height = int(display_width * aspect_ratio)
            
            # Create a display image with existing annotations
            display_image = image.resize((display_width, display_height), Image.LANCZOS)
            
            # Calculate scale factors for annotation coordinates
            scale_x = width / display_width
            scale_y = height / display_height
            
            # Convert to RGB if it's not already (for drawing colored points)
            if display_image.mode != 'RGB':
                display_image = display_image.convert('RGB')
                
            # Draw existing annotations on the image
            if len(st.session_state.annotations) > 0:
                draw = ImageDraw.Draw(display_image)
                
                # Draw all annotations
                for _, row in st.session_state.annotations.iterrows():
                    # Convert original coordinates to display coordinates
                    display_x = row['x'] / scale_x
                    display_y = row['y'] / scale_y
                    
                    # Draw a circle at the point
                    draw.ellipse(
                        (display_x-point_size, display_y-point_size, display_x+point_size, display_y+point_size), 
                        fill='red', 
                        outline='white'
                    )
                    
                    # Draw the label text with a background for visibility
                    text_x = display_x + point_size + 5
                    text_y = display_y - point_size
                    
                    # Measure text width for background
                    font = ImageFont.load_default()
                    text_width, text_height = draw.textsize(row['label'], font=font) if hasattr(draw, 'textsize') else (len(row['label']) * 7, 12)
                    
                    # Draw text background
                    draw.rectangle(
                        [text_x - 2, text_y - 2, text_x + text_width + 2, text_y + text_height + 2],
                        fill=(0, 0, 0),
                        outline=None
                    )
                    
                    # Draw the text
                    draw.text((text_x, text_y), row['label'], fill='white')
            
            try:
                # Get click coordinates using streamlit_image_coordinates
                clicked_coords = streamlit_image_coordinates(
                    display_image,
                    key="annotator"
                )
                
                # If image was clicked, store coordinates for annotation
                if clicked_coords and not st.session_state.awaiting_label:
                    # Convert display coordinates back to original image coordinates
                    original_x = clicked_coords["x"] * scale_x
                    original_y = clicked_coords["y"] * scale_y
                    st.session_state.current_point = (original_x, original_y)
                    st.session_state.awaiting_label = True
                    
                    # Show a message confirming the click
                    st.success(f"Point selected at original coordinates: ({original_x:.1f}, {original_y:.1f})")
                    st.rerun()  # This forces a refresh to show the label input form
            except ImportError:
                # Fallback method using a placeholder
                st.warning("For better annotation experience, install: pip install streamlit-image-coordinates")
                
                # Display the image
                st.image(display_image, use_container_width=False)
                
                # Manual coordinate input
                st.subheader("Enter coordinates manually:")
                col_x, col_y = st.columns(2)
                with col_x:
                    x = st.number_input("X coordinate:", min_value=0, max_value=width, value=width//2)
                with col_y:
                    y = st.number_input("Y coordinate:", min_value=0, max_value=height, value=height//2)
                
                if st.button("Set Point"):
                    st.session_state.current_point = (x, y)
                    st.session_state.awaiting_label = True
                    st.rerun()
        
        with col2:
            st.header("Add Annotation")
            
            # Show coordinates of last click and get label
            if st.session_state.awaiting_label and st.session_state.current_point:
                x, y = st.session_state.current_point
                st.write(f"Selected Point: ({x:.2f}, {y:.2f})")
                
                # Form for adding the annotation
                with st.form("annotation_form"):
                    label = st.text_input("Label")
                    submitted = st.form_submit_button("Add Annotation")
                    cancel = st.form_submit_button("Cancel")
                    
                    if submitted and label:
                        # Add new annotation
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        new_row = pd.DataFrame({
                            'x': [x],
                            'y': [y],
                            'label': [label],
                            'timestamp': [timestamp]
                        })
                        
                        # Update annotations
                        if len(st.session_state.annotations) == 0:
                            st.session_state.annotations = new_row
                        else:
                            st.session_state.annotations = pd.concat(
                                [st.session_state.annotations, new_row], 
                                ignore_index=True
                            )
                        
                        # Reset current point
                        st.session_state.current_point = None
                        st.session_state.awaiting_label = False
                        st.rerun()
                        
                    if cancel:
                        st.session_state.current_point = None
                        st.session_state.awaiting_label = False
                        st.rerun()
            else:
                st.write("👈 Click on the image to select a point")
            
            # Display table of annotations
            if not st.session_state.annotations.empty:
                st.header("Current Annotations")
                st.dataframe(
                    st.session_state.annotations[['x', 'y', 'label']], 
                    use_container_width=True
                )
                
                # Add undo button
                if st.button("Undo Last Annotation"):
                    if len(st.session_state.annotations) > 0:
                        st.session_state.annotations = st.session_state.annotations.iloc[:-1]
                        st.rerun()
    else:
        st.info("Please upload an image to start annotating")

def convert_df_to_csv(df):
    """Convert dataframe to CSV string for download"""
    return df.to_csv(index=False).encode('utf-8')

if __name__ == "__main__":
    main()